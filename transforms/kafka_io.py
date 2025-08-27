"""Simplified Kafka I/O transforms for reading from Kafka topics."""

from datetime import datetime
import json
import logging
from typing import Any, Dict

import apache_beam as beam
from apache_beam.io.kafka import ReadFromKafka


class ParseKafkaMessage(beam.DoFn):
    """Parse Kafka messages from JSON format."""

    def process(self, element):
        """
        Parse Kafka message and add processing metadata.

        Args:
            element: Kafka message (key, value) tuple

        Yields:
            Parsed message dictionary with metadata
        """
        try:
            key, value = element

            # Parse JSON message
            if isinstance(value, bytes):
                value = value.decode('utf-8')

            message = json.loads(value)

            # Add processing metadata
            message['processing_time'] = datetime.utcnow().isoformat()

            yield message

        except Exception as e:
            logging.error(f"Failed to parse message: {e}")
            # Skip invalid messages for now
            pass


def create_kafka_source(bootstrap_servers: str, topic: str, consumer_group: str):
    """
    Create Kafka source transform.

    Args:
        bootstrap_servers: Kafka bootstrap servers
        topic: Kafka topic name
        consumer_group: Consumer group ID

    Returns:
        ReadFromKafka transform
    """
    return ReadFromKafka(
        consumer_config={
            'bootstrap.servers': bootstrap_servers,
            'group.id': consumer_group,
            'auto.offset.reset': 'latest',
            'enable.auto.commit': 'true'
        },
        topics=[topic],
        with_metadata=False
    )
