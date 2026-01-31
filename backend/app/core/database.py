from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Base class for models
Base = declarative_base()

# These will be initialized lazily
_engine = None
_async_engine = None
_SessionLocal = None
_AsyncSessionLocal = None


def get_engine():
    """Get or create SQLAlchemy engine"""
    global _engine
    if _engine is None:
        from app.core.config import settings
        _engine = create_engine(
            settings.DATABASE_URL.replace("+asyncpg", ""),
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_async_engine():
    """Get or create async SQLAlchemy engine"""
    global _async_engine
    if _async_engine is None:
        from app.core.config import settings
        _async_engine = create_async_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    return _async_engine


def get_session_local():
    """Get or create SessionLocal"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_async_session_local():
    """Get or create AsyncSessionLocal"""
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _AsyncSessionLocal


def get_db():
    """
    Dependency function for FastAPI to get database session.
    Automatically closes session after request.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """
    Async dependency function for FastAPI to get async database session.
    Automatically closes session after request.
    """
    AsyncSessionLocal = get_async_session_local()
    async with AsyncSessionLocal() as session:
        yield session
