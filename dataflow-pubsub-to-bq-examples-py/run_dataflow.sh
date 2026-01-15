#!/bin/bash

# Dataflow Pub/Sub to BigQuery Pipeline with Runner V2
# This script runs the pipeline on Dataflow with specific scaling test configuration
# - Reads from Pub/Sub subscription (public taxi data)
# - Writes to BigQuery table with full schema
# - Uses Runner V2 with fixed 5 workers (n2-standard-4) for scaling test
# - Python SDK uses default 12 threads per vCPU (48 threads per worker, 240 total threads)
# - Expected load: ~2,000 RPS from Pub/Sub subscription

set -e

# --- Configuration ---
PROJECT_ID="your-project-id"
REGION="us-central1"
TEMP_BUCKET="gs://your-gcs-bucket"
BIGQUERY_DATASET="demo_dataset"
BIGQUERY_TABLE="taxi_events"
SUBSCRIPTION_NAME="taxi_telemetry"
PUBLIC_TOPIC="projects/pubsub-public-data/topics/taxirides-realtime"
JOB_NAME="dataflow-pubsub-to-bq-$(date +%Y%m%d-%H%M%S)"

# Full resource paths
FULL_SUBSCRIPTION="projects/${PROJECT_ID}/subscriptions/${SUBSCRIPTION_NAME}"
FULL_TABLE="${PROJECT_ID}:${BIGQUERY_DATASET}.${BIGQUERY_TABLE}"

# --- Main Script ---

echo "=== Dataflow Pub/Sub to BigQuery Pipeline (Runner V2) ==="
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Job Name: ${JOB_NAME}"
echo "Subscription: ${SUBSCRIPTION_NAME}"
echo "BigQuery Table: ${FULL_TABLE}"
echo ""
echo "Scaling Test Configuration:"
echo "  - Machine Type: n2-standard-4 (4 vCPUs, 16GB RAM)"
echo "  - Workers: 5 (fixed, no auto-scaling)"
echo "  - Threads per Worker: 48 (12 threads per vCPU × 4 vCPUs)"
echo "  - Total Processing Capacity: 240 threads (5 workers × 48)"
echo "  - Expected Load: ~2,000 RPS"
echo "  - BigQuery Write: Storage Write API with 1-second micro-batching"
echo ""

# 1. Check/Create GCS bucket
echo "Checking GCS bucket..."
if ! gsutil ls ${TEMP_BUCKET} 2>/dev/null; then
    echo "Creating GCS bucket..."
    gsutil mb -p ${PROJECT_ID} -l ${REGION} ${TEMP_BUCKET}
else
    echo "GCS bucket already exists."
fi

# 2. Check/Create BigQuery dataset
echo "Checking BigQuery dataset..."
if ! bq show --dataset ${PROJECT_ID}:${BIGQUERY_DATASET} 2>/dev/null; then
    echo "Creating BigQuery dataset..."
    bq mk --dataset --location=${REGION} ${PROJECT_ID}:${BIGQUERY_DATASET}
else
    echo "BigQuery dataset already exists."
fi

# 3. Check/Create BigQuery table with schema
echo "Checking BigQuery table..."
if ! bq show ${FULL_TABLE} 2>/dev/null; then
    echo "Creating BigQuery table with schema..."
    bq mk \
        --table \
        --time_partitioning_field=publish_time \
        --time_partitioning_type=DAY \
        --clustering_fields=publish_time \
        --schema=subscription_name:STRING,message_id:STRING,publish_time:TIMESTAMP,ride_id:STRING,point_idx:INT64,latitude:FLOAT,longitude:FLOAT,timestamp:TIMESTAMP,meter_reading:FLOAT,meter_increment:FLOAT,ride_status:STRING,passenger_count:INT64,attributes:STRING \
        ${FULL_TABLE}
else
    echo "BigQuery table already exists."
fi

# 4. Check/Create Pub/Sub subscription
echo "Checking Pub/Sub subscription..."
if ! gcloud pubsub subscriptions describe ${SUBSCRIPTION_NAME} --project=${PROJECT_ID} 2>/dev/null; then
    echo "Creating Pub/Sub subscription..."
    gcloud pubsub subscriptions create ${SUBSCRIPTION_NAME} \
        --project=${PROJECT_ID} \
        --topic=${PUBLIC_TOPIC}
else
    echo "Pub/Sub subscription already exists."
fi

# 5. Install Python dependencies
echo "Installing Python dependencies..."
uv sync

# 6. Build package wheel for Dataflow workers
echo "Building package wheel for Dataflow workers..."
uv build --wheel
WHEEL_FILE=$(ls -t dist/*.whl | head -1)
echo "Built wheel: ${WHEEL_FILE}"

# 7. Submit pipeline to Dataflow
echo ""
echo "Submitting pipeline to Dataflow with Runner V2..."
uv run python -m dataflow_pubsub_to_bq.pipeline \
    --runner=DataflowRunner \
    --project=${PROJECT_ID} \
    --region=${REGION} \
    --job_name=${JOB_NAME} \
    --temp_location=${TEMP_BUCKET}/temp \
    --staging_location=${TEMP_BUCKET}/staging \
    --subscription=${FULL_SUBSCRIPTION} \
    --output_table=${FULL_TABLE} \
    --subscription_name=${SUBSCRIPTION_NAME} \
    --streaming \
    --experiments=use_runner_v2 \
    --sdk_container_image=apache/beam_python3.12_sdk:2.70.0 \
    --extra_packages=${WHEEL_FILE} \
    --machine_type=n2-standard-4 \
    --num_workers=5 \
    --max_num_workers=5 \
    --enable_streaming_engine

echo ""
echo "=== Job Submitted Successfully ==="
echo "The pipeline has been submitted to Dataflow and is starting up..."
echo ""
echo "View job at:"
echo "https://console.cloud.google.com/dataflow/jobs/${REGION}/${JOB_NAME}?project=${PROJECT_ID}"
echo ""
echo "Monitor BigQuery table at:"
echo "https://console.cloud.google.com/bigquery?project=${PROJECT_ID}&ws=!1m5!1m4!4m3!1s${PROJECT_ID}!2s${BIGQUERY_DATASET}!3s${BIGQUERY_TABLE}"
echo ""
echo "Scaling Test Metrics to Monitor:"
echo "  1. System Lag - Should remain low (<10s) if throughput is adequate"
echo "  2. Throughput - Should be ~2,000 elements/sec"
echo "  3. CPU Utilization - Watch for bottlenecks"
echo "  4. Worker Thread Usage - 48 threads per worker (default for n2-standard-4)"
