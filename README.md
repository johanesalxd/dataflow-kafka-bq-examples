# Dataflow Kafka BigQuery Examples

This repository contains examples for working with Kafka data streams and BigQuery integration.

## Project Structure

```
.
├── docker-compose.yml              # Kafka setup (KRaft mode, no ZooKeeper)
├── kafka-setup-comparison.md       # ZooKeeper vs KRaft comparison
├── kafka-tools/                    # Kafka producer/consumer tools
│   ├── data_generator.py           # Kafka message producer
│   ├── data_consumer.py            # Kafka message consumer
│   └── example_usage.md            # Usage examples and documentation
├── schemas/                        # JSON schemas for data validation
│   ├── user_events.json
│   ├── product_updates.json
│   └── user_profiles.json
├── utils/                          # Utility modules
│   ├── __init__.py
│   └── config_loader.py
└── old/                            # Legacy files
```

## Quick Start

1. **Start Kafka (KRaft mode - no ZooKeeper needed):**
   ```bash
   docker-compose up -d
   ```

2. **Install dependencies:**
   ```bash
   pip install kafka-python
   ```

3. **Generate sample data:**
   ```bash
   python kafka-tools/data_generator.py --mode batch --batch-size 10
   ```

4. **Consume data:**
   ```bash
   python kafka-tools/data_consumer.py --mode batch --batch-size 10 --from-beginning
   ```

5. **Access Kafka UI:**
   Open http://localhost:8080 to view topics and messages

## Features

### Modern Kafka Setup
- ✅ **KRaft mode** - No ZooKeeper dependency
- ✅ **Docker Compose** - Easy setup and teardown
- ✅ **Kafka UI** - Web interface for monitoring

### Data Tools
- ✅ **Data Generator** - Produces realistic sample data for 3 topics:
  - `user-events` - User interactions (page views, purchases, etc.)
  - `product-updates` - Product information changes
  - `user-profiles` - User profile updates
- ✅ **Data Consumer** - Flexible consumer with batch and continuous modes
- ✅ **JSON Schemas** - Data validation schemas

### Topics Generated
- **user-events**: User interactions with products
- **product-updates**: Product catalog changes
- **user-profiles**: User profile information

## Documentation

- **[Kafka Tools Usage](kafka-tools/example_usage.md)** - Detailed usage examples
- **[Kafka Setup Comparison](kafka-setup-comparison.md)** - ZooKeeper vs KRaft comparison

## Architecture

This setup uses modern **Kafka KRaft mode**:
- **Simpler**: Only Kafka + Kafka UI (no ZooKeeper)
- **Faster**: Better performance and startup time
- **Modern**: KRaft is the future of Kafka

## Connection Details

- **Kafka Broker**: `localhost:9092`
- **Kafka UI**: `http://localhost:8080`
- **Container Network**: `kafka:9093` (for inter-container communication)
