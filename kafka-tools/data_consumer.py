"""
Data consumer for Kafka topics.
Consumes sample data from user-events, product-updates, and user-profiles topics.
"""

import argparse
from datetime import datetime
import json
import logging
import signal
import sys
from typing import List, Optional

from kafka import KafkaConsumer


class DataConsumer:
    """Consume data from Kafka topics."""

    def __init__(self, bootstrap_servers: str, consumer_group: str = 'data-consumer-group'):
        """
        Initialize the data consumer.

        Args:
            bootstrap_servers: Kafka bootstrap servers
            consumer_group: Consumer group ID
        """
        self.bootstrap_servers = bootstrap_servers
        self.consumer_group = consumer_group
        self.consumer = None
        self.message_count = 0
        self.running = True

        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logging.info("Received shutdown signal, stopping consumer...")
        self.running = False

    def _create_consumer(self, topics: List[str], from_beginning: bool = False):
        """
        Create and configure Kafka consumer.

        Args:
            topics: List of topics to subscribe to
            from_beginning: Whether to start from the beginning of topics
        """
        auto_offset_reset = 'earliest' if from_beginning else 'latest'

        self.consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.consumer_group,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=True,
            auto_commit_interval_ms=1000,
            value_deserializer=lambda m: json.loads(
                m.decode('utf-8')) if m else None,
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            consumer_timeout_ms=1000  # Timeout for batch mode
        )

        logging.info(f"Created consumer for topics: {topics}")
        logging.info(f"Consumer group: {self.consumer_group}")
        logging.info(f"Auto offset reset: {auto_offset_reset}")

    def _format_message(self, message) -> str:
        """
        Format message for display.

        Args:
            message: Kafka message

        Returns:
            Formatted string representation
        """
        timestamp = datetime.fromtimestamp(
            message.timestamp / 1000).isoformat()

        formatted = f"""
{'='*60}
Topic: {message.topic}
Partition: {message.partition}
Offset: {message.offset}
Key: {message.key}
Timestamp: {timestamp}
Value: {json.dumps(message.value, indent=2)}
{'='*60}
"""
        return formatted

    def consume_batch(self, topics: List[str], batch_size: int, from_beginning: bool = False):
        """
        Consume a batch of messages.

        Args:
            topics: Topics to consume from
            batch_size: Number of messages to consume
            from_beginning: Whether to start from beginning
        """
        logging.info(
            f"Starting batch consumption of {batch_size} messages from topics: {topics}")

        try:
            self._create_consumer(topics, from_beginning)

            if not self.consumer:
                raise RuntimeError("Failed to create Kafka consumer")

            consumed = 0
            for message in self.consumer:
                if not self.running or consumed >= batch_size:
                    break

                print(self._format_message(message))
                consumed += 1
                self.message_count += 1

                if consumed % 10 == 0:
                    logging.info(f"Consumed {consumed}/{batch_size} messages")

            logging.info(
                f"Batch consumption completed. Total messages consumed: {consumed}")

        except Exception as e:
            logging.error(f"Error during batch consumption: {e}")
            raise
        finally:
            self.close()

    def consume_continuous(self, topics: List[str], from_beginning: bool = False):
        """
        Consume messages continuously.

        Args:
            topics: Topics to consume from
            from_beginning: Whether to start from beginning
        """
        logging.info(f"Starting continuous consumption from topics: {topics}")

        try:
            self._create_consumer(topics, from_beginning)

            if not self.consumer:
                raise RuntimeError("Failed to create Kafka consumer")

            for message in self.consumer:
                if not self.running:
                    break

                print(self._format_message(message))
                self.message_count += 1

                if self.message_count % 10 == 0:
                    logging.info(
                        f"Total messages consumed: {self.message_count}")

        except Exception as e:
            logging.error(f"Error during continuous consumption: {e}")
            raise
        finally:
            self.close()

    def close(self):
        """Close the Kafka consumer."""
        if self.consumer:
            self.consumer.close()
            logging.info("Kafka consumer closed")
            logging.info(
                f"Total messages consumed in this session: {self.message_count}")


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """Main entry point."""
    setup_logging()

    parser = argparse.ArgumentParser(description='Kafka Data Consumer')
    parser.add_argument(
        '--bootstrap-servers',
        default='localhost:9092',
        help='Kafka bootstrap servers'
    )
    parser.add_argument(
        '--mode',
        choices=['batch', 'continuous'],
        default='continuous',
        help='Consumption mode'
    )
    parser.add_argument(
        '--topics',
        nargs='+',
        default=['user-events', 'product-updates', 'user-profiles'],
        help='Topics to consume from'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of messages to consume (batch mode only)'
    )
    parser.add_argument(
        '--consumer-group',
        default='data-consumer-group',
        help='Consumer group ID'
    )
    parser.add_argument(
        '--from-beginning',
        action='store_true',
        help='Start consuming from the beginning of topics'
    )

    args = parser.parse_args()

    try:
        consumer = DataConsumer(args.bootstrap_servers, args.consumer_group)

        if args.mode == 'batch':
            consumer.consume_batch(
                args.topics, args.batch_size, args.from_beginning)
        else:
            consumer.consume_continuous(args.topics, args.from_beginning)

    except KeyboardInterrupt:
        logging.info("Consumer interrupted by user")
        return 0
    except Exception as e:
        logging.error(f"Data consumption failed: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
