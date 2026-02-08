import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import users, travel, trips, jobs

# Configure logging BEFORE creating the app
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set specific module log levels
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("app").setLevel(logging.INFO)
logging.getLogger("asyncio").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS Configuration - Combined origins
cors_origins = [
    "http://localhost:5173",
    "http://localhost:3000", 
    "https://tripmebuddy.senseddreams.com",
    "https://senseddreams.com",
]

# Add origins from settings if configured
# if settings.BACKEND_CORS_ORIGINS:
#     cors_origins.extend([str(origin) for origin in settings.BACKEND_CORS_ORIGINS])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Debug mode: {settings.DEBUG}")

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
app.include_router(trips.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Trip Me Buddy API",
        "version": settings.VERSION,
        "docs": "/docs" if settings.DEBUG else "Documentation disabled in production"
    }
