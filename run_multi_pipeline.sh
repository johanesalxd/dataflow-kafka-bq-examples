#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
PROJECT_ID="johanesa-playground-326616" # <-- IMPORTANT: SET YOUR GCP PROJECT ID HERE
REGION="us-central1" # <-- Change to your preferred region
TEMP_BUCKET="gs://johanesa-playground-326616-dataflow" # <-- IMPORTANT: SET YOUR GCS BUCKET HERE
BIGQUERY_DATASET="dataflow_demo"

# Table configurations for multi-pipeline
USER_PROFILES_TABLE="${PROJECT_ID}:${BIGQUERY_DATASET}.raw_user_profiles"
ENRICHED_EVENTS_TABLE="${PROJECT_ID}:${BIGQUERY_DATASET}.enriched_events"

# Kafka configurations
KAFKA_BOOTSTRAP_SERVERS="34.132.61.26:9092" # Replace with your Kafka's EXTERNAL_IP (no http:// prefix)
USER_EVENTS_TOPIC="user-events"
USER_PROFILES_TOPIC="user-profiles"
PRODUCT_UPDATES_TOPIC="product-updates"
CONSUMER_GROUP_ID="dataflow-multi-pipeline-consumer"
KAFKA_READ_OFFSET="earliest" # Set to "earliest" to read from beginning, "latest" for new messages only

# Job configuration
JAR_FILE="target/dataflow-kafka-bq-examples-1.0-SNAPSHOT.jar"
JOB_NAME="multi-pipeline-kafka-to-bq-$(date +%Y%m%d-%H%M%S)"

# --- Main Script ---

echo "=== Multi-Pipeline Dataflow Deployment Script ==="
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Job Name: ${JOB_NAME}"
echo "Kafka Server: ${KAFKA_BOOTSTRAP_SERVERS}"
echo "Topics: ${USER_EVENTS_TOPIC}, ${USER_PROFILES_TOPIC}, ${PRODUCT_UPDATES_TOPIC}"
echo "User Profiles Table: ${USER_PROFILES_TABLE}"
echo "Enriched Events Table: ${ENRICHED_EVENTS_TABLE}"
echo ""


# 1. Create GCS bucket if it doesn't exist
echo "Creating GCS bucket if it doesn't exist..."
gsutil ls ${TEMP_BUCKET} 2>/dev/null || gsutil mb -p ${PROJECT_ID} ${TEMP_BUCKET}

# 2. Create BigQuery dataset if it doesn't exist
echo "Creating BigQuery dataset if it doesn't exist..."
bq show --dataset ${PROJECT_ID}:${BIGQUERY_DATASET} || bq mk --dataset ${PROJECT_ID}:${BIGQUERY_DATASET}

# 3. Create BigQuery tables if they don't exist
echo "Creating user profiles BigQuery table if it doesn't exist..."
bq mk --table \
--description "Table to store user profile data from Kafka" \
${USER_PROFILES_TABLE} \
schemas/user_profiles.json || echo "User profiles table already exists"

echo "Creating enriched events BigQuery table if it doesn't exist..."
bq mk --table \
--description "Table to store enriched events with joined user and product data" \
--time_partitioning_field=processing_time \
--time_partitioning_type=DAY \
${ENRICHED_EVENTS_TABLE} \
schemas/enriched_events.json || echo "Enriched events table already exists"

# 4. Copy SQL files to resources directory for packaging
echo "Copying SQL files to resources directory..."
mkdir -p src/main/resources/udf
cp udf/user_event_aggregations.sql src/main/resources/udf/ 2>/dev/null || echo "user_event_aggregations.sql not found, skipping..."

# 5. Compile and package the pipeline with Maven
echo "Compiling and packaging the multi-pipeline with Maven..."
mvn clean package

# 6. Run the pipeline on Dataflow
# NOTE: This uses 'java -cp' approach (explicit main class specification)
echo "Submitting multi-pipeline to Dataflow..."
echo "Execution method: java -cp (with explicit main class)"
echo "Main class: com.johanesalxd.MultiPipelineExample"
echo "Kafka read offset: ${KAFKA_READ_OFFSET}"
java -cp ${JAR_FILE} com.johanesalxd.MultiPipelineExample \
    --runner=DataflowRunner \
    --project=${PROJECT_ID} \
    --region=${REGION} \
    --jobName=${JOB_NAME} \
    --tempLocation=${TEMP_BUCKET}/temp \
    --stagingLocation=${TEMP_BUCKET}/staging \
    --bootstrapServers=${KAFKA_BOOTSTRAP_SERVERS} \
    --consumerGroupId=${CONSUMER_GROUP_ID} \
    --kafkaReadOffset=${KAFKA_READ_OFFSET} \
    --userEventsTopic=${USER_EVENTS_TOPIC} \
    --userProfilesTopic=${USER_PROFILES_TOPIC} \
    --productUpdatesTopic=${PRODUCT_UPDATES_TOPIC} \
    --userProfilesTable=${USER_PROFILES_TABLE} \
    --enrichedEventsTable=${ENRICHED_EVENTS_TABLE} \
    --bigQueryProject=${PROJECT_ID} \
    --bigQueryDataset=${BIGQUERY_DATASET} \
    --streaming \
    --maxNumWorkers=3 \
    --autoscalingAlgorithm=THROUGHPUT_BASED

echo ""
echo "=== Job Submitted Successfully ==="
echo "The multi-pipeline has been submitted to Dataflow and is starting up..."
echo "Data will be written to two tables:"
echo "  - User Profiles: ${USER_PROFILES_TABLE}"
echo "  - Enriched Events: ${ENRICHED_EVENTS_TABLE}"
echo "View your job at: https://console.cloud.google.com/dataflow/jobs/${REGION}/${JOB_NAME}?project=${PROJECT_ID}"
echo "Monitor BigQuery tables:"
echo "  - User Profiles: https://console.cloud.google.com/bigquery?project=${PROJECT_ID}&ws=!1m5!1m4!4m3!1s${PROJECT_ID}!2s${BIGQUERY_DATASET}!3suser_profiles"
echo "  - Enriched Events: https://console.cloud.google.com/bigquery?project=${PROJECT_ID}&ws=!1m5!1m4!4m3!1s${PROJECT_ID}!2s${BIGQUERY_DATASET}!3senriched_events"
echo ""
echo "To view enriched events results, run:"
echo "  bq query --use_legacy_sql=false 'SELECT * FROM \`${ENRICHED_EVENTS_TABLE}\` ORDER BY processing_time DESC LIMIT 10'"
