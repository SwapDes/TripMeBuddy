"""
Authentication endpoints for user registration and password management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import re

from app.core.database import get_async_db
from app.models.user import User
from app.services.keycloak_admin import KeycloakAdmin
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


# Pydantic models
class RegisterRequest(BaseModel):
    """User registration request"""
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v


class RegisterResponse(BaseModel):
    """User registration response"""
    success: bool
    message: str
    user_id: Optional[str] = None
    email: str


class PasswordResetRequest(BaseModel):
    """Password reset request"""
    email: EmailStr


# Keycloak admin client
def get_keycloak_admin() -> KeycloakAdmin:
    """Get Keycloak admin client"""
    return KeycloakAdmin(
        server_url=settings.KEYCLOAK_SERVER_URL,
        realm_name=settings.KEYCLOAK_REALM,
        client_id=settings.KEYCLOAK_BACKEND_CLIENT_ID,
        client_secret=settings.KEYCLOAK_BACKEND_CLIENT_SECRET,
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_async_db),
    keycloak: KeycloakAdmin = Depends(get_keycloak_admin)
):
    """
    Register a new user
    
    Creates user in both Keycloak and database.
    No email verification required for MVP.
    """
    try:
        # Parse full name into first and last name
        name_parts = request.full_name.strip().split(maxsplit=1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        # Check if user already exists in database
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.email == request.email.lower())
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        
        # Create user in Keycloak
        try:
            keycloak_user_id = await keycloak.create_user(
                email=request.email.lower(),
                password=request.password,
                first_name=first_name,
                last_name=last_name,
                email_verified=True  # Skip email verification for MVP
            )
        except ValueError as e:
            # User already exists in Keycloak
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user in authentication system: {str(e)}"
            )
        
        # Create user in database
        name_parts = request.full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        db_user = User(
            id=keycloak_user_id,
            email=request.email.lower(),
            username=request.email.lower().split('@')[0],
            first_name=first_name,
            last_name=last_name
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        return RegisterResponse(
            success=True,
            message="Registration successful! You can now login.",
            user_id=db_user.id,
            email=db_user.email
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/forgot-password")
async def forgot_password(request: PasswordResetRequest):
    """
    Request password reset
    
    MVP: Returns message to contact support.
    Future: Will send email with reset link.
    """
    return {
        "success": True,
        "message": (
            "Password reset is currently handled manually. "
            "Please contact support@tripmebuddy.com with your email address "
            "and we'll help you reset your password within 24 hours."
        )
    }


@router.get("/check-email/{email}")
async def check_email_availability(
    email: str,
    keycloak: KeycloakAdmin = Depends(get_keycloak_admin)
):
    """
    Check if email is available for registration
    """
    try:
        exists = await keycloak.user_exists(email.lower())
        return {
            "email": email.lower(),
            "available": not exists
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check email availability: {str(e)}"
        )
