# Lead Generation API (Django + Docker)

A professional lead generation and email verification API built with Django REST Framework, featuring AI-powered filtering and multi-source scraping.

## Features

- **Multi-Source Lead Generation**: Search across Google Maps, Custom Search, SerpAPI, and Apify
- **AI-Powered Filtering**: Uses Gemini AI to filter out agencies and keep potential clients
- **Email Verification**: Comprehensive email validation with DNS and syntax checks
- **Phone Number Normalization**: Automatic phone number formatting
- **Rate Limiting**: Built-in protection against abuse
- **Asynchronous Processing**: Celery integration for background tasks
- **Production Ready**: Docker containerization with security best practices

## Tech Stack

- **Backend**: Django 5.1, Django REST Framework
- **Database**: PostgreSQL
- **Cache/Queue**: Redis, Celery
- **APIs**: SerpAPI, Google Custom Search, Apify, Gemini AI
- **Deployment**: Docker, Docker Compose

## Project Structure

```
backend/
├── Dockerfile              # Production-ready container
├── requirements.txt        # Python dependencies
├── manage.py              # Django CLI
├── leadgen/               # Django project settings
│   ├── settings.py        # Main configuration
│   ├── urls.py           # URL routing
│   └── celery.py         # Celery configuration
├── leads/                 # Main app
│   ├── models.py         # Lead model with validation
│   ├── views.py          # API endpoints
│   ├── services.py       # Business logic (LeadGenerator, EmailVerifier)
│   ├── serializers.py    # DRF serializers
│   ├── urls.py           # App URLs
│   └── admin.py          # Django admin configuration
├── logs/                  # Application logs
└── .env                   # Environment variables (not in git)
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- API keys for external services (see Configuration)

### 1. Clone and Setup

```bash
cd lead-gen-project
cp backend/.env.example backend/.env  # Copy and fill in your API keys
```

### 2. Environment Configuration

Edit `backend/.env` with your actual API keys:

```env
# Required API Keys
SERPAPI_KEY=your_serpapi_key
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CX=your_google_custom_search_cx
APIFY_API_KEY=your_apify_api_key
GEMINI_API_KEY=your_gemini_api_key

# Database
POSTGRES_PASSWORD=your_secure_password
SECRET_KEY=your_django_secret_key
```

### 3. Launch Services

```bash
docker compose up --build
```

### 4. Run Migrations

```bash
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
```

### 5. Create Admin User (Optional)

```bash
docker compose exec backend python manage.py createsuperuser
```

## API Endpoints

### Health Check
```
GET /api/health/
```

### Lead Management
```
GET  /api/leads/              # List leads (paginated)
GET  /api/leads/export/       # Export verified leads as CSV
POST /api/leads/{id}/         # Delete lead
POST /api/leads/{id}/verify/  # Verify single lead
```

### Lead Generation
```
POST /api/generate/           # Generate new leads
```

**Request Body:**
```json
{
  "category": "Web Design",
  "platforms": ["x", "reddit", "google-cse"],
  "niche": "Real Estate",
  "target_location": "New York",
  "is_professional": false
}
```

### Email Verification
```
POST /api/leads/verify-single/     # Verify single email
POST /api/leads/verify-multi/      # Verify multiple emails
POST /api/leads/verify-file/       # Upload file with emails
POST /api/leads/bulk-verify/       # Verify all unverified leads
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DEBUG` | Enable debug mode | No |
| `SECRET_KEY` | Django secret key | Yes |
| `ALLOWED_HOSTS` | Comma-separated hosts | Yes |
| `POSTGRES_*` | Database configuration | Yes |
| `SERPAPI_KEY` | SerpAPI key for searches | Yes |
| `GOOGLE_API_KEY` | Google API key | No |
| `GOOGLE_CX` | Google Custom Search CX | No |
| `APIFY_API_KEY` | Apify API key | No |
| `GEMINI_API_KEY` | Google Gemini API key | No |

### Security Features

- **CORS**: Configured for frontend domains only
- **Rate Limiting**: 100 requests/hour per IP
- **Input Validation**: Comprehensive email and data validation
- **Non-root Container**: Runs as django user
- **Environment Variables**: No hardcoded secrets

## Development

### Running Tests

```bash
docker compose exec backend python manage.py test
```

### Code Quality

- Black for code formatting
- Flake8 for linting
- Pre-commit hooks recommended

### Logging

Logs are written to:
- Console (INFO level)
- `backend/logs/leadgen.log` (INFO level)
- Django debug toolbar in development

## Production Deployment

### Using Gunicorn

Update `docker-compose.yml` command:
```yaml
command: gunicorn leadgen.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### Environment Setup

- Set `DEBUG=False`
- Use strong `SECRET_KEY`
- Configure proper `ALLOWED_HOSTS`
- Set up SSL/TLS
- Use environment-specific `.env` files

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL container is healthy
   - Verify `POSTGRES_*` environment variables

2. **API Key Errors**
   - Ensure all required API keys are set in `.env`
   - Check key validity and quotas

3. **Permission Denied**
   - Container runs as non-root user
   - Check file permissions in volumes

4. **Port Conflicts**
   - Modify ports in `docker-compose.yml` if needed

### Logs

Check logs with:
```bash
docker compose logs backend
docker compose logs celery_worker
```

## Contributing

1. Follow Django best practices
2. Add tests for new features
3. Update documentation
4. Use meaningful commit messages

## License

This project is licensed under the MIT License.