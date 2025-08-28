#!/usr/bin/env python3
"""
Enhanced script to list Kafka consumer groups with detailed information
"""

import argparse
import sys

from kafka import KafkaAdminClient
from kafka.errors import KafkaError


def list_consumer_groups_detailed(bootstrap_servers):
    """List all consumer groups with detailed information"""
    try:
        # Create admin client
        admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            client_id='detailed-consumer-group-lister'
        )

        print(f"Connecting to Kafka at: {bootstrap_servers}")
        print("=" * 60)

        # List consumer groups
        consumer_groups = admin_client.list_consumer_groups()

        if not consumer_groups:
            print("No consumer groups found via admin client.")
        else:
            print(
                f"Found {len(consumer_groups)} consumer group(s) via admin client:")
            print("-" * 50)

            for group in consumer_groups:
                # Handle both tuple and object formats
                if isinstance(group, tuple):
                    group_id = group[0]
                    group_type = group[1] if len(group) > 1 else "Unknown"
                    protocol_type = group[2] if len(group) > 2 else "Unknown"
                else:
                    group_id = group.group_id
                    group_type = group.group_type
                    protocol_type = group.protocol_type

                print(f"Group ID: {group_id}")
                print(f"Group Type: {group_type}")
                print(f"Protocol Type: {protocol_type}")

                # Try to get more details about this group
                try:
                    group_metadata = admin_client.describe_consumer_groups([
                                                                           group_id])
                    if group_id in group_metadata:
                        metadata = group_metadata[group_id]
                        print(f"State: {metadata.state}")
                        print(f"Members: {len(metadata.members)}")
                        for member in metadata.members:
                            print(f"  - Member ID: {member.member_id}")
                            print(f"    Client ID: {member.client_id}")
                except Exception as e:
                    print(f"Could not get detailed info: {e}")

                print("-" * 30)

        # Also try to check for specific consumer groups that might not show up in list
        print("\nChecking for specific consumer groups...")
        specific_groups = [
            "dataflow-kafka-to-bq-consumer",
            "data-consumer-group",
            "kafka-to-bq-flex"
        ]

        for group_id in specific_groups:
            try:
                group_metadata = admin_client.describe_consumer_groups([
                                                                       group_id])
                if group_metadata and len(group_metadata) > 0:
                    metadata = group_metadata[0]
                    print(f"Found specific group: {group_id}")
                    print(f"  State: {metadata.state}")
                    print(f"  Members: {len(metadata.members)}")
                    print(f"  Protocol: {metadata.protocol}")
                    print(f"  Protocol Type: {metadata.protocol_type}")
                    for member in metadata.members:
                        print(
                            f"    - Member: {member.member_id} (Client: {member.client_id})")
                    print("-" * 30)
            except Exception as e:
                print(f"Group {group_id} not found or error: {e}")

        # List all topics to see what's available
        print("\nAvailable topics:")
        try:
            topics = admin_client.list_topics()
            for topic in topics:
                print(f"  - {topic}")
        except Exception as e:
            print(f"Could not list topics: {e}")

    except KafkaError as e:
        print(f"Kafka error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if 'admin_client' in locals():
            admin_client.close()


def main():
    parser = argparse.ArgumentParser(
        description='List Kafka consumer groups with details')
    parser.add_argument('--bootstrap-servers',
                        default='localhost:9092',
                        help='Kafka bootstrap servers (default: localhost:9092)')

    args = parser.parse_args()

    list_consumer_groups_detailed(args.bootstrap_servers)


if __name__ == "__main__":
    main()
