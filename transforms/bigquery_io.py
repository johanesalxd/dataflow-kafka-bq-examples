"""Simplified BigQuery I/O transforms for writing data."""

from datetime import datetime
import logging
from typing import Optional

import apache_beam as beam
from apache_beam.io.gcp.bigquery import BigQueryDisposition
from apache_beam.io.gcp.bigquery import WriteToBigQuery


class PrepareBigQueryRecord(beam.DoFn):
    """Prepare records for BigQuery insertion."""

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

            # Convert timestamp to proper format if needed
            if 'timestamp' in record and record['timestamp']:
                if isinstance(record['timestamp'], str):
                    try:
                        # Try to parse and reformat to ensure consistency
                        dt = datetime.fromisoformat(
                            record['timestamp'].replace('Z', '+00:00'))
                        record['timestamp'] = dt.isoformat()
                    except ValueError:
                        # If parsing fails, keep original value
                        pass

            yield record

        except Exception as e:
            logging.error(f"Error preparing BigQuery record: {e}")
            # Skip invalid records for now
            pass


def create_bigquery_sink(table_spec: str, schema_path: Optional[str] = None):
    """
    Create BigQuery sink transform.

    Args:
        table_spec: BigQuery table specification (project:dataset.table)
        schema_path: Path to schema file (optional)

    Returns:
        WriteToBigQuery transform
    """
    import json

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
        create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
        write_disposition=BigQueryDisposition.WRITE_APPEND,
        insert_retry_strategy='RETRY_ON_TRANSIENT_ERROR'
    )
