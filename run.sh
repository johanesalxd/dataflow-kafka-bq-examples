#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
ENV="local"
PROJECT_ID="johanesa-playground-326616" # <-- IMPORTANT: SET YOUR GCP PROJECT ID HERE
CONFIG_FILE="config.yaml"
PIPELINE_FILE="pipeline.py"

# --- Main Script ---

# 1. Set up virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# 2. Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# 3. Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Check for gcloud authentication
echo "Checking for gcloud authentication..."
if ! gcloud auth application-default print-access-token &> /dev/null; then
    echo "You are not authenticated with gcloud. Please run 'gcloud auth application-default login' and try again."
    exit 1
fi

# 5. Update project ID in config.yaml
echo "Updating project ID in ${CONFIG_FILE} to '${PROJECT_ID}'..."
sed -i "s/project_id: .*/project_id: ${PROJECT_ID}/" ${CONFIG_FILE}

# 6. Run the pipeline
echo "Running the Dataflow pipeline..."
python ${PIPELINE_FILE} \
    --config ${CONFIG_FILE} \
    --environment ${ENV}

echo "Pipeline finished."
