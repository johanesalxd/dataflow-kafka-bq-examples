"""
Main Dataflow pipeline for streaming Kafka data to BigQuery.
Supports both DirectRunner (local) and DataflowRunner (cloud).
"""

import argparse
import logging
import sys
from typing import Any, Dict

import apache_beam as beam
from apache_beam.options.pipeline_options import GoogleCloudOptions
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import StandardOptions

from transforms.aggregations import create_aggregation_pipeline
from transforms.aggregations import PrepareForBigQuery
from transforms.bigquery_io import create_bigquery_pipeline_branch
from transforms.bigquery_io import FormatDLQRecord
# Import our custom transforms
from transforms.kafka_io import AddTimestamp
from transforms.kafka_io import create_kafka_source
from transforms.kafka_io import ParseKafkaMessage
from transforms.kafka_io import ValidateMessage
from utils.config_loader import get_table_spec
from utils.config_loader import load_config
from utils.config_loader import validate_config


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_pipeline_options(config: Dict[str, Any], args) -> PipelineOptions:
    """
    Create pipeline options based on configuration and arguments.

    Args:
        config: Configuration dictionary
        args: Command line arguments

    Returns:
        Configured PipelineOptions
    """
    pipeline_args = [
        f'--runner={config["runner"]}',
        '--save_main_session',
        '--setup_file=./setup.py'
    ]

    # Add streaming flag if enabled
    if config["pipeline"]["streaming"]:
        pipeline_args.append('--streaming')

    # Add job name if provided
    if args.job_name:
        pipeline_args.append(f'--job_name={args.job_name}')

    # Add Dataflow-specific options if using DataflowRunner
    if config["runner"] == "DataflowRunner":
        gcp_config = config.get("gcp", {})
        pipeline_args.extend([
            f'--project={config["bigquery"]["project_id"]}',
            f'--region={gcp_config.get("region", "us-central1")}',
            f'--temp_location={gcp_config.get("temp_location")}',
            f'--staging_location={gcp_config.get("staging_location")}',
            f'--max_num_workers={config["pipeline"].get("max_num_workers", 10)}',
            f'--num_workers={config["pipeline"].get("num_workers", 2)}'
        ])

        if gcp_config.get("service_account"):
            pipeline_args.append(
                f'--service_account_email={gcp_config["service_account"]}')

    return PipelineOptions(pipeline_args)


def get_required_fields(topic_name: str) -> list:
    """Get required fields for validation based on topic name."""
    field_mapping = {
        'user-events': ['event_id', 'user_id', 'event_type', 'timestamp'],
        'product-updates': ['product_id', 'product_name', 'price', 'category', 'timestamp'],
        'user-profiles': ['user_id', 'username', 'user_segment', 'timestamp']
    }
    return field_mapping.get(topic_name, [])


def create_topic_pipeline(pipeline, topic_config: Dict[str, Any], config: Dict[str, Any]):
    """
    Create pipeline for a single Kafka topic.

    Args:
        pipeline: Beam pipeline object
        topic_config: Topic configuration
        config: Full configuration dictionary

    Returns:
        Tuple of (raw_results, aggregated_results, dlq_results)
    """
    topic_name = topic_config['name']
    logging.info(f"Creating pipeline for topic: {topic_name}")

    # Required fields for validation
    required_fields = get_required_fields(topic_name)

    # Create Kafka source
    kafka_source = create_kafka_source(
        bootstrap_servers=config['kafka']['bootstrap_servers'],
        topic=topic_name,
        consumer_group=config['kafka']['consumer_group']
    )

    # Read from Kafka and parse messages
    raw_messages = (
        pipeline
        | f'ReadFromKafka_{topic_name}' >> kafka_source
        | f'ParseMessages_{topic_name}' >> beam.ParDo(
            ParseKafkaMessage(topic_name)
        ).with_outputs('dlq', main='main')
    )

    # Validate messages
    validated_messages = (
        raw_messages.main
        | f'ValidateMessages_{topic_name}' >> beam.ParDo(
            ValidateMessage(required_fields)
        ).with_outputs('dlq', main='main')
    )

    # Add timestamps for windowing
    timestamped_messages = (
        validated_messages.main
        | f'AddTimestamp_{topic_name}' >> beam.ParDo(AddTimestamp())
    )

    # Branch 1: Raw data to BigQuery
    raw_table_spec = get_table_spec(config, topic_config['raw_table'])
    schema_path = f"schemas/{topic_name.replace('-', '_')}.json"

    raw_sink, raw_dlq_sink, raw_prepare = create_bigquery_pipeline_branch(
        table_spec=raw_table_spec,
        schema_path=schema_path,
        table_type="raw"
    )

    raw_prepared = (
        timestamped_messages
        | f'PrepareRaw_{topic_name}' >> beam.ParDo(raw_prepare).with_outputs('dlq', main='main')
    )

    raw_results = (
        raw_prepared.main
        | f'WriteRawToBQ_{topic_name}' >> raw_sink
    )

    # Branch 2: Aggregated data to BigQuery
    agg_table_spec = get_table_spec(config, topic_config['agg_table'])

    aggregation_transform, _ = create_aggregation_pipeline(
        topic_config=topic_config,
        window_duration=config['pipeline']['window_duration_seconds']
    )

    aggregated_data = (
        timestamped_messages
        | f'Aggregate_{topic_name}' >> aggregation_transform
        | f'PrepareAggregated_{topic_name}' >> beam.ParDo(
            PrepareForBigQuery()
        ).with_outputs('dlq', main='main')
    )

    agg_sink, agg_dlq_sink, _ = create_bigquery_pipeline_branch(
        table_spec=agg_table_spec,
        table_type="aggregated"
    )

    agg_results = (
        aggregated_data.main
        | f'WriteAggToBQ_{topic_name}' >> agg_sink
    )

    # Collect all DLQ records
    all_dlq_records = (
        (raw_messages.dlq, validated_messages.dlq,
         raw_prepared.dlq, aggregated_data.dlq)
        | f'FlattenDLQ_{topic_name}' >> beam.Flatten()
        | f'FormatDLQ_{topic_name}' >> beam.ParDo(FormatDLQRecord())
    )

    # Write DLQ records to BigQuery
    dlq_table_spec = get_table_spec(config, topic_config['dlq_table'])
    _, dlq_sink, _ = create_bigquery_pipeline_branch(
        table_spec=dlq_table_spec,
        table_type="dlq"
    )

    dlq_results = (
        all_dlq_records
        | f'WriteDLQToBQ_{topic_name}' >> dlq_sink
    )

    return raw_results, agg_results, dlq_results


def run_pipeline(config: Dict[str, Any], args):
    """
    Run the main pipeline.

    Args:
        config: Configuration dictionary
        args: Command line arguments
    """
    logging.info(f"Starting pipeline with runner: {config['runner']}")

    # Create pipeline options
    pipeline_options = create_pipeline_options(config, args)

    # Create and run pipeline
    with beam.Pipeline(options=pipeline_options) as pipeline:

        # Create pipelines for each topic
        all_results = []
        for topic_config in config['kafka']['topics']:
            raw_results, agg_results, dlq_results = create_topic_pipeline(
                pipeline, topic_config, config
            )
            all_results.extend([raw_results, agg_results, dlq_results])

        logging.info(
            f"Pipeline created for {len(config['kafka']['topics'])} topics")


def main():
    """Main entry point."""
    setup_logging()

    parser = argparse.ArgumentParser(
        description='Kafka to BigQuery Dataflow Pipeline')
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--environment',
        default='local',
        choices=['local', 'cloud'],
        help='Environment to run in'
    )
    parser.add_argument(
        '--job_name',
        help='Dataflow job name (optional)'
    )

    args, pipeline_args = parser.parse_known_args()

    try:
        # Load and validate configuration
        config = load_config(args.config, args.environment)
        validate_config(config)

        logging.info(
            f"Configuration loaded for environment: {args.environment}")
        logging.info(
            f"Topics to process: {[t['name'] for t in config['kafka']['topics']]}")

        # Run pipeline
        run_pipeline(config, args)

        logging.info("Pipeline completed successfully")

    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
