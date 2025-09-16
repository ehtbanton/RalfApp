# Video Storage Platform

A scalable full-stack video storage and analysis platform built with FastAPI, React, PostgreSQL, Redis, and Traefik.

## Features

### Core Platform
- 🚀 **FastAPI Backend** with async support and JWT authentication
- ⚛️ **React Frontend** with modern UI/UX using Tailwind CSS
- 🐘 **PostgreSQL Database** optimized for video metadata storage
- 🔴 **Redis Cache** for sessions, caching, and pub/sub messaging
- 🌐 **Traefik Reverse Proxy** with automatic SSL certificate management
- 📦 **Docker Compose** orchestration for easy deployment

### Video Management
- 📤 **Multiple Upload Methods**: Simple HTTP upload and WebSocket chunked upload
- 🎬 **Video Storage** with organized file system structure
- 📊 **Metadata Extraction** using FFmpeg for video properties
- 🔍 **Search and Filter** capabilities for video collections

### AI-Powered Analysis
- 🧠 **PyTorch Integration** for deep learning video analysis
- 👁️ **Computer Vision** with OpenCV for video processing
- 🎯 **Scene Detection** using feature similarity analysis
- 🏃 **Motion Analysis** with optical flow detection
- 📈 **Quality Assessment** for sharpness and brightness metrics
- ⚡ **Celery Workers** for background processing

### Real-time Features
- 🌐 **WebSocket Support** for real-time upload progress
- 📢 **Live Notifications** for analysis completion
- 📊 **Progress Tracking** during video processing
- 🔄 **Auto-resume** capability for interrupted uploads

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git
- Make (optional, for convenience)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ralf-app
   ```

2. **Run the setup script**
   ```bash
   # Make setup script executable
   chmod +x scripts/setup.sh

   # Run setup (creates .env, networks, builds images)
   ./scripts/setup.sh
   ```

   Or use Make:
   ```bash
   make setup
   ```

3. **Configure environment**
   Edit the `.env` file with your domain and email:
   ```bash
   DOMAIN=your-domain.com
   ACME_EMAIL=your-email@example.com
   ```

4. **Start the platform**
   ```bash
   docker-compose up -d
   ```

   Or with Make:
   ```bash
   make up
   ```

### Development Setup

For local development without SSL:

```bash
# Install dependencies
make install-backend
make install-frontend

# Start development servers
make dev-backend    # Backend on :8000
make dev-frontend   # Frontend on :3000
make dev-worker     # Analysis worker
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Traefik     │────│   React App     │────│   FastAPI       │
│  (Reverse Proxy)│    │   (Frontend)    │    │   (Backend)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │              ┌─────────────────┐
         │                       │              │   PostgreSQL    │
         │                       │              │   (Database)    │
         │                       │              └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐    ┌─────────────────┐
         │              │     Redis       │────│  Celery Worker  │
         │              │ (Cache/Queue)   │    │   (Analysis)    │
         └──────────────┴─────────────────┘    └─────────────────┘
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user

### Videos
- `GET /api/videos` - List user videos
- `GET /api/videos/{id}` - Get video details
- `DELETE /api/videos/{id}` - Delete video

### Upload
- `POST /api/upload/simple` - Simple file upload
- `POST /api/upload/session` - Create chunked upload session
- `WS /ws/upload/{token}` - WebSocket upload endpoint

### Analysis
- `POST /api/analysis/{video_id}` - Start video analysis
- `GET /api/analysis/{analysis_id}` - Get analysis results

## Analysis Types

### 1. Metadata Extraction
Extracts basic video information:
- Duration, resolution, frame rate
- Codec, bitrate, file format
- Automatically runs on upload

### 2. Scene Detection
Detects scene changes using feature similarity:
- Uses ResNet50 features
- Configurable similarity threshold
- Returns timestamps of scene changes

### 3. Motion Analysis
Analyzes motion patterns:
- Optical flow calculation
- Motion magnitude statistics
- Movement variance over time

### 4. Quality Assessment
Assesses video quality metrics:
- Sharpness using Laplacian variance
- Brightness analysis
- Statistical quality measures

## WebSocket Upload

For large files, use WebSocket upload with chunking:

```javascript
const wsUpload = new WebSocketUpload(sessionToken);
wsUpload.onProgress = (progress) => console.log(progress);
wsUpload.onComplete = (result) => console.log('Upload complete');
await wsUpload.connect();

// Upload file in chunks
for (let chunk of chunks) {
    wsUpload.uploadChunk(chunkIndex, base64Data);
}
```

## Deployment

### Production Deployment

1. **Set production environment**
   ```bash
   # Set ENV=production in .env
   ENV=production
   ```

2. **Deploy with script**
   ```bash
   ./scripts/deploy.sh
   ```

   Or with Make:
   ```bash
   make deploy
   ```

### SSL Configuration

Traefik automatically handles SSL certificates using Let's Encrypt:
- Certificates are automatically issued and renewed
- HTTP traffic is redirected to HTTPS
- HSTS headers are configured

### Scaling

Scale services based on load:

```bash
# Scale backend instances
docker-compose up -d --scale backend=3

# Scale workers for analysis
docker-compose up -d --scale worker=5

# Or use maintenance script
./scripts/maintenance.sh scale worker=5
```

## Maintenance

### Backup

```bash
# Full backup (database + videos + config)
./scripts/maintenance.sh backup

# Database only
make db-backup
```

### Monitoring

```bash
# Real-time container stats
./scripts/maintenance.sh monitor

# Health checks
./scripts/maintenance.sh health

# Service logs
make logs
make logs-backend
make logs-worker
```

### Cleanup

```bash
# Clean up Docker resources
./scripts/maintenance.sh cleanup

# Complete cleanup
make clean
```

## Configuration

### Environment Variables

Key variables in `.env`:

```bash
# Domain Configuration
DOMAIN=your-domain.com
ACME_EMAIL=your-email@example.com

# Database
POSTGRES_DB=video_storage
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure-password

# Security
JWT_SECRET=your-jwt-secret
REDIS_PASSWORD=redis-password

# Application
ENV=production
VIDEO_STORAGE_PATH=/app/storage
```

### Traefik Configuration

- Main config: `traefik/traefik.yml`
- Dynamic config: `traefik/dynamic.yml`
- SSL settings, security headers, CORS configuration

## Development

### Backend Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload

# Run tests
pytest

# Code formatting
black .
flake8 .
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm start

# Run tests
npm test

# Build for production
npm run build
```

### Adding New Analysis Types

1. **Implement analysis function** in `backend/app/tasks.py`
2. **Add analysis type** to frontend options
3. **Update database schema** if needed
4. **Add API endpoint** if custom logic required

## Monitoring and Logging

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Analysis worker logs
docker-compose logs -f worker
```

### Metrics

- Container stats via `docker stats`
- Database performance via PostgreSQL queries
- Redis memory usage
- Custom application metrics

## Security

### Features
- JWT-based authentication
- HTTPS with automatic SSL certificates
- CORS protection
- Rate limiting via Redis
- Input validation and sanitization
- Secure headers via Traefik

### Recommendations
- Change default Traefik dashboard password
- Use strong database passwords
- Regularly update Docker images
- Monitor logs for suspicious activity
- Backup regularly

## Troubleshooting

### Common Issues

1. **SSL Certificate Issues**
   ```bash
   # Check Traefik logs
   docker-compose logs traefik

   # Force certificate renewal
   ./scripts/maintenance.sh ssl-renew
   ```

2. **Database Connection Issues**
   ```bash
   # Check database status
   docker-compose ps postgres

   # Check logs
   docker-compose logs postgres
   ```

3. **Upload Issues**
   ```bash
   # Check storage permissions
   ls -la backend/storage/

   # Check backend logs
   docker-compose logs backend
   ```

4. **Analysis Not Working**
   ```bash
   # Check worker status
   docker-compose ps worker

   # Check worker logs
   docker-compose logs worker

   # Check Redis connection
   docker-compose exec redis redis-cli ping
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run linting and tests
6. Submit a pull request

## License

[License information]

## Support

For issues and questions:
- Check the troubleshooting section
- Review logs using provided commands
- Submit issues with logs and configuration details