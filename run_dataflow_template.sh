#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
PROJECT_ID="your-project-id" # <-- IMPORTANT: SET YOUR GCP PROJECT ID HERE
REGION="us-central1" # <-- Change to your preferred region
TEMP_BUCKET="gs://your-gcs-bucket" # <-- IMPORTANT: SET YOUR GCS BUCKET HERE
BIGQUERY_DATASET="dataflow_demo"
BIGQUERY_TABLE="${PROJECT_ID}:${BIGQUERY_DATASET}.raw_user_events_flex"
KAFKA_BOOTSTRAP_SERVERS="EXTERNAL_IP:9092" # Replace with your Kafka's EXTERNAL_IP (no http:// prefix)
KAFKA_TOPIC="user-events"
CONSUMER_GROUP_ID="dataflow-flex-kafka-to-bq-consumer"
UDF_FILE="udf/process.js"
UDF_GCS_PATH="${TEMP_BUCKET}/udf/process.js"
JOB_NAME="kafka-to-bq-flex-$(date +%Y%m%d-%H%M%S)"

# --- Main Script ---

echo "=== Dataflow Template Deployment Script ==="
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

# 3. Create BigQuery table and upload UDF to GCS
echo "Creating BigQuery table if it doesn't exist..."
bq mk --table \
--description "Table to store raw Kafka JSON payloads with timestamps" \
--time_partitioning_field=event_time \
--time_partitioning_type=DAY \
${BIGQUERY_TABLE} \
schemas/generic_table.json || echo "Table already exists"

echo "Uploading UDF to GCS..."
gsutil cp ${UDF_FILE} ${UDF_GCS_PATH}

# 4. Run the pipeline on Dataflow using Flex Template
echo "Submitting pipeline to Dataflow..."
gcloud dataflow flex-template run ${JOB_NAME} \
  --project=${PROJECT_ID} \
  --template-file-gcs-location=gs://dataflow-templates-${REGION}/latest/flex/Kafka_to_BigQuery_Flex \
  --region=${REGION} \
  --temp-location=${TEMP_BUCKET}/temp \
  --staging-location=${TEMP_BUCKET}/staging \
  --max-workers=3 \
  --parameters="\
readBootstrapServerAndTopic=${KAFKA_BOOTSTRAP_SERVERS};${KAFKA_TOPIC},\
kafkaReadAuthenticationMode=NONE,\
messageFormat=JSON,\
outputTableSpec=${BIGQUERY_TABLE},\
useBigQueryDLQ=false,\
persistKafkaKey=false,\
writeMode=SINGLE_TABLE_NAME,\
numStorageWriteApiStreams=0,\
enableCommitOffsets=true,\
kafkaReadOffset=earliest,\
javascriptTextTransformReloadIntervalMinutes=0,\
createDisposition=CREATE_IF_NEEDED,\
writeDisposition=WRITE_APPEND,\
consumerGroupId=${CONSUMER_GROUP_ID},\
javascriptTextTransformGcsPath=${UDF_GCS_PATH},\
javascriptTextTransformFunctionName=process"

echo ""
echo "=== Job Submitted Successfully ==="
echo "The pipeline has been submitted to Dataflow and is starting up..."
echo "View your job at: https://console.cloud.google.com/dataflow/jobs/${REGION}/${JOB_NAME}?project=${PROJECT_ID}"
echo "Monitor BigQuery table: https://console.cloud.google.com/bigquery?project=${PROJECT_ID}&ws=!1m5!1m4!4m3!1s${PROJECT_ID}!2s${BIGQUERY_DATASET}!3sraw_user_events_flex"
