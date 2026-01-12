# Trip Me Buddy - Backend API

FastAPI backend service with Keycloak authentication, PostgreSQL database, and Redis caching.

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── __init__.py       # API router aggregation
│   │       └── users.py          # User endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py             # Application settings
│   │   ├── database.py           # SQLAlchemy setup
│   │   ├── cache.py              # Redis connection
│   │   └── security.py           # JWT validation
│   ├── models/                   # SQLAlchemy models
│   ├── schemas/                  # Pydantic schemas
│   ├── services/                 # Business logic
│   ├── __init__.py
│   └── main.py                   # FastAPI application
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Setup Instructions

### 1. Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Update the following values:
- `DB_HOST`: RDS endpoint from Terraform outputs
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password
- `REDIS_HOST`: ElastiCache endpoint from Terraform outputs
- `KEYCLOAK_SERVER_URL`: ALB DNS name from Terraform outputs
- `KEYCLOAK_CLIENT_SECRET`: Backend client secret from Keycloak

### 2. Local Development

Install dependencies:
```bash
pip install -r requirements.txt
```

Run application:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 3. Docker Build

Build image:
```bash
docker build -t trip-me-buddy-backend .
```

Run container locally:
```bash
docker run -p 8000:8000 --env-file .env trip-me-buddy-backend
```

### 4. Deploy to AWS ECR + ECS

See deployment instructions in project documentation.

## API Endpoints

### Public Endpoints
- `GET /health` - Health check

### Protected Endpoints (Requires JWT)
- `GET /api/v1/users/me` - Get current user info
- `GET /api/v1/users/profile` - Get user profile

## Authentication

All protected endpoints require a valid JWT token from Keycloak:

```
Authorization: Bearer <jwt_token>
```

## Testing Authentication

1. Get token from Keycloak
2. Use token in API requests
3. Test with Thunder Client or Postman
