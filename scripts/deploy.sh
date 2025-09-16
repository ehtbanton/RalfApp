#!/bin/bash

# Production Deployment Script for Video Storage Platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[DEPLOY]${NC} $1"
}

print_header "Starting production deployment..."

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found. Please run setup.sh first."
    exit 1
fi

# Load environment variables
source .env

# Validate production requirements
if [ "$ENV" != "production" ]; then
    print_warning "ENV is not set to 'production' in .env file"
    read -p "Continue anyway? (y/N): " confirm
    if [[ ! $confirm == [yY] ]]; then
        exit 1
    fi
fi

# Create backup
print_status "Creating backup of current deployment..."
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup database
if docker-compose ps postgres | grep -q "Up"; then
    print_status "Backing up database..."
    docker-compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_DIR/database.sql"
fi

# Backup uploaded videos
if [ -d "backend/storage" ]; then
    print_status "Backing up uploaded videos..."
    cp -r backend/storage "$BACKUP_DIR/"
fi

print_status "Backup created in $BACKUP_DIR"

# Pull latest changes (if using Git)
if [ -d ".git" ]; then
    print_status "Pulling latest changes..."
    git pull origin main || print_warning "Git pull failed or not in a Git repository"
fi

# Update Docker images
print_status "Pulling latest base images..."
docker-compose pull

# Rebuild images
print_status "Rebuilding application images..."
docker-compose build --no-cache

# Stop services gracefully
print_status "Stopping services..."
docker-compose down --timeout 30

# Start services
print_status "Starting services..."
docker-compose up -d

# Wait for services to be healthy
print_status "Waiting for services to be ready..."
sleep 45

# Health check
print_status "Performing health checks..."

# Check backend health
if curl -f -s "https://api.${DOMAIN}/health" > /dev/null; then
    print_status "✓ Backend health check passed"
else
    print_error "✗ Backend health check failed"
fi

# Check frontend
if curl -f -s "https://${DOMAIN}" > /dev/null; then
    print_status "✓ Frontend health check passed"
else
    print_error "✗ Frontend health check failed"
fi

# Check database connection
if docker-compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;" > /dev/null 2>&1; then
    print_status "✓ Database connection check passed"
else
    print_error "✗ Database connection check failed"
fi

# Check Redis connection
if docker-compose exec -T redis redis-cli -a "$REDIS_PASSWORD" ping > /dev/null 2>&1; then
    print_status "✓ Redis connection check passed"
else
    print_error "✗ Redis connection check failed"
fi

# Show service status
print_status "Service status:"
docker-compose ps

# Show resource usage
print_status "Resource usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Cleanup old images
print_status "Cleaning up old images..."
docker image prune -f

print_header "Deployment completed!"
echo
print_status "Access URLs:"
echo "  Frontend: https://${DOMAIN}"
echo "  API: https://api.${DOMAIN}"
echo "  Traefik Dashboard: https://traefik.${DOMAIN}"
echo
print_status "Backup location: $BACKUP_DIR"
echo
print_status "To view logs, run: docker-compose logs -f"
print_status "To monitor services, run: docker-compose ps"