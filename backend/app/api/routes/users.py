from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text  # Add this import
from typing import Dict
from app.core.database import get_db
from app.core.security import get_current_user, get_current_active_user
from app.schemas.user import User, UserProfile, UserCreate
from app.models.user import User as UserModel

router = APIRouter()


@router.get("/users/me", response_model=UserProfile)
async def read_users_me(
        current_user: Dict = Depends(get_current_active_user)
):
    """
    Get current user information from JWT token.
    This endpoint returns user info directly from Keycloak without database lookup.
    """
    return UserProfile(**current_user)


@router.get("/users/profile", response_model=User)
async def read_user_profile(
        current_user: Dict = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """
    Get current user's database profile.
    Creates user in database if doesn't exist.
    """
    user_id = current_user.get("sub")

    # Check if user exists in database
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()

    # Create user if doesn't exist
    if not db_user:
        db_user = UserModel(
            id=user_id,
            email=current_user.get("email"),
            username=current_user.get("preferred_username"),
            first_name=current_user.get("given_name"),
            last_name=current_user.get("family_name"),
            is_active=True
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

    return db_user


@router.get("/users/test-db")
async def test_database_connection(db: Session = Depends(get_db)):
    """
    Test endpoint to verify database connectivity.
    Public endpoint for debugging.
    """
    try:
        # Use text() wrapper for SQLAlchemy 2.0
        db.execute(text("SELECT 1"))
        return {
            "status": "success",
            "message": "Database connection successful"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database connection failed: {str(e)}"
        )


@router.get("/users/test-redis")
async def test_redis_connection():
    """
    Test endpoint to verify Redis connectivity.
    Public endpoint for debugging.
    """
    try:
        from app.core.cache import get_redis
        redis_client = get_redis()

        # Test Redis with ping
        redis_client.ping()

        # Test set and get
        redis_client.set("test_key", "test_value", ex=10)
        value = redis_client.get("test_key")

        return {
            "status": "success",
            "message": "Redis connection successful",
            "test_value": value
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Redis connection failed: {str(e)}"
        )
