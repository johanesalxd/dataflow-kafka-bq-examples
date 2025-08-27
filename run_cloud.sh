#!/bin/bash

# Run Dataflow pipeline on Google Cloud with DataflowRunner
# This script deploys the pipeline to Google Cloud Dataflow

set -e

echo "=== Dataflow Kafka to BigQuery Demo - Cloud Runner ==="

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "ERROR: gcloud CLI is not installed"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "ERROR: Not authenticated with gcloud"
    echo "Please run: gcloud auth login"
    exit 1
fi

# Get current project
PROJECT=$(gcloud config get-value project)
if [ -z "$PROJECT" ]; then
    echo "ERROR: No default project set"
    echo "Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "Using project: $PROJECT"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Update configuration with current project
echo "Updating configuration with project: $PROJECT"
sed -i.bak "s/your-project-id/$PROJECT/g" config.yaml

# Validate required GCS buckets exist
BUCKET_NAME="${PROJECT}-dataflow-temp"
echo "Checking if GCS bucket exists: gs://$BUCKET_NAME"

if ! gsutil ls gs://$BUCKET_NAME &> /dev/null; then
    echo "Creating GCS bucket: gs://$BUCKET_NAME"
    gsutil mb gs://$BUCKET_NAME
fi

# Update config with bucket paths
sed -i.bak "s|gs://your-bucket|gs://$BUCKET_NAME|g" config.yaml

# Enable required APIs
echo "Enabling required Google Cloud APIs..."
gcloud services enable dataflow.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable storage.googleapis.com

# Create BigQuery dataset if it doesn't exist
DATASET="dataflow_demo_prod"
echo "Creating BigQuery dataset: $DATASET"
bq mk --dataset --location=US $PROJECT:$DATASET 2>/dev/null || echo "Dataset already exists"

# Run the pipeline
JOB_NAME="kafka-bq-demo-cloud-$(date +%Y%m%d-%H%M%S)"
echo "Starting Dataflow pipeline: $JOB_NAME"

python pipeline.py \
    --environment cloud \
    --config config.yaml \
    --job_name "$JOB_NAME"

echo "Pipeline submitted successfully!"
echo "Job name: $JOB_NAME"
echo "Monitor the pipeline at:"
echo "https://console.cloud.google.com/dataflow/jobs?project=$PROJECT"
