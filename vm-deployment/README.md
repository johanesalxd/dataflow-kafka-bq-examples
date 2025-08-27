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
   ./provision_kafka_vm.sh
   ```

   This script will:
   - Create a VM with e2-standard-2 machine type and 80GB boot disk
   - Create firewall rules for Kafka (9092), Kafka UI (8080), and SSH (22)
   - Output the VM's external IP address

3. **Note the external IP address** from the script output - you'll need it for the next steps.

### Step 2: Setup Docker on the VM

1. **Copy the setup script to the VM**
   ```bash
   # Replace VM_EXTERNAL_IP with the IP from Step 1
   gcloud compute scp setup_kafka_vm.sh kafka-vm:~/ --zone=us-central1-a
   ```

2. **SSH into the VM and run the setup**
   ```bash
   gcloud compute ssh kafka-vm --zone=us-central1-a

   # On the VM:
   chmod +x setup_kafka_vm.sh
   ./setup_kafka_vm.sh
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
   gcloud compute scp docker-compose-vm.yml kafka-vm:~/docker-compose.yml --zone=us-central1-a
   ```

3. **Start Kafka on the VM**
   ```bash
   # SSH into the VM:
   gcloud compute ssh kafka-vm --zone=us-central1-a

   # On the VM:
   docker-compose up -d
   ```

4. **Verify Kafka is running**
   ```bash
   # On the VM:
   docker-compose ps
   docker-compose logs kafka
   ```

### Step 4: Configure Your Local Environment

1. **Update your config.yaml**
   ```yaml
   # In your main project directory, update config.yaml:
   kafka:
     bootstrap_servers: "YOUR_VM_EXTERNAL_IP:9092"  # Replace with actual IP
     consumer_group: "dataflow-consumer"
     topics:
       - name: "user-events"
         raw_table: "user_events_raw"
   ```

2. **Test connectivity from your local machine**
   ```bash
   # Install kafkacat/kcat if not already installed
   # Ubuntu/Debian:
   sudo apt-get install kafkacat

   # macOS:
   brew install kcat

   # Test connection:
   kafkacat -b YOUR_VM_EXTERNAL_IP:9092 -L
   ```

### Step 5: Access Kafka UI

1. **Open Kafka UI in your browser**
   ```
   http://YOUR_VM_EXTERNAL_IP:8080
   ```

2. **Create the user-events topic** (if not already created)
   - Navigate to Topics in the UI
   - Click "Add a Topic"
   - Name: `user-events`
   - Partitions: 3
   - Replication Factor: 1

## Testing the Setup

### Test 1: Send Test Messages

```bash
# From your local machine, send a test message:
echo '{"event_id": "test-001", "user_id": "user-123", "event_type": "page_view", "timestamp": "2024-01-01T12:00:00Z"}' | \
kafkacat -b YOUR_VM_EXTERNAL_IP:9092 -t user-events -P
```

### Test 2: Consume Messages

```bash
# From your local machine, consume messages:
kafkacat -b YOUR_VM_EXTERNAL_IP:9092 -t user-events -C
```

### Test 3: Run Data Generator

```bash
# From your main project directory:
python data_generator.py --config config.yaml --num_messages 10
```

## Running the Dataflow Pipeline

Once Kafka is running and configured:

1. **For local testing (DirectRunner)**
   ```bash
   python pipeline.py --config config.yaml --environment local
   ```

2. **For cloud deployment (DataflowRunner)**
   ```bash
   python pipeline.py --config config.yaml --environment cloud --job_name kafka-to-bq-$(date +%Y%m%d-%H%M%S)
   ```

## Monitoring and Maintenance

### View Kafka Logs
```bash
# SSH into the VM:
gcloud compute ssh kafka-vm --zone=us-central1-a

# View logs:
docker-compose logs -f kafka
docker-compose logs -f zookeeper
```

### Restart Kafka Services
```bash
# On the VM:
docker-compose restart kafka
# or restart all services:
docker-compose restart
```

### Stop Kafka Services
```bash
# On the VM:
docker-compose down
```

### VM Management
```bash
# Stop the VM (to save costs):
gcloud compute instances stop kafka-vm --zone=us-central1-a

# Start the VM:
gcloud compute instances start kafka-vm --zone=us-central1-a

# Delete the VM (when no longer needed):
gcloud compute instances delete kafka-vm --zone=us-central1-a
```

## Troubleshooting

### Common Issues

1. **Cannot connect to Kafka from local machine**
   - Verify firewall rules are created: `gcloud compute firewall-rules list`
   - Check VM external IP: `gcloud compute instances list`
   - Ensure KAFKA_ADVERTISED_LISTENERS uses the correct external IP

2. **Kafka container fails to start**
   - Check logs: `docker-compose logs kafka`
   - Verify Zookeeper is running: `docker-compose logs zookeeper`
   - Check disk space: `df -h`

3. **Permission denied errors**
   - Ensure user is in docker group: `groups $USER`
   - Re-login after running setup script: `exit` and SSH back in

4. **Dataflow pipeline fails to connect**
   - Verify config.yaml has correct bootstrap_servers
   - Test connectivity with kafkacat
   - Check GCP networking and firewall rules

### Useful Commands

```bash
# Check VM status
gcloud compute instances list

# SSH into VM
gcloud compute ssh kafka-vm --zone=us-central1-a

# Copy files to/from VM
gcloud compute scp LOCAL_FILE kafka-vm:REMOTE_PATH --zone=us-central1-a
gcloud compute scp kafka-vm:REMOTE_FILE LOCAL_PATH --zone=us-central1-a

# View firewall rules
gcloud compute firewall-rules list

# Check Kafka topics
kafkacat -b VM_IP:9092 -L
```

## Cost Optimization

- **Stop the VM when not in use** to avoid compute charges
- **Use preemptible instances** for development (add `--preemptible` to the gcloud command)
- **Monitor usage** through GCP Console billing section

## Security Considerations

- The current setup uses no authentication for simplicity
- For production use, consider:
  - Enabling Kafka SASL/SSL authentication
  - Using private IPs with VPN access
  - Implementing proper network security groups
  - Regular security updates for the VM

## File Structure

```
vm-deployment/
├── README.md                 # This guide
├── provision_kafka_vm.sh     # VM provisioning script
├── setup_kafka_vm.sh         # Docker installation script
└── docker-compose-vm.yml     # Kafka Docker Compose configuration
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Kafka and Docker logs
3. Verify GCP permissions and quotas
4. Consult the Apache Kafka and Google Cloud documentation
