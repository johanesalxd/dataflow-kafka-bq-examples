# Pub/Sub to BigQuery Pipeline (Python)

Python implementation of a streaming pipeline that reads taxi ride data from Google Cloud Pub/Sub and writes to BigQuery.

## Architecture

```
Pub/Sub (taxirides-realtime) -> Dataflow Pipeline -> BigQuery (taxi_events)
```

## Features

- Reads from public Pub/Sub topic (taxirides-realtime)
- Parses taxi ride JSON messages
- Captures Pub/Sub metadata (subscription_name, message_id, publish_time, attributes)
- Writes to partitioned and clustered BigQuery table
- Uses BigQuery Storage Write API for optimal performance
- Micro-batching with 1-second flush intervals
- Supports both local (DirectRunner) and production (DataflowRunner with Runner V2)

## Project Structure

```
dataflow-pubsub-to-bq-examples-py/
├── README.md                 # This file
├── pyproject.toml           # Project configuration and dependencies (uv)
├── run_local.sh             # Local testing script
├── run_dataflow.sh          # Production Dataflow deployment script
└── dataflow_pubsub_to_bq/
    ├── __init__.py
    ├── pipeline.py          # Main pipeline code
    ├── pipeline_options.py  # Custom pipeline options
    └── transforms/
        ├── __init__.py
        └── json_to_tablerow.py  # JSON parsing transform
```

## Input Data Format

The pipeline reads taxi ride events from the public Pub/Sub topic with this structure:

```json
{
  "ride_id": "7da878a4-37ce-4aa6-a899-07d4054afe96",
  "point_idx": 267,
  "latitude": 40.76561,
  "longitude": -73.96572,
  "timestamp": "2023-07-10T19:00:33.56833-04:00",
  "meter_reading": 11.62449,
  "meter_increment": 0.043537416,
  "ride_status": "enroute",
  "passenger_count": 1
}
```

## BigQuery Output Schema

```
subscription_name: STRING
message_id: STRING
publish_time: TIMESTAMP (partitioned, clustered)
ride_id: STRING
point_idx: INT64
latitude: FLOAT
longitude: FLOAT
timestamp: TIMESTAMP
meter_reading: FLOAT
meter_increment: FLOAT
ride_status: STRING
passenger_count: INT64
attributes: STRING
```

## Prerequisites

- Google Cloud Project with billing enabled
- APIs enabled: Dataflow, Pub/Sub, BigQuery, Cloud Storage
- gcloud CLI configured
- Python 3.9+
- uv package manager

## Setup

### Install uv (if not installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or on macOS/Linux with Homebrew:

```bash
brew install uv
```

### Install Project Dependencies

```bash
cd dataflow-pubsub-to-bq-examples-py
uv sync
```

This will create a virtual environment and install all dependencies defined in `pyproject.toml`.

## Usage

### Local Testing (DirectRunner)

```bash
./run_local.sh
```

This script will:
1. Check/create BigQuery dataset
2. Check/create BigQuery table with schema
3. Check/create Pub/Sub subscription
4. Install Python dependencies
5. Run pipeline locally with DirectRunner

### Production Deployment (DataflowRunner)

```bash
./run_dataflow.sh
```

This script will:
1. Check/create GCS bucket for temp/staging
2. Check/create BigQuery dataset
3. Check/create BigQuery table with schema
4. Check/create Pub/Sub subscription
5. Install Python dependencies
6. Submit pipeline to Dataflow with Runner V2

## Performance Optimizations

### BigQuery Storage Write API

This pipeline uses the **BigQuery Storage Write API** for optimal performance:

| Feature | Benefit |
|---------|---------|
| Auto-batching | Batches rows internally before committing |
| Exactly-once semantics | Built-in deduplication |
| Lower cost | First 2 TB/month free, then $0.025/GB (vs $0.05/GB for legacy streaming) |
| Higher throughput | Better for high-volume streaming (2,000+ RPS) |
| Micro-batching | `triggering_frequency=1` flushes every 1 second |

**Implementation:**
```python
bigquery.WriteToBigQuery(
    method=bigquery.WriteToBigQuery.Method.STORAGE_WRITE_API,
    triggering_frequency=1,  # Flush every 1 second
)
```

This provides automatic micro-batching without manual `GroupIntoBatches` transforms.

### Alternative: Legacy Streaming API with Count-Based Batching

If you need to use the **legacy STREAMING_INSERTS API** with count-based batching (e.g., "100 records OR 1 second, whichever comes first"), you can use `GroupIntoBatches`:

```python
import random
from apache_beam.transforms.util import GroupIntoBatches

# In pipeline.py
(messages
 | 'ParseMessages' >> beam.ParDo(
     ParsePubSubMessage(custom_options.subscription_name)
 )
 | 'AddRandomKeys' >> beam.Map(lambda x: (random.randint(0, 4), x))  # 5 shards for parallelism
 | 'BatchMessages' >> GroupIntoBatches.WithShardedKey(
     batch_size=100,  # Flush after 100 records
     max_buffering_duration_secs=1,  # OR after 1 second
 )
 | 'ExtractBatches' >> beam.FlatMapTuple(lambda k, v: v)
 | 'WriteToBigQuery' >> bigquery.WriteToBigQuery(
     table=custom_options.output_table,
     schema={'fields': get_bigquery_schema()},
     write_disposition=bigquery.BigQueryDisposition.WRITE_APPEND,
     create_disposition=bigquery.BigQueryDisposition.CREATE_IF_NEEDED,
     method=bigquery.WriteToBigQuery.Method.STREAMING_INSERTS,  # Legacy API
 ))
```

**Trade-offs:**
- **Pros:** Exact control over batch size (100 records OR 1 second trigger)
- **Cons:** Higher cost ($0.05/GB vs $0.025/GB), requires sharding for parallelism, more complex code
- **When to use:** When you need exact count-based triggering or are using legacy systems

**Note:** For production workloads, the Storage Write API is strongly recommended over legacy streaming inserts.

## Performance Results

### Production Test Results

Tested with the configuration below, the pipeline achieved excellent performance:

| Metric | Result |
|--------|--------|
| **Target Throughput** | 2,000 RPS |
| **Sustained Throughput** | **3,400+ RPS** |
| **Performance vs Target** | **170% (exceeds target)** |
| **Sustained Range** | 3,300 - 3,500 RPS (stable) |
| **Peak Throughput (Backlog Catchup)** | **58,630+ RPS** |
| **Peak Scaling Factor** | **29x target, 17x sustained** |

**Key Findings:**
- The Python SDK with Storage Write API and Runner V2 easily handles high-volume streaming workloads (2k+ RPS)
- During backlog catchup scenarios, the pipeline can scale to **58k+ RPS** to clear accumulated messages
- Demonstrates excellent burst capacity for handling traffic spikes or recovering from downtime

## Scaling Analysis

### Dataflow Runner V2 Configuration

The production deployment uses these settings:

| Setting | Value | Notes |
|---------|-------|-------|
| Runner | DataflowRunner with Runner V2 | Required for Python SDK |
| Machine Type | n2-standard-4 | 4 vCPUs, 16 GB RAM |
| Workers | 5 (fixed) | No auto-scaling |
| Threads per Worker | 48 (default) | 12 threads per vCPU × 4 vCPUs |
| Total Capacity | 240 threads | 5 workers × 48 threads |
| Actual Load | ~3,400 RPS | From Pub/Sub subscription |
| Per-Thread Load | ~14 messages/sec | 3,400 / 240 threads |

### Thread Configuration

The Python SDK on Dataflow uses **12 threads per vCPU** by default. For n2-standard-4 machines (4 vCPUs), this means:
- 12 threads/vCPU × 4 vCPUs = **48 threads per worker**
- 5 workers × 48 threads = **240 total threads**

This is sufficient for processing 3,400+ RPS with low system lag.

### Monitoring

Monitor the pipeline performance at:

- Dataflow console: https://console.cloud.google.com/dataflow
- BigQuery: https://console.cloud.google.com/bigquery

Key metrics to watch:
- System lag (data freshness)
- Throughput (elements/sec)
- CPU utilization per worker
- Memory usage per worker

## Configuration

### run_local.sh
Edit these variables:
- `PROJECT_ID`: Your GCP project ID
- `REGION`: GCP region for resources
- `BIGQUERY_DATASET`: BigQuery dataset name
- `SUBSCRIPTION_NAME`: Pub/Sub subscription name

### run_dataflow.sh
Edit these variables:
- `PROJECT_ID`: Your GCP project ID
- `REGION`: GCP region for Dataflow job
- `TEMP_BUCKET`: GCS bucket for temp/staging
- `BIGQUERY_DATASET`: BigQuery dataset name
- `SUBSCRIPTION_NAME`: Pub/Sub subscription name

## Troubleshooting

### High System Lag

If system lag is increasing:
1. Increase number of workers (`--num_workers`)
2. Use larger machine type (`--machine_type=n2-standard-8`)
3. Check BigQuery write quota limits

### OOM Errors

If workers run out of memory:
1. Reduce `--number_of_worker_harness_threads` (max 12)
2. Use machine type with more RAM
3. Check for memory leaks in transforms

### Slow BigQuery Writes

If BigQuery is the bottleneck:
1. Enable Streaming Engine (`--enable_streaming_engine`)
2. Check BigQuery streaming insert quota
3. Consider batch writes with windowing

## License

This project is provided as-is for educational and testing purposes.
