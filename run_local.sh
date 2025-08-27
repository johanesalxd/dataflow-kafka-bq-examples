#!/bin/bash

# Run Dataflow pipeline locally with DirectRunner
# This script sets up the environment and runs the pipeline

set -e

echo "=== Dataflow Kafka to BigQuery Demo - Local Runner ==="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if Kafka is running
echo "Checking Kafka connectivity..."
if ! nc -z localhost 9092; then
    echo "ERROR: Kafka is not running on localhost:9092"
    echo "Please start Kafka using: docker-compose up -d"
    exit 1
fi

# Update configuration with your GCP project
echo "Please ensure you have updated config.yaml with your GCP project ID"
echo "Current project in config:"
grep "project_id" config.yaml

# Set Google Cloud credentials if not already set
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "WARNING: GOOGLE_APPLICATION_CREDENTIALS not set"
    echo "Please set it to your service account key file path"
    echo "export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json"
fi

# Run the pipeline
echo "Starting Dataflow pipeline with DirectRunner..."
python pipeline.py \
    --environment local \
    --config config.yaml \
    --job_name "kafka-bq-demo-local-$(date +%Y%m%d-%H%M%S)"

echo "Pipeline started successfully!"
echo "Monitor the pipeline output in the terminal."
echo "To stop the pipeline, press Ctrl+C"
