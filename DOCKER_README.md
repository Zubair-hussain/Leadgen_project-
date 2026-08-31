# LeadGen - Docker Setup Guide

This guide explains how to run the LeadGen application using Docker for efficient development and production deployments.

## 🚀 Quick Start

### Prerequisites
- Docker Desktop (latest version)
- Docker Compose V2
- At least 4GB RAM available
- Git

### Development Setup

1. **Clone and navigate to the project:**
   ```bash
   git clone <repository-url>
   cd lead-gen-project
   ```

2. **Start all services:**
   ```bash
   docker-compose up -d
   ```

3. **Run database migrations:**
   ```bash
   docker-compose exec backend python manage.py migrate
   ```

4. **Access the application:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - PostgreSQL: localhost:5433
   - Redis: localhost:6379

## 🏗️ Architecture

The application consists of the following services:

- **backend**: Django REST API with Celery workers
- **db**: PostgreSQL 16 database
- **redis**: Redis cache and message broker
- **celery_worker**: Background task processing
- **celery_beat**: Scheduled task management
- **nginx**: Reverse proxy (production only)

## 📋 Available Commands

### Basic Operations
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f backend

# Restart services
docker-compose restart
```

### Database Operations
```bash
# Run migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Access database shell
docker-compose exec db psql -U leadgen_user -d leadgen

# Backup database
docker-compose exec db pg_dump -U leadgen_user leadgen > backup.sql

# Restore database
docker-compose exec db psql -U leadgen_user leadgen < backup.sql
```

### Development Workflow
```bash
# Rebuild after code changes
docker-compose build backend

# Run tests
docker-compose exec backend python manage.py test

# Collect static files
docker-compose exec backend python manage.py collectstatic --noinput

# Check Django configuration
docker-compose exec backend python manage.py check --deploy
```

## 🔧 Configuration

### Environment Variables

The application uses environment variables for configuration. Key variables include:

- `DEBUG`: Enable/disable debug mode
- `SECRET_KEY`: Django secret key
- `POSTGRES_*`: Database configuration
- `REDIS_URL`: Redis connection URL
- `SERPAPI_KEY`: Search API key
- `GOOGLE_API_KEY`: Google API key
- `APIFY_API_KEY`: Apify API key

### Production Deployment

For production deployment:

1. **Update environment variables:**
   ```bash
   cp backend/.env backend/.env.prod
   # Edit .env.prod with production values
   ```

2. **Use production compose file:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

3. **Enable SSL/TLS:**
   - Place SSL certificates in `nginx/ssl/`
   - Update nginx configuration

## 🔍 Troubleshooting

### Common Issues

1. **Port conflicts:**
   - Change ports in `docker-compose.override.yml`
   - Or stop conflicting services

2. **Database connection issues:**
   ```bash
   # Check if database is ready
   docker-compose exec db pg_isready -U leadgen_user

   # Reset database
   docker-compose down -v
   docker-compose up -d db
   ```

3. **Permission issues:**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   ```

4. **Memory issues:**
   - Increase Docker Desktop memory allocation
   - Reduce Celery concurrency in environment variables

### Logs and Debugging

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs backend

# Follow logs in real-time
docker-compose logs -f backend

# Check container resource usage
docker stats
```

### Health Checks

```bash
# Check service health
docker-compose ps

# Manual health checks
curl http://localhost:8000/health/
docker-compose exec redis redis-cli ping
```

## 📊 Monitoring

### Production Monitoring (Optional)

Enable monitoring services:

```bash
# Start with monitoring
docker-compose --profile monitoring up -d

# Access monitoring
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (admin/admin)
```

## 🔄 Updates and Maintenance

### Updating the Application

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose build
docker-compose up -d

# Run migrations if needed
docker-compose exec backend python manage.py migrate
```

### Backup Strategy

```bash
# Database backup
docker-compose exec db pg_dump -U leadgen_user leadgen > backup_$(date +%Y%m%d_%H%M%S).sql

# Full backup (including volumes)
docker run --rm -v leadgen_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/backup_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
```

## 🧹 Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Full cleanup
docker system prune -a --volumes
```

## 📈 Performance Optimization

### Production Optimizations

1. **Resource Limits:**
   - Configure memory and CPU limits in `docker-compose.prod.yml`

2. **Database Optimization:**
   - Use connection pooling
   - Configure PostgreSQL settings for your hardware

3. **Caching:**
   - Redis is configured for both cache and session storage
   - Configure cache timeouts appropriately

4. **Static Files:**
   - Use CDN for static files in production
   - Configure nginx for static file serving

## 🤝 Contributing

When making changes to the Docker setup:

1. Test changes in development environment
2. Update this documentation
3. Ensure production configurations work
4. Test backup/restore procedures

## 📞 Support

For issues with the Docker setup:

1. Check the troubleshooting section
2. Review logs: `docker-compose logs`
3. Check container status: `docker-compose ps`
4. Verify environment variables
5. Ensure sufficient system resources

---

**Note:** This setup is optimized for both development productivity and production reliability. The configuration includes security best practices, health checks, and resource management.