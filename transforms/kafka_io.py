"""Kafka I/O transforms for reading from Kafka topics."""

from datetime import datetime
import json
import logging
from typing import Any, Dict, Optional

import apache_beam as beam
from apache_beam.io.kafka import ReadFromKafka
from apache_beam.transforms import window


class ParseKafkaMessage(beam.DoFn):
    """Parse Kafka messages from JSON format."""

    def __init__(self, topic_name: str):
        self.topic_name = topic_name

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
            message['topic'] = self.topic_name

            # Add key if present
            if key:
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                message['kafka_key'] = key

            yield message

        except json.JSONDecodeError as e:
            logging.error(
                f"Failed to parse JSON message from topic {self.topic_name}: {e}")
            # Yield to DLQ
            yield beam.pvalue.TaggedOutput('dlq', {
                'topic': self.topic_name,
                'raw_message': str(value),
                'error': f"JSON decode error: {str(e)}",
                'processing_time': datetime.utcnow().isoformat()
            })
        except Exception as e:
            logging.error(
                f"Unexpected error processing message from topic {self.topic_name}: {e}")
            yield beam.pvalue.TaggedOutput('dlq', {
                'topic': self.topic_name,
                'raw_message': str(element),
                'error': f"Processing error: {str(e)}",
                'processing_time': datetime.utcnow().isoformat()
            })


class ValidateMessage(beam.DoFn):
    """Validate message schema and required fields."""

    def __init__(self, required_fields: list):
        self.required_fields = required_fields

    def process(self, element):
        """
        Validate message has required fields.

        Args:
            element: Parsed message dictionary

        Yields:
            Valid message or sends to DLQ
        """
        try:
            missing_fields = [
                field for field in self.required_fields if field not in element]

            if missing_fields:
                logging.warning(
                    f"Message missing required fields: {missing_fields}")
                yield beam.pvalue.TaggedOutput('dlq', {
                    'message': element,
                    'error': f"Missing required fields: {missing_fields}",
                    'processing_time': datetime.utcnow().isoformat()
                })
            else:
                yield element

        except Exception as e:
            logging.error(f"Error validating message: {e}")
            yield beam.pvalue.TaggedOutput('dlq', {
                'message': element,
                'error': f"Validation error: {str(e)}",
                'processing_time': datetime.utcnow().isoformat()
            })


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
            'auto.offset.reset': 'latest',  # Start from latest for demo
            'enable.auto.commit': 'true',
            'session.timeout.ms': '30000',
            'request.timeout.ms': '40000'
        },
        topics=[topic],
        with_metadata=False,
        max_num_records=None,  # Unlimited for streaming
        start_read_time=None   # Start immediately
    )


class AddTimestamp(beam.DoFn):
    """Add timestamp to messages for windowing."""

    def process(self, element, timestamp=beam.DoFn.TimestampParam):
        """
        Add timestamp information to the message.

        Args:
            element: Message dictionary
            timestamp: Beam timestamp

        Yields:
            Message with timestamp information
        """
        try:
            # Convert Beam timestamp to datetime
            element['beam_timestamp'] = timestamp.to_utc_datetime().isoformat()
            yield element
        except Exception as e:
            logging.error(f"Error adding timestamp: {e}")
            yield element  # Continue processing even if timestamp fails
