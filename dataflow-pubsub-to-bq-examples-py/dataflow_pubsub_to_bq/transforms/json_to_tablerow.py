"""Transform to parse Pub/Sub messages and convert to BigQuery TableRow."""

from datetime import datetime
import json
import logging
import time
from typing import Any, Dict

import apache_beam as beam
from apache_beam.io.gcp.pubsub import PubsubMessage
from apache_beam.utils.timestamp import Timestamp


class ParsePubSubMessage(beam.DoFn):
    """Parses Pub/Sub messages and extracts taxi ride data with metadata.

    This transform extracts:
    - Pub/Sub metadata: subscription_name, message_id, publish_time, attributes
    - Taxi ride data: ride_id, point_idx, latitude, longitude, timestamp,
                      meter_reading, meter_increment, ride_status, passenger_count
    """

    def __init__(self, subscription_name: str):
        """Initializes the transform with subscription name.

        Args:
            subscription_name: The Pub/Sub subscription name to record in BigQuery.
        """
        self.subscription_name = subscription_name

    def process(self, element: PubsubMessage) -> Any:
        """Processes a single Pub/Sub message.

        Args:
            element: PubsubMessage containing data and attributes.

        Yields:
            Dictionary with all fields for BigQuery insertion.
        """
        try:
            # Decode the message data
            message_data = element.data.decode('utf-8')
            ride_data = json.loads(message_data)

            # Extract Pub/Sub metadata (for data quality checks)
            message_id = element.message_id if hasattr(
                element, 'message_id') else ''

            # Convert to Beam Timestamp for Storage Write API compatibility
            # Beam expects Timestamp objects with .micros attribute for TIMESTAMP fields
            if hasattr(element, 'publish_time') and element.publish_time:
                publish_time = Timestamp.of(element.publish_time.timestamp())
            else:
                publish_time = Timestamp.of(time.time())

            # Extract custom attributes from the message (if any)
            attributes = element.attributes if element.attributes else {}

            # Parse taxi ride timestamp (ISO 8601 with timezone offset)
            # Example: "2026-01-15T05:45:49.16882-05:00"
            ride_timestamp_str = ride_data.get('timestamp', '')
            if ride_timestamp_str:
                try:
                    ride_timestamp = Timestamp.of(
                        datetime.fromisoformat(ride_timestamp_str).timestamp()
                    )
                except (ValueError, AttributeError):
                    logging.warning(
                        f"Invalid timestamp format: {ride_timestamp_str}"
                    )
                    ride_timestamp = None
            else:
                ride_timestamp = None

            # Create BigQuery row with all fields
            bq_row = {
                # Pub/Sub metadata
                'subscription_name': self.subscription_name,
                'message_id': message_id,
                'publish_time': publish_time,
                # Taxi ride data
                'ride_id': ride_data.get('ride_id', ''),
                'point_idx': ride_data.get('point_idx', 0),
                'latitude': ride_data.get('latitude', 0.0),
                'longitude': ride_data.get('longitude', 0.0),
                'timestamp': ride_timestamp,
                'meter_reading': ride_data.get('meter_reading', 0.0),
                'meter_increment': ride_data.get('meter_increment', 0.0),
                'ride_status': ride_data.get('ride_status', ''),
                'passenger_count': ride_data.get('passenger_count', 0),
                'attributes': json.dumps(attributes),
            }

            yield bq_row

        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON: {e}, data: {element.data}")
        except Exception as e:
            logging.error(f"Error processing message: {e}")


def get_bigquery_schema() -> list:
    """Returns the BigQuery schema for the taxi_events table.

    Returns:
        List of BigQuery schema field definitions.
    """
    return [
        {'name': 'subscription_name', 'type': 'STRING', 'mode': 'NULLABLE'},
        {'name': 'message_id', 'type': 'STRING', 'mode': 'NULLABLE'},
        {'name': 'publish_time', 'type': 'TIMESTAMP', 'mode': 'NULLABLE'},
        {'name': 'ride_id', 'type': 'STRING', 'mode': 'NULLABLE'},
        {'name': 'point_idx', 'type': 'INT64', 'mode': 'NULLABLE'},
        {'name': 'latitude', 'type': 'FLOAT', 'mode': 'NULLABLE'},
        {'name': 'longitude', 'type': 'FLOAT', 'mode': 'NULLABLE'},
        {'name': 'timestamp', 'type': 'TIMESTAMP', 'mode': 'NULLABLE'},
        {'name': 'meter_reading', 'type': 'FLOAT', 'mode': 'NULLABLE'},
        {'name': 'meter_increment', 'type': 'FLOAT', 'mode': 'NULLABLE'},
        {'name': 'ride_status', 'type': 'STRING', 'mode': 'NULLABLE'},
        {'name': 'passenger_count', 'type': 'INT64', 'mode': 'NULLABLE'},
        {'name': 'attributes', 'type': 'STRING', 'mode': 'NULLABLE'},
    ]
