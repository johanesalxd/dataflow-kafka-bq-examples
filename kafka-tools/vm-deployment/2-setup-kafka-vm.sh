#!/bin/bash

# This script installs Docker and Docker Compose on the Kafka VM
# and sets up the Kafka services using docker-compose.

set -e

echo "=== Setting up Kafka VM ==="

# Update the system
echo "Updating system packages..."
sudo apt-get update -y

# Install Docker
echo "Installing Docker..."
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up the stable repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update package index and install Docker
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Add current user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
echo "Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Start and enable Docker service
echo "Starting Docker service..."
sudo systemctl start docker
sudo systemctl enable docker

echo "=== Setup Complete ==="
echo "Docker and Docker Compose have been installed."
echo ""
echo "Next steps:"
echo "1. Log out and log back in (or run 'newgrp docker') to apply group changes"
echo "2. Copy your docker-compose.yml to this VM"
echo "3. Update the KAFKA_ADVERTISED_LISTENERS in docker-compose.yml"
echo "4. Run 'docker-compose up -d' to start Kafka"
echo ""
echo "Versions installed:"
docker --version
docker-compose --version