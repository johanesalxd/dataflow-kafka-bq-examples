#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
PROJECT_ID="your-project-id" # <-- IMPORTANT: SET YOUR GCP PROJECT ID HERE
REGION="us-central1" # <-- Change to your preferred region
TEMP_BUCKET="gs://your-gcs-bucket" # <-- IMPORTANT: SET YOUR GCS BUCKET HERE
BIGQUERY_DATASET="dataflow_demo"
BIGQUERY_TABLE="${PROJECT_ID}:${BIGQUERY_DATASET}.raw_user_events"
KAFKA_BOOTSTRAP_SERVERS="EXTERNAL_IP:9092" # Replace with your Kafka's EXTERNAL_IP (no http:// prefix)
KAFKA_TOPIC="user-events"
CONSUMER_GROUP_ID="dataflow-kafka-to-bq-consumer"
JAR_FILE="target/dataflow-kafka-bq-examples-1.0-SNAPSHOT.jar"
JOB_NAME="kafka-to-bq-$(date +%Y%m%d-%H%M%S)"

# --- Main Script ---

echo "=== Dataflow Deployment Script ==="
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Job Name: ${JOB_NAME}"
echo "Kafka Server: ${KAFKA_BOOTSTRAP_SERVERS}"
echo "BigQuery Table: ${BIGQUERY_TABLE}"
echo ""

# 1. Create GCS bucket if it doesn't exist
echo "Creating GCS bucket if it doesn't exist..."
gsutil ls ${TEMP_BUCKET} 2>/dev/null || gsutil mb -p ${PROJECT_ID} ${TEMP_BUCKET}

# 2. Create BigQuery dataset if it doesn't exist
echo "Creating BigQuery dataset if it doesn't exist..."
bq show --dataset ${PROJECT_ID}:${BIGQUERY_DATASET} || bq mk --dataset ${PROJECT_ID}:${BIGQUERY_DATASET}

# 3. Compile and package the pipeline with Maven
echo "Compiling and packaging the pipeline with Maven..."
mvn clean package

# 4. Run the pipeline on Dataflow
echo "Submitting pipeline to Dataflow..."
java -jar ${JAR_FILE} \
    --runner=DataflowRunner \
    --project=${PROJECT_ID} \
    --region=${REGION} \
    --jobName=${JOB_NAME} \
    --tempLocation=${TEMP_BUCKET}/temp \
    --stagingLocation=${TEMP_BUCKET}/staging \
    --bootstrapServers=${KAFKA_BOOTSTRAP_SERVERS} \
    --topic=${KAFKA_TOPIC} \
    --outputTable=${BIGQUERY_TABLE} \
    --consumerGroupId=${CONSUMER_GROUP_ID} \
    --streaming \
    --maxNumWorkers=3 \
    --autoscalingAlgorithm=THROUGHPUT_BASED

echo ""
echo "=== Job Submitted Successfully ==="
echo "The pipeline has been submitted to Dataflow and is starting up..."
echo "View your job at: https://console.cloud.google.com/dataflow/jobs/${REGION}/${JOB_NAME}?project=${PROJECT_ID}"
echo "Monitor BigQuery table: https://console.cloud.google.com/bigquery?project=${PROJECT_ID}&ws=!1m5!1m4!4m3!1s${PROJECT_ID}!2s${BIGQUERY_DATASET}!3sraw_user_events"
