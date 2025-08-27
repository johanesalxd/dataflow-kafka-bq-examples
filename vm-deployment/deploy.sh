#!/bin/bash

# Kafka VM Deployment Automation Script
# This script automates the entire Kafka VM deployment process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if required tools are installed
check_prerequisites() {
    print_status "Checking prerequisites..."

    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi

    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "No active gcloud authentication found. Please run 'gcloud auth login'"
        exit 1
    fi

    print_success "Prerequisites check passed"
}

# Function to get user input
get_user_input() {
    print_status "Getting deployment configuration..."

    # Get project ID
    DEFAULT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
    read -p "Enter your GCP Project ID [$DEFAULT_PROJECT]: " PROJECT_ID
    PROJECT_ID=${PROJECT_ID:-$DEFAULT_PROJECT}

    if [ -z "$PROJECT_ID" ]; then
        print_error "Project ID is required"
        exit 1
    fi

    # Get zone
    read -p "Enter deployment zone [us-central1-a]: " ZONE
    ZONE=${ZONE:-us-central1-a}

    # Get VM name
    read -p "Enter VM name [kafka-vm]: " VM_NAME
    VM_NAME=${VM_NAME:-kafka-vm}

    print_success "Configuration collected"
    echo "  Project ID: $PROJECT_ID"
    echo "  Zone: $ZONE"
    echo "  VM Name: $VM_NAME"
}

# Function to provision VM
provision_vm() {
    print_status "Provisioning VM..."

    # Update the provision script with user inputs
    sed -i.bak "s/PROJECT_ID=\".*\"/PROJECT_ID=\"$PROJECT_ID\"/" provision_kafka_vm.sh
    sed -i.bak "s/ZONE=\".*\"/ZONE=\"$ZONE\"/" provision_kafka_vm.sh
    sed -i.bak "s/VM_NAME=\".*\"/VM_NAME=\"$VM_NAME\"/" provision_kafka_vm.sh

    # Run provision script
    chmod +x provision_kafka_vm.sh
    ./provision_kafka_vm.sh

    # Get VM external IP
    VM_IP=$(gcloud compute instances describe $VM_NAME --zone=$ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

    if [ -z "$VM_IP" ]; then
        print_error "Failed to get VM external IP"
        exit 1
    fi

    print_success "VM provisioned successfully"
    print_success "VM External IP: $VM_IP"

    # Save IP for later use
    echo "$VM_IP" > .vm_ip
}

# Function to setup Docker on VM
setup_docker() {
    print_status "Setting up Docker on VM..."

    # Wait for VM to be ready
    print_status "Waiting for VM to be ready..."
    sleep 30

    # Copy setup script to VM
    gcloud compute scp setup_kafka_vm.sh $VM_NAME:~/ --zone=$ZONE --quiet

    # Run setup script on VM
    gcloud compute ssh $VM_NAME --zone=$ZONE --command="chmod +x setup_kafka_vm.sh && ./setup_kafka_vm.sh" --quiet

    print_success "Docker setup completed"
}

# Function to deploy Kafka
deploy_kafka() {
    print_status "Deploying Kafka..."

    VM_IP=$(cat .vm_ip)

    # Update docker-compose file with VM IP
    sed "s/34\.133\.182\.34/$VM_IP/g" docker-compose-vm.yml > docker-compose-updated.yml

    # Copy docker-compose file to VM
    gcloud compute scp docker-compose-updated.yml $VM_NAME:~/docker-compose.yml --zone=$ZONE --quiet

    # Start Kafka on VM
    gcloud compute ssh $VM_NAME --zone=$ZONE --command="docker-compose up -d" --quiet

    # Wait for Kafka to start
    print_status "Waiting for Kafka to start..."
    sleep 60

    # Verify Kafka is running
    if gcloud compute ssh $VM_NAME --zone=$ZONE --command="docker-compose ps | grep kafka | grep Up" --quiet; then
        print_success "Kafka deployed successfully"
    else
        print_error "Kafka deployment failed"
        exit 1
    fi

    # Clean up temporary file
    rm -f docker-compose-updated.yml
}

# Function to update local config
update_config() {
    print_status "Updating local configuration..."

    VM_IP=$(cat .vm_ip)

    # Update config.yaml in parent directory
    if [ -f "../config.yaml" ]; then
        sed -i.bak "s/bootstrap_servers: \".*\"/bootstrap_servers: \"$VM_IP:9092\"/" ../config.yaml
        print_success "config.yaml updated with VM IP: $VM_IP:9092"
    else
        print_warning "config.yaml not found in parent directory"
    fi
}

# Function to test deployment
test_deployment() {
    print_status "Testing deployment..."

    VM_IP=$(cat .vm_ip)

    # Test if kafkacat is available
    if command -v kafkacat &> /dev/null || command -v kcat &> /dev/null; then
        KAFKA_CMD="kafkacat"
        if command -v kcat &> /dev/null; then
            KAFKA_CMD="kcat"
        fi

        print_status "Testing Kafka connectivity..."
        if timeout 10 $KAFKA_CMD -b $VM_IP:9092 -L &> /dev/null; then
            print_success "Kafka connectivity test passed"
        else
            print_warning "Kafka connectivity test failed (this might be normal if kafkacat/kcat is not installed)"
        fi
    else
        print_warning "kafkacat/kcat not found. Skipping connectivity test."
    fi

    print_success "Deployment completed!"
    echo ""
    echo "Next steps:"
    echo "1. Access Kafka UI at: http://$VM_IP:8080"
    echo "2. Update your applications to use bootstrap_servers: $VM_IP:9092"
    echo "3. Test with: python data_generator.py --config config.yaml --num_messages 10"
    echo "4. Run pipeline with: python pipeline.py --config config.yaml --environment local"
}

# Function to cleanup on error
cleanup() {
    print_error "Deployment failed. Cleaning up..."
    rm -f .vm_ip docker-compose-updated.yml
    # Restore backup files
    [ -f provision_kafka_vm.sh.bak ] && mv provision_kafka_vm.sh.bak provision_kafka_vm.sh
}

# Main execution
main() {
    echo "========================================="
    echo "    Kafka VM Deployment Automation"
    echo "========================================="
    echo ""

    # Set trap for cleanup on error
    trap cleanup ERR

    check_prerequisites
    get_user_input

    echo ""
    read -p "Proceed with deployment? (y/N): " CONFIRM
    if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
        print_status "Deployment cancelled"
        exit 0
    fi

    echo ""
    provision_vm
    setup_docker
    deploy_kafka
    update_config
    test_deployment

    # Cleanup backup files
    rm -f provision_kafka_vm.sh.bak .vm_ip

    print_success "All done! 🎉"
}

# Run main function
main "$@"
