"""
Dataflow pipeline for streaming Kafka messages to a partitioned BigQuery table.
"""

import argparse
import json
import logging
import time

import apache_beam as beam
from apache_beam.io.gcp.bigquery import BigQueryDisposition
from apache_beam.io.gcp.bigquery import WriteToBigQuery
from apache_beam.io.kafka import ReadFromKafka
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import StandardOptions
import yaml


def setup_logging():
    """Setup basic logging."""
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def load_config(config_path, environment):
    """Load YAML configuration file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config[environment]


class ParseKafkaMessage(beam.DoFn):
    """Parse JSON message from Kafka and add a processing timestamp."""

    def process(self, element):
        try:
            # Kafka messages are (key, value) pairs
            key, value = element
            print(f"Received message from Kafka: {value}")
            message = json.loads(value.decode('utf-8'))

            # Add a processing timestamp
            message['processing_time'] = time.strftime(
                '%Y-%m-%d %H:%M:%S', time.gmtime())

            yield message
        except Exception as e:
            print(f"Failed to parse message: {element}, error: {e}")
            # You can add a dead-letter queue here if needed
            pass


def run():
    """Build and run the pipeline."""
    parser = argparse.ArgumentParser(
        description='Kafka to BigQuery Dataflow Pipeline')
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to the configuration file'
    )
    parser.add_argument(
        '--environment',
        choices=['local', 'cloud'],
        default='local',
        help='Execution environment'
    )
    args, beam_args = parser.parse_known_args()

    # Load configuration
    config = load_config(args.config, args.environment)

    # Set pipeline options
    pipeline_options = PipelineOptions(beam_args)
    pipeline_options.view_as(
        StandardOptions).runner = config['runner']

    if config['pipeline']['streaming']:
        pipeline_options.view_as(StandardOptions).streaming = True

    # Get topic config for user-events
    topic_config = next(
        (t for t in config['kafka']['topics'] if t['name'] == 'user-events'), None)
    if not topic_config:
        raise ValueError("Configuration for 'user-events' topic not found.")

    # BigQuery table specification
    table_spec = (
        f"{config['bigquery']['project_id']}:"
        f"{config['bigquery']['dataset']}."
        f"{topic_config['raw_table']}"
    )

    # BigQuery table schema
    with open('schemas/user_events.json', 'r') as f:
        schema = json.load(f)

    table_schema = {'fields': schema}

    p = beam.Pipeline(options=pipeline_options)
    (
        p
        | "ReadFromKafka" >> ReadFromKafka(
            consumer_config={
                'bootstrap.servers': config['kafka']['bootstrap_servers'],
                'group.id': config['kafka']['consumer_group'],
                'auto.offset.reset': 'latest'
            },
            topics=[topic_config['name']]
        )
        | "ParseMessage" >> beam.ParDo(ParseKafkaMessage())
        | "WriteToBigQuery" >> WriteToBigQuery(
            table=table_spec,
            schema=table_schema,
            write_disposition=BigQueryDisposition.WRITE_APPEND,
            create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
            additional_bq_parameters={
                'timePartitioning': {
                    'type': 'DAY',
                    'field': 'timestamp'
                }
            },
            custom_gcs_temp_location=config.get(
                'gcp', {}).get('temp_location')
        )
    )
    result = p.run()
    if config['runner'] == 'DirectRunner':
        result.wait_until_finish()


if __name__ == '__main__':
    setup_logging()
    try:
        run()
    except Exception as e:
        logging.error(f"Pipeline failed with error: {e}")
