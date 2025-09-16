#!/bin/bash

# Video Storage Platform Setup Script
# This script sets up the entire video storage platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

print_status "Setting up Video Storage Platform..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    print_status "Creating .env file from template..."
    cp .env.example .env

    # Generate random JWT secret
    JWT_SECRET=$(openssl rand -base64 32)
    sed -i "s/your-super-secret-jwt-key-change-this-in-production/$JWT_SECRET/" .env

    # Generate random database password
    DB_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
    sed -i "s/your-secure-password/$DB_PASSWORD/" .env

    # Generate random Redis password
    REDIS_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
    sed -i "s/your-redis-password/$REDIS_PASSWORD/" .env

    print_warning "Please edit the .env file and configure your domain and email settings"
    print_warning "Required variables: DOMAIN, ACME_EMAIL"

    read -p "Press enter to continue after editing .env file..."
fi

# Validate required environment variables
source .env

if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "your-domain.com" ]; then
    print_error "Please set DOMAIN in .env file"
    exit 1
fi

if [ -z "$ACME_EMAIL" ] || [ "$ACME_EMAIL" = "your-email@example.com" ]; then
    print_error "Please set ACME_EMAIL in .env file"
    exit 1
fi

# Create Docker network
print_status "Creating Docker network 'web'..."
docker network create web 2>/dev/null || true

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p traefik
mkdir -p backend/storage
mkdir -p letsencrypt

# Set permissions for Let's Encrypt
chmod 600 letsencrypt 2>/dev/null || true

print_status "Building Docker images..."
docker-compose build

print_status "Starting services..."
docker-compose up -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 30

# Check if services are running
print_status "Checking service status..."
docker-compose ps

# Display access information
print_status "Setup complete!"
echo
print_status "Access URLs:"
echo "  Frontend: https://${DOMAIN}"
echo "  API: https://api.${DOMAIN}"
echo "  Traefik Dashboard: https://traefik.${DOMAIN} (admin/admin)"
echo
print_status "Default credentials for Traefik dashboard:"
echo "  Username: admin"
echo "  Password: admin"
echo
print_warning "Please change the default Traefik dashboard password!"
print_status "To generate a new password hash, run:"
echo "  htpasswd -nb admin your_new_password"

# Show logs
print_status "Showing recent logs (press Ctrl+C to exit):"
docker-compose logs --tail=50 -f