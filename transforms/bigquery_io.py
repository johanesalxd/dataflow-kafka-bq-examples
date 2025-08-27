"""BigQuery I/O transforms for writing data."""

from datetime import datetime
import json
import logging
from typing import Any, Dict, Optional

import apache_beam as beam
from apache_beam.io.gcp.bigquery import BigQueryDisposition
from apache_beam.io.gcp.bigquery import WriteToBigQuery


class PrepareBigQueryRecord(beam.DoFn):
    """Prepare records for BigQuery insertion."""

    def __init__(self, table_type: str = "raw"):
        """
        Initialize the transform.

        Args:
            table_type: Type of table (raw, aggregated)
        """
        self.table_type = table_type

    def process(self, element):
        """
        Prepare record for BigQuery insertion.

        Args:
            element: Input record dictionary

        Yields:
            BigQuery-compatible record
        """
        try:
            # Create a copy to avoid modifying the original
            record = dict(element)

            # Ensure processing_time is set
            if 'processing_time' not in record:
                record['processing_time'] = datetime.utcnow().isoformat()

            # Remove any fields that shouldn't go to BigQuery
            fields_to_remove = ['kafka_key', 'topic', 'beam_timestamp']
            for field in fields_to_remove:
                record.pop(field, None)

            # Convert timestamp strings to proper format if needed
            timestamp_fields = ['timestamp', 'processing_time',
                                'window_start_time', 'window_end_time', 'aggregation_time']
            for field in timestamp_fields:
                if field in record and record[field]:
                    # Ensure timestamp is in ISO format
                    if isinstance(record[field], str):
                        try:
                            # Try to parse and reformat to ensure consistency
                            dt = datetime.fromisoformat(
                                record[field].replace('Z', '+00:00'))
                            record[field] = dt.isoformat()
                        except ValueError:
                            # If parsing fails, keep original value
                            pass

            yield record

        except Exception as e:
            logging.error(f"Error preparing BigQuery record: {e}")
            # Send to DLQ
            yield beam.pvalue.TaggedOutput('dlq', {
                'original_record': element,
                'error': f"BigQuery preparation error: {str(e)}",
                'processing_time': datetime.utcnow().isoformat(),
                'table_type': self.table_type
            })


def create_bigquery_sink(table_spec: str, schema_path: Optional[str] = None, create_disposition: str = "CREATE_IF_NEEDED"):
    """
    Create BigQuery sink transform.

    Args:
        table_spec: BigQuery table specification (project:dataset.table)
        schema_path: Path to schema file (optional)
        create_disposition: Table creation disposition

    Returns:
        WriteToBigQuery transform
    """

    # Load schema if provided
    table_schema = None
    if schema_path:
        try:
            with open(schema_path, 'r') as f:
                schema_data = json.load(f)
                if isinstance(schema_data, list):
                    table_schema = {'fields': schema_data}
                else:
                    table_schema = schema_data
        except Exception as e:
            logging.warning(f"Could not load schema from {schema_path}: {e}")

    return WriteToBigQuery(
        table=table_spec,
        schema=table_schema,
        create_disposition=create_disposition,
        write_disposition=BigQueryDisposition.WRITE_APPEND,
        insert_retry_strategy='RETRY_ON_TRANSIENT_ERROR',
        additional_bq_parameters={
            'timePartitioning': {
                'type': 'DAY',
                'field': 'processing_time'
            },
            'clustering': {
                'fields': ['user_id'] if 'user' in table_spec else ['product_id'] if 'product' in table_spec else []
            }
        }
    )


def create_dlq_sink(table_spec: str):
    """
    Create Dead Letter Queue sink for failed records.

    Args:
        table_spec: BigQuery DLQ table specification

    Returns:
        WriteToBigQuery transform for DLQ
    """

    # DLQ schema in string format
    dlq_schema = "original_record:STRING,original_data:STRING,message:STRING,raw_message:STRING,topic:STRING,error:STRING,processing_time:TIMESTAMP,table_type:STRING"

    return WriteToBigQuery(
        table=table_spec,
        schema=dlq_schema,
        create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
        write_disposition=BigQueryDisposition.WRITE_APPEND,
        insert_retry_strategy='RETRY_ON_TRANSIENT_ERROR'
    )


class FormatDLQRecord(beam.DoFn):
    """Format records for DLQ table."""

    def process(self, element):
        """
        Format DLQ record for BigQuery insertion.

        Args:
            element: DLQ record dictionary

        Yields:
            Formatted DLQ record
        """
        try:
            # Convert complex objects to JSON strings
            formatted_record = {}

            for key, value in element.items():
                if key in ['original_record', 'original_data', 'message']:
                    # Convert to JSON string if it's a dict/list
                    if isinstance(value, (dict, list)):
                        formatted_record[key] = json.dumps(value)
                    else:
                        formatted_record[key] = str(
                            value) if value is not None else None
                else:
                    formatted_record[key] = value

            # Ensure required fields are present
            if 'processing_time' not in formatted_record:
                formatted_record['processing_time'] = datetime.utcnow(
                ).isoformat()

            if 'error' not in formatted_record:
                formatted_record['error'] = 'Unknown error'

            yield formatted_record

        except Exception as e:
            logging.error(f"Error formatting DLQ record: {e}")
            # Fallback record
            yield {
                'original_record': str(element),
                'error': f"DLQ formatting error: {str(e)}",
                'processing_time': datetime.utcnow().isoformat()
            }


def create_bigquery_pipeline_branch(table_spec: str, schema_path: Optional[str] = None, table_type: str = "raw"):
    """
    Create a complete BigQuery pipeline branch with DLQ handling.

    Args:
        table_spec: BigQuery table specification
        schema_path: Path to schema file
        table_type: Type of table (raw, aggregated)

    Returns:
        Tuple of (main_sink, dlq_sink, prepare_transform)
    """

    # Create DLQ table spec
    dlq_table_spec = table_spec.replace('.', '_dlq.')

    # Create transforms
    prepare_transform = PrepareBigQueryRecord(table_type=table_type)
    main_sink = create_bigquery_sink(table_spec, schema_path)
    dlq_sink = create_dlq_sink(dlq_table_spec)

    return main_sink, dlq_sink, prepare_transform
