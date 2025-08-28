#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
PROJECT_ID="johanesa-playground-326616" # <-- IMPORTANT: SET YOUR GCP PROJECT ID HERE
BIGQUERY_TABLE="${PROJECT_ID}:dataflow_demo_local.raw_user_events"
KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
KAFKA_TOPIC="user-events"
CONSUMER_GROUP_ID="local-kafka-to-bq-consumer"
JAR_FILE="target/dataflow-kafka-bq-examples-1.0-SNAPSHOT.jar"

# --- Main Script ---

# 1. Create BigQuery dataset if it doesn't exist
echo "Creating BigQuery dataset if it doesn't exist..."
bq show --dataset ${PROJECT_ID}:dataflow_demo_local || bq mk --dataset ${PROJECT_ID}:dataflow_demo_local

# 2. Compile and package the pipeline with Maven
echo "Compiling and packaging the pipeline with Maven..."
mvn clean package

# 3. Run the pipeline
echo "Running the pipeline..."
java -jar ${JAR_FILE} \
    --runner=DirectRunner \
    --project=${PROJECT_ID} \
    --bootstrapServers=${KAFKA_BOOTSTRAP_SERVERS} \
    --topic=${KAFKA_TOPIC} \
    --outputTable=${BIGQUERY_TABLE} \
    --consumerGroupId=${CONSUMER_GROUP_ID}

echo "Pipeline finished."
