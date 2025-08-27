"""
Simplified Dataflow pipeline for streaming Kafka user_events to BigQuery.
"""

import argparse
import logging
import sys

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import StandardOptions

from transforms.bigquery_io import create_bigquery_sink
from transforms.bigquery_io import PrepareBigQueryRecord
from transforms.kafka_io import create_kafka_source
from transforms.kafka_io import ParseKafkaMessage
from utils.config_loader import load_config


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def create_pipeline_options(config, args):
    """Create pipeline options based on configuration."""
    pipeline_args = [
        f'--runner={config["runner"]}',
        '--save_main_session'
    ]

    # Add streaming flag
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
            f'--staging_location={gcp_config.get("staging_location")}'
        ])

    return PipelineOptions(pipeline_args)


def run_pipeline(config, args):
    """Run the simplified pipeline."""
    logging.info(f"Starting pipeline with runner: {config['runner']}")

    # Create pipeline options
    pipeline_options = create_pipeline_options(config, args)

    # Get user_events topic configuration
    user_events_topic = None
    for topic in config['kafka']['topics']:
        if topic['name'] == 'user-events':
            user_events_topic = topic
            break

    if not user_events_topic:
        raise ValueError("user-events topic not found in configuration")

    # Create table specification
    table_spec = f"{config['bigquery']['project_id']}.{config['bigquery']['dataset']}.{user_events_topic['raw_table']}"
    schema_path = "schemas/user_events.json"

    logging.info(f"Writing to BigQuery table: {table_spec}")

    # Create and run pipeline
    with beam.Pipeline(options=pipeline_options) as pipeline:

        # Read from Kafka
        kafka_source = create_kafka_source(
            bootstrap_servers=config['kafka']['bootstrap_servers'],
            topic='user-events',
            consumer_group=config['kafka']['consumer_group']
        )

        # Create the pipeline
        (
            pipeline
            | 'ReadFromKafka' >> kafka_source
            | 'ParseMessages' >> beam.ParDo(ParseKafkaMessage())
            | 'PrepareForBigQuery' >> beam.ParDo(PrepareBigQueryRecord())
            | 'WriteToBigQuery' >> create_bigquery_sink(table_spec, schema_path)
        )

        logging.info("Pipeline created successfully")


def main():
    """Main entry point."""
    setup_logging()

    parser = argparse.ArgumentParser(
        description='Simplified Kafka to BigQuery Pipeline')
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
        # Load configuration
        config = load_config(args.config, args.environment)
        logging.info(
            f"Configuration loaded for environment: {args.environment}")

        # Run pipeline
        run_pipeline(config, args)
        logging.info("Pipeline completed successfully")

    except Exception as e:
        logging.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
