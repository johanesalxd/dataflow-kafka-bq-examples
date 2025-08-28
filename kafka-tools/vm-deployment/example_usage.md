# Kafka VM Deployment Guide

This guide provides step-by-step instructions for deploying Kafka on a Google Compute Engine VM and configuring it for use with Apache Beam/Dataflow pipelines.

## Overview

This deployment creates:
- A Google Compute Engine VM (e2-standard-2 with 80GB disk)
- Kafka cluster running in Docker containers
- Kafka UI for monitoring and management
- Proper firewall rules for external access

## Prerequisites

Before starting, ensure you have:

1. **Google Cloud SDK installed and configured**
   ```bash
   # Install gcloud CLI if not already installed
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init
   ```

2. **Required permissions in your GCP project**
   - Compute Engine Admin
   - Security Admin (for firewall rules)
   - Service Account User

3. **Project configuration**
   - Update the `PROJECT_ID` in `provision_kafka_vm.sh` to match your GCP project
   - Ensure billing is enabled for your project

## Deployment Steps

### Step 1: Provision the VM

1. **Configure the provisioning script**
   ```bash
   # Edit provision_kafka_vm.sh and update these variables:
   PROJECT_ID="your-project-id"  # Replace with your actual project ID
   ZONE="us-central1-a"          # Adjust zone if needed
   ```

2. **Run the provisioning script**
   ```bash
   chmod +x provision_kafka_vm.sh
   ./kafka-tools/vm-deployment/1-provision-kafka-vm.sh
   ```

   This script will:
   - Create a VM with e2-standard-2 machine type and 80GB boot disk
   - Create firewall rules for Kafka (9092), Kafka UI (8080), and SSH (22)
   - Output the VM's external IP address

3. **Note the external IP address** from the script output - you'll need it for the next steps.

### Step 2: Setup Docker on the VM

1. **Copy the setup script to the VM**
   ```bash
   gcloud compute scp ./kafka-tools/vm-deployment/2-setup-kafka-vm.sh kafka-broker-vm:~/ --zone=us-central1-a
   ```

2. **SSH into the VM and run the setup**
   ```bash
   gcloud compute ssh kafka-broker-vm --zone=us-central1-a

   # On the VM:
   chmod +x 2-setup-kafka-vm.sh
   ./2-setup-kafka-vm.sh
   ```

   This will install Docker and Docker Compose on the VM.

3. **Verify Docker installation**
   ```bash
   # On the VM:
   docker --version
   docker-compose --version
   ```

### Step 3: Deploy Kafka

1. **Update the Docker Compose configuration**
   ```bash
   # Edit docker-compose-vm.yml and replace the IP addresses
   # with your VM's external IP in the KAFKA_ADVERTISED_LISTENERS section
   ```

2. **Copy Docker Compose file to the VM**
   ```bash
   # From your local machine:
   gcloud compute scp ./kafka-tools/vm-deployment/docker-compose-vm.yml kafka-broker-vm:~/docker-compose.yml --zone=us-central1-a
   ```

3. **Start Kafka on the VM**
   ```bash
   # SSH into the VM:
   gcloud compute ssh kafka-broker-vm --zone=us-central1-a

   # On the VM:
   docker-compose up -d
   ```

4. **Verify Kafka is running**
   ```bash
   # On the VM:
   docker-compose ps
   docker-compose logs kafka
   ```
