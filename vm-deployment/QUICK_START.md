# Quick Start Guide

## One-Command Deployment

For a fully automated deployment, simply run:

```bash
cd vm-deployment
./deploy.sh
```

This script will:
1. Check prerequisites (gcloud CLI, authentication)
2. Prompt for your GCP project ID, zone, and VM name
3. Provision the VM with firewall rules
4. Install Docker on the VM
5. Deploy Kafka with Docker Compose
6. Update your local config.yaml
7. Test the deployment

## Manual Step-by-Step

If you prefer manual control, follow the detailed instructions in [README.md](README.md).

## Files Overview

- **`deploy.sh`** - Automated deployment script
- **`README.md`** - Comprehensive step-by-step guide
- **`provision_kafka_vm.sh`** - VM provisioning script
- **`setup_kafka_vm.sh`** - Docker installation script
- **`docker-compose-vm.yml`** - Kafka Docker Compose configuration

## Prerequisites

- Google Cloud SDK installed and configured
- Active GCP project with billing enabled
- Compute Engine and Security Admin permissions

## After Deployment

1. Access Kafka UI at `http://YOUR_VM_IP:8080`
2. Test with data generator: `python data_generator.py --config config.yaml --num_messages 10`
3. Run pipeline: `python pipeline.py --config config.yaml --environment local`

## Cost Management

Remember to stop the VM when not in use:
```bash
gcloud compute instances stop kafka-vm --zone=us-central1-a
