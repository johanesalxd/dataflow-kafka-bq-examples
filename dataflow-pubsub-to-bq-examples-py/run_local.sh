#!/bin/bash

# Local Pub/Sub to BigQuery Pipeline
# This script runs the pipeline locally with DirectRunner for testing
# - Reads from Pub/Sub subscription (public taxi data)
# - Writes to BigQuery table with full schema
# - Includes pre-flight checks for all required resources

set -e

# --- Configuration ---
PROJECT_ID="johanesa-playground-326616"
REGION="us-central1"
BIGQUERY_DATASET="demo_dataset"
BIGQUERY_TABLE="taxi_events"
SUBSCRIPTION_NAME="taxi_telemetry"
PUBLIC_TOPIC="projects/pubsub-public-data/topics/taxirides-realtime"

# Full resource paths
FULL_SUBSCRIPTION="projects/${PROJECT_ID}/subscriptions/${SUBSCRIPTION_NAME}"
FULL_TABLE="${PROJECT_ID}:${BIGQUERY_DATASET}.${BIGQUERY_TABLE}"

# --- Main Script ---

echo "=== Local Pub/Sub to BigQuery Pipeline ==="
echo "Project ID: ${PROJECT_ID}"
echo "Subscription: ${SUBSCRIPTION_NAME}"
echo "BigQuery Table: ${FULL_TABLE}"
echo ""

# 1. Check/Create BigQuery dataset
echo "Checking BigQuery dataset..."
if ! bq show --dataset ${PROJECT_ID}:${BIGQUERY_DATASET} 2>/dev/null; then
    echo "Creating BigQuery dataset..."
    bq mk --dataset --location=${REGION} ${PROJECT_ID}:${BIGQUERY_DATASET}
else
    echo "BigQuery dataset already exists."
fi

# 2. Check/Create BigQuery table with schema
echo "Checking BigQuery table..."
if ! bq show ${FULL_TABLE} 2>/dev/null; then
    echo "Creating BigQuery table with schema..."
    bq mk \
        --table \
        --time_partitioning_field=publish_time \
        --time_partitioning_type=DAY \
        --clustering_fields=publish_time \
        --schema=subscription_name:STRING,message_id:STRING,publish_time:TIMESTAMP,ride_id:STRING,point_idx:INT64,latitude:FLOAT,longitude:FLOAT,timestamp:STRING,meter_reading:FLOAT,meter_increment:FLOAT,ride_status:STRING,passenger_count:INT64,attributes:STRING \
        ${FULL_TABLE}
else
    echo "BigQuery table already exists."
fi

# 3. Check/Create Pub/Sub subscription
echo "Checking Pub/Sub subscription..."
if ! gcloud pubsub subscriptions describe ${SUBSCRIPTION_NAME} --project=${PROJECT_ID} 2>/dev/null; then
    echo "Creating Pub/Sub subscription..."
    gcloud pubsub subscriptions create ${SUBSCRIPTION_NAME} \
        --project=${PROJECT_ID} \
        --topic=${PUBLIC_TOPIC}
else
    echo "Pub/Sub subscription already exists."
fi

# 4. Install Python dependencies
echo "Installing Python dependencies..."
uv sync

# 5. Run the pipeline
echo ""
echo "Running pipeline with DirectRunner..."
uv run python -m dataflow_pubsub_to_bq.pipeline \
    --runner=DirectRunner \
    --project=${PROJECT_ID} \
    --subscription=${FULL_SUBSCRIPTION} \
    --output_table=${FULL_TABLE} \
    --subscription_name=${SUBSCRIPTION_NAME} \
    --streaming

echo ""
echo "Pipeline started. Press Ctrl+C to stop."
