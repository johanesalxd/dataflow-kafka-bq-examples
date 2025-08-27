"""
Data generator for Kafka topics.
Generates sample data for user-events, product-updates, and user-profiles topics.
"""

import argparse
from datetime import datetime
from datetime import timedelta
import json
import logging
import random
import time
from typing import Any, Dict, List
import uuid

from kafka import KafkaProducer


class DataGenerator:
    """Generate sample data for Kafka topics."""

    def __init__(self, bootstrap_servers: str):
        """
        Initialize the data generator.

        Args:
            bootstrap_servers: Kafka bootstrap servers
        """
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )

        # Sample data for generation
        self.users = [f"user_{i:03d}" for i in range(1, 101)]  # 100 users
        self.products = [f"prod_{i:03d}" for i in range(1, 51)]  # 50 products
        self.event_types = ['page_view', 'add_to_cart',
                            'purchase', 'remove_from_cart']
        self.categories = ['Electronics',
                           'Books', 'Clothing', 'Home', 'Sports']
        self.user_segments = ['premium', 'regular', 'new']
        self.product_names = [
            'Wireless Headphones', 'Laptop Computer', 'Coffee Maker', 'Running Shoes',
            'Smartphone', 'Tablet', 'Desk Chair', 'Monitor', 'Keyboard', 'Mouse',
            'Book - Fiction', 'Book - Non-fiction', 'T-Shirt', 'Jeans', 'Jacket',
            'Blender', 'Toaster', 'Vacuum Cleaner', 'Basketball', 'Tennis Racket'
        ]

    def generate_user_event(self) -> Dict[str, Any]:
        """Generate a user event."""
        return {
            'event_id': f"evt_{uuid.uuid4().hex[:8]}",
            'user_id': random.choice(self.users),
            'event_type': random.choice(self.event_types),
            'product_id': random.choice(self.products),
            'timestamp': datetime.utcnow().isoformat()
        }

    def generate_product_update(self) -> Dict[str, Any]:
        """Generate a product update."""
        return {
            'product_id': random.choice(self.products),
            'product_name': random.choice(self.product_names),
            'price': round(random.uniform(10.0, 500.0), 2),
            'category': random.choice(self.categories),
            'timestamp': datetime.utcnow().isoformat()
        }

    def generate_user_profile(self) -> Dict[str, Any]:
        """Generate a user profile update."""
        user_id = random.choice(self.users)
        return {
            'user_id': user_id,
            'username': f"username_{user_id.split('_')[1]}",
            'user_segment': random.choice(self.user_segments),
            'registration_date': (datetime.utcnow() - timedelta(days=random.randint(1, 365))).date().isoformat(),
            'timestamp': datetime.utcnow().isoformat()
        }

    def send_message(self, topic: str, message: Dict[str, Any], key: str = None):
        """
        Send a message to Kafka topic.

        Args:
            topic: Kafka topic name
            message: Message to send
            key: Optional message key
        """
        try:
            future = self.producer.send(topic, value=message, key=key)
            # Wait for the message to be sent
            record_metadata = future.get(timeout=10)
            logging.debug(f"Sent message to {topic}: {message}")
            return record_metadata
        except Exception as e:
            logging.error(f"Failed to send message to {topic}: {e}")
            raise

    def generate_batch(self, topic: str, count: int):
        """
        Generate a batch of messages for a topic.

        Args:
            topic: Topic name
            count: Number of messages to generate
        """
        logging.info(f"Generating {count} messages for topic: {topic}")

        for i in range(count):
            if topic == 'user-events':
                message = self.generate_user_event()
                key = message['user_id']
            elif topic == 'product-updates':
                message = self.generate_product_update()
                key = message['product_id']
            elif topic == 'user-profiles':
                message = self.generate_user_profile()
                key = message['user_id']
            else:
                raise ValueError(f"Unknown topic: {topic}")

            self.send_message(topic, message, key)

            # Small delay to simulate real-time data
            time.sleep(0.1)

        logging.info(f"Completed generating {count} messages for {topic}")

    def generate_continuous(self, topics: List[str], messages_per_minute: int = 60):
        """
        Generate continuous stream of messages.

        Args:
            topics: List of topics to generate data for
            messages_per_minute: Rate of message generation per topic
        """
        logging.info(f"Starting continuous generation for topics: {topics}")
        logging.info(
            f"Rate: {messages_per_minute} messages per minute per topic")

        interval = 60.0 / messages_per_minute  # seconds between messages

        try:
            while True:
                for topic in topics:
                    if topic == 'user-events':
                        message = self.generate_user_event()
                        key = message['user_id']
                    elif topic == 'product-updates':
                        message = self.generate_product_update()
                        key = message['product_id']
                    elif topic == 'user-profiles':
                        message = self.generate_user_profile()
                        key = message['user_id']
                    else:
                        continue

                    self.send_message(topic, message, key)
                    time.sleep(interval / len(topics))

        except KeyboardInterrupt:
            logging.info("Stopping continuous generation...")
        finally:
            self.close()

    def close(self):
        """Close the Kafka producer."""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logging.info("Kafka producer closed")


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """Main entry point."""
    setup_logging()

    parser = argparse.ArgumentParser(description='Kafka Data Generator')
    parser.add_argument(
        '--bootstrap-servers',
        default='localhost:9092',
        help='Kafka bootstrap servers'
    )
    parser.add_argument(
        '--mode',
        choices=['batch', 'continuous'],
        default='continuous',
        help='Generation mode'
    )
    parser.add_argument(
        '--topics',
        nargs='+',
        default=['user-events', 'product-updates', 'user-profiles'],
        help='Topics to generate data for'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of messages per batch (batch mode only)'
    )
    parser.add_argument(
        '--rate',
        type=int,
        default=60,
        help='Messages per minute per topic (continuous mode only)'
    )

    args = parser.parse_args()

    try:
        generator = DataGenerator(args.bootstrap_servers)

        if args.mode == 'batch':
            for topic in args.topics:
                generator.generate_batch(topic, args.batch_size)
        else:
            generator.generate_continuous(args.topics, args.rate)

    except Exception as e:
        logging.error(f"Data generation failed: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
