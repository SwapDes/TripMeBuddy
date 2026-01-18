from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import users, travel

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS Configuration
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for ALB and monitoring"""
    return {
        "status": "healthy",
        "service": "trip-me-buddy-backend",
        "version": settings.VERSION
    }

# API Routes
app.include_router(users.router, prefix="/api/v1", tags=["users"])
app.include_router(travel.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Trip Me Buddy API",
        "version": settings.VERSION,
        "docs": "/docs" if settings.DEBUG else "Documentation disabled in production"
    }
