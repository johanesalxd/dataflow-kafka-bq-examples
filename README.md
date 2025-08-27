# Dataflow Kafka to BigQuery Demo

A comprehensive Apache Beam pipeline that demonstrates streaming data from Kafka to BigQuery with dual processing paths: raw data ingestion and real-time aggregations using Beam SQL.

## 🏗️ Architecture

```
Kafka Topics                    Processing                      BigQuery Tables
============                    ==========                      ===============

user-events    ──┬──> Raw ──────────────────────────────> raw_user_events
                 └──> Window + Aggregate ────────────────> user_events_agg
                      (count events per user/window)

product-updates ──┬──> Raw ──────────────────────────────> raw_product_updates
                  └──> Window + Aggregate ────────────────> product_updates_agg
                       (count updates per product/window)

user-profiles ───┬──> Raw ──────────────────────────────> raw_user_profiles
                 └──> Window + Aggregate ────────────────> user_profiles_agg
                      (count profile changes/window)
```

## ✨ Features

- **Multi-source streaming**: Processes 3 independent Kafka topics
- **Dual processing paths**: Raw data ingestion + real-time aggregations
- **Beam SQL integration**: Uses SQL for windowed aggregations
- **Dead Letter Queue (DLQ)**: Handles failed records gracefully
- **Runner flexibility**: Supports both DirectRunner (local) and DataflowRunner (cloud)
- **Production-ready**: Includes error handling, monitoring, and configuration management

## 📋 Prerequisites

### Local Development
- Python 3.8+
- Docker and Docker Compose
- Google Cloud SDK (gcloud)
- Google Cloud Project with billing enabled

### Google Cloud Setup
- BigQuery API enabled
- Dataflow API enabled
- Cloud Storage API enabled
- Service account with appropriate permissions

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/johanesalxd/dataflow-kafka-bq-examples.git
cd dataflow-kafka-bq-examples

# Update configuration with your GCP project
sed -i 's/your-project-id/YOUR_ACTUAL_PROJECT_ID/g' config.yaml
```

### 2. Start Local Kafka

```bash
# Start Kafka and Zookeeper
docker-compose up -d

# Verify Kafka is running
docker-compose ps

# Access Kafka UI (optional)
open http://localhost:8080
```

### 3. Set up Google Cloud Authentication

```bash
# Authenticate with Google Cloud
gcloud auth login
gcloud auth application-default login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Create BigQuery dataset
bq mk --dataset --location=US YOUR_PROJECT_ID:dataflow_demo_local
```

### 4. Generate Sample Data

```bash
# Install dependencies
pip install kafka-python

# Generate continuous sample data
python data_generator.py --mode continuous --rate 30

# Or generate batch data
python data_generator.py --mode batch --batch-size 100
```

### 5. Run the Pipeline

#### Local Execution (DirectRunner)
```bash
./run_local.sh
```

#### Cloud Execution (DataflowRunner)
```bash
./run_cloud.sh
```

## 📊 Data Model

### User Events (`user-events` topic)
```json
{
  "event_id": "evt_12345678",
  "user_id": "user_001",
  "event_type": "page_view",
  "product_id": "prod_456",
  "timestamp": "2025-01-27T10:30:00Z"
}
```

### Product Updates (`product-updates` topic)
```json
{
  "product_id": "prod_456",
  "product_name": "Wireless Headphones",
  "price": 99.99,
  "category": "Electronics",
  "timestamp": "2025-01-27T10:00:00Z"
}
```

### User Profiles (`user-profiles` topic)
```json
{
  "user_id": "user_001",
  "username": "john_doe",
  "user_segment": "premium",
  "registration_date": "2024-01-15",
  "timestamp": "2025-01-27T09:00:00Z"
}
```

## 🔧 Configuration

### Environment Configuration (`config.yaml`)

The pipeline supports two environments:

- **local**: Uses DirectRunner for local development
- **cloud**: Uses DataflowRunner for production deployment

Key configuration sections:
- `kafka`: Bootstrap servers, topics, consumer groups
- `bigquery`: Project, dataset, table specifications
- `pipeline`: Window duration, streaming settings
- `gcp`: Cloud-specific settings (region, buckets, service accounts)

### Customizing Window Duration

```yaml
pipeline:
  window_duration_seconds: 60  # 1-minute windows for local
  # window_duration_seconds: 300  # 5-minute windows for production
```

## 📈 Monitoring and Observability

### Local Monitoring
- Pipeline logs in terminal output
- Kafka UI: http://localhost:8080
- BigQuery console for data verification

### Cloud Monitoring
- Dataflow console: https://console.cloud.google.com/dataflow
- BigQuery console: https://console.cloud.google.com/bigquery
- Cloud Logging for detailed logs

### Key Metrics to Monitor
- Message processing rate
- DLQ record count
- BigQuery insert success rate
- Pipeline lag and throughput

## 🗂️ Project Structure

```
dataflow-kafka-bq-examples/
├── pipeline.py                 # Main pipeline logic
├── data_generator.py           # Sample data generator
├── config.yaml                 # Configuration file
├── docker-compose.yml          # Local Kafka setup
├── requirements.txt            # Python dependencies
├── setup.py                    # Package setup for Dataflow
├── run_local.sh               # Local execution script
├── run_cloud.sh               # Cloud execution script
├── transforms/                 # Modular transforms
│   ├── kafka_io.py            # Kafka I/O operations
│   ├── aggregations.py        # Beam SQL aggregations
│   └── bigquery_io.py         # BigQuery I/O operations
├── utils/                      # Utility modules
│   └── config_loader.py       # Configuration management
└── schemas/                    # BigQuery table schemas
    ├── user_events.json
    ├── product_updates.json
    └── user_profiles.json
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Kafka Connection Issues
```bash
# Check if Kafka is running
docker-compose ps

# Restart Kafka
docker-compose down && docker-compose up -d

# Check Kafka logs
docker-compose logs kafka
```

#### 2. BigQuery Permission Issues
```bash
# Verify authentication
gcloud auth list

# Check project permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID
```

#### 3. Pipeline Import Errors
```bash
# Install dependencies in virtual environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 4. Schema Validation Errors
- Check that sample data matches the expected schema
- Verify BigQuery table schemas are correctly defined
- Review DLQ tables for failed records

### Debugging Tips

1. **Enable debug logging**:
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Check DLQ tables** for failed records:
   ```sql
   SELECT * FROM `project.dataset.dlq_user_events`
   ORDER BY processing_time DESC LIMIT 10;
   ```

3. **Monitor pipeline metrics** in Dataflow console

4. **Verify data flow** by checking record counts:
   ```sql
   SELECT COUNT(*) FROM `project.dataset.raw_user_events`;
   SELECT COUNT(*) FROM `project.dataset.user_events_agg`;
   ```

## 🚀 Extending the Pipeline

### Adding New Topics

1. **Update configuration**:
   ```yaml
   topics:
     - name: "new-topic"
       raw_table: "raw_new_topic"
       agg_table: "new_topic_agg"
       dlq_table: "dlq_new_topic"
   ```

2. **Create BigQuery schema**:
   ```bash
   # Create schemas/new_topic.json
   ```

3. **Add aggregation logic**:
   ```python
   # Update transforms/aggregations.py
   def get_new_topic_aggregation_query():
       return "SELECT ..."
   ```

### Future Enhancements

- **3-way stream joins**: Join user events, product updates, and user profiles
- **Real-time ML predictions**: Add ML model inference
- **Advanced windowing**: Implement session windows or sliding windows
- **Schema evolution**: Handle schema changes gracefully
- **Exactly-once processing**: Implement idempotent processing

## 📚 References

- [Apache Beam Documentation](https://beam.apache.org/documentation/)
- [Google Cloud Dataflow](https://cloud.google.com/dataflow/docs)
- [BigQuery Streaming](https://cloud.google.com/bigquery/docs/streaming-data-into-bigquery)
- [Kafka Documentation](https://kafka.apache.org/documentation/)

## 📄 License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 💡 Demo Use Cases

This pipeline demonstrates several real-world streaming patterns:

1. **E-commerce Analytics**: Track user behavior and product performance
2. **Real-time Dashboards**: Power live analytics dashboards
3. **Data Lake Ingestion**: Raw data preservation for future analysis
4. **Stream Processing**: Real-time aggregations and transformations
5. **Error Handling**: Robust error handling with DLQ patterns

Perfect for demonstrating modern data engineering practices with Apache Beam and Google Cloud!
