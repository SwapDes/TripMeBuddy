"""
Pydantic schemas for job management.
"""
from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    """Schema for creating a new job."""
    user_id: str  # Changed from int to str for Keycloak UUID
    job_type: str
    input_data: Dict[str, Any]


class JobStatusUpdate(BaseModel):
    """Schema for updating job status."""
    status: Optional[str] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    current_step: Optional[str] = None
    error_message: Optional[str] = None


class JobResponse(BaseModel):
    """Schema for job information response."""
    job_id: str
    user_id: str  # Changed from int to str for Keycloak UUID
    job_type: str
    status: str
    progress: int
    current_step: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobProgressEvent(BaseModel):
    """Schema for SSE progress event."""
    job_id: str
    status: str
    progress: int
    current_step: Optional[str] = None
    timestamp: datetime


class JobCompletionEvent(BaseModel):
    """Schema for SSE completion event."""
    job_id: str
    status: str  # "completed" or "failed"
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamp: datetime
