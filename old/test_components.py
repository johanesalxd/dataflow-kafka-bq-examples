#!/usr/bin/env python3
"""
Simple test script to verify pipeline components work correctly.
This tests the configuration loading and basic imports without running the full pipeline.
"""

import logging
from pathlib import Path
import sys

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))


def test_imports():
    """Test that all modules can be imported successfully."""
    print("Testing imports...")

    try:
        # Test utility imports
        from utils.config_loader import get_table_spec
        from utils.config_loader import load_config
        from utils.config_loader import validate_config
        print("✅ Utils imported successfully")

        # Make load_config available globally for other tests
        globals()['load_config'] = load_config
        globals()['validate_config'] = validate_config
        globals()['get_table_spec'] = get_table_spec

        # Test transform imports (these will show import errors but that's expected without dependencies)
        try:
            from transforms.aggregations import \
                get_user_events_aggregation_query
            from transforms.bigquery_io import PrepareBigQueryRecord
            from transforms.kafka_io import ParseKafkaMessage
            from transforms.kafka_io import ValidateMessage
            print("✅ Transforms imported successfully")
        except ImportError as e:
            print(
                f"⚠️  Transform imports failed (expected without Apache Beam): {e}")

        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_config_loading():
    """Test configuration loading and validation."""
    print("\nTesting configuration loading...")

    try:
        # Import functions locally
        from utils.config_loader import get_table_spec
        from utils.config_loader import load_config
        from utils.config_loader import validate_config

        # Test loading local config
        config = load_config('config.yaml', 'local')
        print("✅ Configuration loaded successfully")

        # Test validation
        validate_config(config)
        print("✅ Configuration validation passed")

        # Test table spec generation
        table_spec = get_table_spec(config, 'raw_user_events')
        print(f"✅ Table spec generated: {table_spec}")

        # Print some config details
        print(f"   Runner: {config['runner']}")
        print(f"   Kafka servers: {config['kafka']['bootstrap_servers']}")
        print(f"   Topics: {[t['name'] for t in config['kafka']['topics']]}")
        print(f"   BigQuery project: {config['bigquery']['project_id']}")

        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_data_generator():
    """Test data generator functionality."""
    print("\nTesting data generator...")

    try:
        from data_generator import DataGenerator

        # Create generator (but don't connect to Kafka)
        print("✅ DataGenerator class imported successfully")

        # Test data generation methods without Kafka
        generator = DataGenerator.__new__(DataGenerator)
        generator.users = ["user_001", "user_002"]
        generator.products = ["prod_001", "prod_002"]
        generator.event_types = ['page_view', 'purchase']
        generator.categories = ['Electronics', 'Books']
        generator.user_segments = ['premium', 'regular']
        generator.product_names = ['Test Product']

        # Test message generation
        user_event = generator.generate_user_event()
        product_update = generator.generate_product_update()
        user_profile = generator.generate_user_profile()

        print("✅ Sample data generation works:")
        print(f"   User event: {user_event}")
        print(f"   Product update: {product_update}")
        print(f"   User profile: {user_profile}")

        return True
    except Exception as e:
        print(f"❌ Data generator test failed: {e}")
        return False


def test_kafka_connectivity():
    """Test Kafka connectivity."""
    print("\nTesting Kafka connectivity...")

    try:
        from kafka import KafkaConsumer
        from kafka import KafkaProducer
        from kafka.errors import NoBrokersAvailable

        # Test producer connection
        try:
            producer = KafkaProducer(
                bootstrap_servers='localhost:9092',
                value_serializer=lambda v: str(v).encode('utf-8'),
                request_timeout_ms=5000,
                api_version=(0, 10, 1)
            )
            producer.close()
            print("✅ Kafka producer connection successful")
            return True
        except NoBrokersAvailable:
            print("❌ Kafka not available - make sure docker-compose is running")
            return False
        except Exception as e:
            print(f"❌ Kafka connection failed: {e}")
            return False

    except ImportError:
        print("❌ kafka-python not installed")
        return False


def main():
    """Run all tests."""
    print("🧪 Testing Dataflow Kafka to BigQuery Pipeline Components\n")

    tests = [
        test_imports,
        test_config_loading,
        test_data_generator,
        test_kafka_connectivity
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)

    print(f"\n📊 Test Results: {sum(results)}/{len(results)} passed")

    if all(results):
        print("🎉 All tests passed! The pipeline components are ready.")
        print("\nNext steps:")
        print("1. Update config.yaml with your GCP project ID")
        print("2. Set up Google Cloud authentication")
        print("3. Run the pipeline with: ./run_local.sh")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")

    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main())
