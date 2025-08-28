#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
PROJECT_ID="johanesa-playground-326616" # <-- IMPORTANT: SET YOUR GCP PROJECT ID HERE
BIGQUERY_TABLE="${PROJECT_ID}:dataflow_demo_local.raw_user_events"
KAFKA_BOOTSTRAP_SERVERS="localhost:9092"
KAFKA_TOPIC="user-events"
JAR_FILE="target/dataflow-kafka-bq-examples-1.0-SNAPSHOT.jar"

# --- Main Script ---

# 1. Create BigQuery dataset if it doesn't exist
echo "Creating BigQuery dataset if it doesn't exist..."
bq show --dataset ${PROJECT_ID}:dataflow_demo_local || bq mk --dataset ${PROJECT_ID}:dataflow_demo_local

# 2. Update BigQuery table in KafkaToBigQuery.java
echo "Updating BigQuery table in KafkaToBigQuery.java to '${BIGQUERY_TABLE}'..."
sed -i "s/to(\".*\")/to(\"${BIGQUERY_TABLE}\")/" src/main/java/com/example/KafkaToBigQuery.java

# 3. Update Kafka bootstrap servers in KafkaToBigQuery.java
echo "Updating Kafka bootstrap servers in KafkaToBigQuery.java to '${KAFKA_BOOTSTRAP_SERVERS}'..."
sed -i "s/withBootstrapServers(\".*\")/withBootstrapServers(\"${KAFKA_BOOTSTRAP_SERVERS}\")/" src/main/java/com/example/KafkaToBigQuery.java

# 4. Update Kafka topic in KafkaToBigQuery.java
echo "Updating Kafka topic in KafkaToBigQuery.java to '${KAFKA_TOPIC}'..."
sed -i "s/withTopic(\".*\")/withTopic(\"${KAFKA_TOPIC}\")/" src/main/java/com/example/KafkaToBigQuery.java

# 5. Compile and package the pipeline with Maven
echo "Compiling and packaging the pipeline with Maven..."
mvn clean package

# 6. Run the pipeline
echo "Running the pipeline..."
java -jar ${JAR_FILE} --runner=DirectRunner --project=${PROJECT_ID}

echo "Pipeline finished."
