#!/bin/bash

# Maintenance Script for Video Storage Platform

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

show_help() {
    echo "Video Storage Platform Maintenance Script"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  backup          Create full backup of database and videos"
    echo "  restore FILE    Restore from backup file"
    echo "  logs SERVICE    Show logs for specific service (all if not specified)"
    echo "  stats           Show system and container statistics"
    echo "  cleanup         Clean up old Docker images and containers"
    echo "  update          Update all services"
    echo "  restart SERVICE Restart specific service (all if not specified)"
    echo "  scale SERVICE=N Scale service to N instances"
    echo "  monitor         Show real-time container stats"
    echo "  ssl-renew       Force SSL certificate renewal"
    echo "  health          Run health checks on all services"
    echo "  help            Show this help message"
}

backup_system() {
    print_status "Creating system backup..."

    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    # Backup database
    print_status "Backing up database..."
    docker-compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_DIR/database.sql"

    # Backup videos
    print_status "Backing up videos..."
    if [ -d "backend/storage" ]; then
        tar -czf "$BACKUP_DIR/videos.tar.gz" backend/storage/
    fi

    # Backup configuration
    print_status "Backing up configuration..."
    cp .env "$BACKUP_DIR/"
    cp docker-compose.yml "$BACKUP_DIR/"

    # Create backup info
    cat > "$BACKUP_DIR/backup_info.txt" << EOF
Backup created: $(date)
Git commit: $(git rev-parse HEAD 2>/dev/null || echo "N/A")
Services:
$(docker-compose ps)
EOF

    print_status "Backup completed: $BACKUP_DIR"
}

show_logs() {
    SERVICE=${1:-}
    if [ -z "$SERVICE" ]; then
        docker-compose logs --tail=100 -f
    else
        docker-compose logs --tail=100 -f "$SERVICE"
    fi
}

show_stats() {
    print_status "System Statistics:"
    echo
    echo "=== Container Stats ==="
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"

    echo
    echo "=== Disk Usage ==="
    df -h

    echo
    echo "=== Service Status ==="
    docker-compose ps

    echo
    echo "=== Database Stats ==="
    source .env
    docker-compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
        SELECT
            schemaname,
            tablename,
            attname as column_name,
            n_distinct,
            most_common_vals
        FROM pg_stats
        WHERE schemaname = 'public'
        ORDER BY schemaname, tablename;
    " 2>/dev/null || echo "Could not retrieve database stats"

    echo
    echo "=== Redis Stats ==="
    docker-compose exec -T redis redis-cli -a "$REDIS_PASSWORD" info memory 2>/dev/null || echo "Could not retrieve Redis stats"
}

cleanup_system() {
    print_status "Cleaning up system..."

    print_status "Removing old Docker images..."
    docker image prune -f

    print_status "Removing unused volumes..."
    docker volume prune -f

    print_status "Removing unused networks..."
    docker network prune -f

    print_status "Cleaning up old backups (keeping last 10)..."
    if [ -d "backups" ]; then
        cd backups
        ls -t | tail -n +11 | xargs -r rm -rf
        cd ..
    fi

    print_status "Cleanup completed"
}

restart_service() {
    SERVICE=${1:-}
    if [ -z "$SERVICE" ]; then
        print_status "Restarting all services..."
        docker-compose restart
    else
        print_status "Restarting $SERVICE..."
        docker-compose restart "$SERVICE"
    fi
}

scale_service() {
    if [ -z "$1" ]; then
        print_error "Usage: $0 scale SERVICE=NUMBER"
        exit 1
    fi

    print_status "Scaling service: $1"
    docker-compose up -d --scale "$1"
}

monitor_system() {
    print_status "Starting real-time monitoring (press Ctrl+C to exit)..."
    docker stats
}

renew_ssl() {
    print_status "Forcing SSL certificate renewal..."
    docker-compose exec traefik rm -f /letsencrypt/acme.json
    docker-compose restart traefik
    print_status "SSL renewal initiated. Check Traefik logs for status."
}

health_check() {
    print_status "Running health checks..."
    source .env

    # Check backend
    if curl -f -s "https://api.${DOMAIN}/health" > /dev/null; then
        print_status "✓ Backend is healthy"
    else
        print_error "✗ Backend health check failed"
    fi

    # Check frontend
    if curl -f -s "https://${DOMAIN}" > /dev/null; then
        print_status "✓ Frontend is healthy"
    else
        print_error "✗ Frontend health check failed"
    fi

    # Check database
    if docker-compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;" > /dev/null 2>&1; then
        print_status "✓ Database is healthy"
    else
        print_error "✗ Database health check failed"
    fi

    # Check Redis
    if docker-compose exec -T redis redis-cli -a "$REDIS_PASSWORD" ping > /dev/null 2>&1; then
        print_status "✓ Redis is healthy"
    else
        print_error "✗ Redis health check failed"
    fi

    # Check worker
    WORKER_STATUS=$(docker-compose ps worker | grep -c "Up" || true)
    if [ "$WORKER_STATUS" -gt 0 ]; then
        print_status "✓ Worker is running"
    else
        print_error "✗ Worker is not running"
    fi
}

# Main script logic
case "${1:-help}" in
    "backup")
        backup_system
        ;;
    "logs")
        show_logs "$2"
        ;;
    "stats")
        show_stats
        ;;
    "cleanup")
        cleanup_system
        ;;
    "restart")
        restart_service "$2"
        ;;
    "scale")
        scale_service "$2"
        ;;
    "monitor")
        monitor_system
        ;;
    "ssl-renew")
        renew_ssl
        ;;
    "health")
        health_check
        ;;
    "help"|*)
        show_help
        ;;
esac