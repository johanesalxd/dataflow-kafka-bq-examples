#!/bin/bash

# This script provisions a Google Compute Engine VM to run Kafka.
# It creates the VM and sets up the necessary firewall rules.

set -e

# --- Configuration ---
PROJECT_ID="johanesa-playground-326616"
VM_NAME="kafka-broker-vm"
ZONE="us-central1-a"
MACHINE_TYPE="e2-standard-2"
IMAGE_FAMILY="debian-11"
IMAGE_PROJECT="debian-cloud"
BOOT_DISK_SIZE="80GB"
NETWORK_TAG="kafka-broker"
FIREWALL_RULE_NAME="allow-kafka-traffic"

# --- Main Logic ---

echo "=== Provisioning Kafka VM: $VM_NAME ==="

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

# Enable required APIs
echo "Enabling required Google Cloud APIs..."
gcloud services enable compute.googleapis.com --project="$PROJECT_ID"

# 1. Create the Compute Engine instance
echo "Creating VM instance: $VM_NAME..."
gcloud compute instances create "$VM_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --image-family="$IMAGE_FAMILY" \
    --image-project="$IMAGE_PROJECT" \
    --boot-disk-size="$BOOT_DISK_SIZE" \
    --tags="$NETWORK_TAG,http-server,https-server" \
    --quiet

# 2. Create the firewall rule
echo "Creating firewall rule: $FIREWALL_RULE_NAME..."
gcloud compute firewall-rules create "$FIREWALL_RULE_NAME" \
    --project="$PROJECT_ID" \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:9092,tcp:8080,tcp:22 \
    --source-ranges=0.0.0.0/0 \
    --target-tags="$NETWORK_TAG" \
    --quiet || echo "Firewall rule '$FIREWALL_RULE_NAME' already exists."

# 3. Get and display the external IP
EXTERNAL_IP=$(gcloud compute instances describe "$VM_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo "=== Provisioning Complete ==="
echo "VM '$VM_NAME' has been created."
echo "External IP Address: $EXTERNAL_IP"
echo ""
echo "Next steps:"
echo "1. SSH into the VM: gcloud compute ssh $VM_NAME --zone $ZONE --project $PROJECT_ID"
echo "2. Install Docker and Docker Compose on the VM."
echo "3. Update your docker-compose.yml with the external IP: $EXTERNAL_IP"
echo ""
echo "To connect to Kafka from your local machine:"
echo "  Bootstrap servers: $EXTERNAL_IP:9092"
echo ""
echo "To access Kafka UI:"
echo "  URL: http://$EXTERNAL_IP:8080"
