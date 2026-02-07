from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# ============================================================================
# TRIP SCHEMAS
# ============================================================================

class TripCreate(BaseModel):
    """Schema for creating a new trip"""
    trip_name: str = Field(..., min_length=1, max_length=255, description="Name for this trip")
    trip_plan: Dict[str, Any] = Field(..., description="Complete trip plan from AI planner")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences used")
    selected_flight: Optional[Dict[str, Any]] = Field(None, description="Selected flight details")
    selected_hotel: Optional[Dict[str, Any]] = Field(None, description="Selected hotel details")
    user_notes: Optional[str] = Field(None, description="User's notes about the trip")

    class Config:
        json_schema_extra = {
            "example": {
                "trip_name": "Bangkok Adventure 2026",
                "trip_plan": {"trip_summary": {}, "destination_info": {}},
                "user_notes": "Don't forget to visit the night markets!"
            }
        }


class TripUpdate(BaseModel):
    """Schema for updating an existing trip"""
    trip_name: Optional[str] = Field(None, min_length=1, max_length=255)
    selected_flight: Optional[Dict[str, Any]] = None
    selected_hotel: Optional[Dict[str, Any]] = None
    is_booked: Optional[bool] = None
    is_favorite: Optional[bool] = None
    status: Optional[str] = Field(None, pattern="^(planned|booked|completed|cancelled)$")
    user_notes: Optional[str] = None


class TripResponse(BaseModel):
    """Schema for trip in API responses"""
    id: int
    user_id: str
    trip_name: str
    destination: str
    country: Optional[str]
    origin: Optional[str]
    departure_date: Optional[datetime]
    return_date: Optional[datetime]
    duration_days: Optional[int]
    travelers_count: int
    budget: Optional[float]
    currency: str
    trip_plan: Dict[str, Any]
    preferences: Optional[Dict[str, Any]]
    selected_flight: Optional[Dict[str, Any]]
    selected_hotel: Optional[Dict[str, Any]]
    is_booked: bool
    is_favorite: bool
    status: str
    user_notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TripSummary(BaseModel):
    """Lightweight schema for trip list view"""
    id: int
    trip_name: str
    destination: str
    country: Optional[str]
    departure_date: Optional[datetime]
    return_date: Optional[datetime]
    duration_days: Optional[int]
    travelers_count: int
    budget: Optional[float]
    currency: str
    is_booked: bool
    is_favorite: bool
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class TripListResponse(BaseModel):
    """Schema for paginated trip list"""
    trips: List[TripSummary]
    total: int
    page: int
    page_size: int
    has_more: bool

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class TripUpdate(BaseModel):
    """Schema for updating trip metadata without re-planning"""
    trip_name: Optional[str] = Field(None, min_length=1, max_length=255)
    departure_date: Optional[str] = Field(None, description="Departure date in YYYY-MM-DD format")
    return_date: Optional[str] = Field(None, description="Return date in YYYY-MM-DD format")
    travelers_count: Optional[int] = Field(None, ge=1, le=20, description="Number of travelers")
    budget: Optional[float] = Field(None, ge=0, description="Trip budget")
    currency: Optional[str] = Field(None, min_length=3, max_length=3, description="Currency code (e.g., USD, INR)")
    selected_flight: Optional[Dict[str, Any]] = None
    selected_hotel: Optional[Dict[str, Any]] = None
    is_booked: Optional[bool] = None
    is_favorite: Optional[bool] = None
    status: Optional[str] = Field(None, pattern="^(planned|booked|completed|cancelled)$")
    user_notes: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "trip_name": "Updated Barcelona Trip",
                "departure_date": "2026-06-15",
                "return_date": "2026-06-25",
                "travelers_count": 3,
                "budget": 5000,
                "currency": "USD",
                "status": "planned",
                "user_notes": "Updated dates to avoid peak season"
            }
        }


class TripReplanRequest(BaseModel):
    """Schema for re-planning a trip with new parameters"""
    departure_date: Optional[str] = Field(None, description="New departure date in YYYY-MM-DD format")
    return_date: Optional[str] = Field(None, description="New return date in YYYY-MM-DD format")
    travelers_count: Optional[int] = Field(None, ge=1, le=20, description="Updated number of travelers")
    budget: Optional[float] = Field(None, ge=0, description="Updated trip budget")
    currency: Optional[str] = Field(None, min_length=3, max_length=3, description="Currency code")
    destination: Optional[str] = Field(None, description="Change destination (triggers full re-plan)")
    origin: Optional[str] = Field(None, description="Change origin city")
    
    class Config:
        json_schema_extra = {
            "example": {
                "departure_date": "2026-07-01",
                "return_date": "2026-07-10",
                "travelers_count": 2,
                "budget": 3000,
                "currency": "USD"
            }
        }


class TripReplanResponse(BaseModel):
    """Response after initiating trip re-planning"""
    success: bool
    job_id: str
    message: str
    trip_id: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "job_id": "job_123abc",
                "message": "Re-planning trip in background. Monitor progress via SSE.",
                "trip_id": 42
            }
        }

class TripReplanRequest(BaseModel):
    """Schema for re-planning a trip with new parameters"""
    departure_date: Optional[str] = Field(None, description="New departure date in YYYY-MM-DD format")
    return_date: Optional[str] = Field(None, description="New return date in YYYY-MM-DD format")
    travelers_count: Optional[int] = Field(None, ge=1, le=20, description="Updated number of travelers")
    budget: Optional[float] = Field(None, ge=0, description="Updated trip budget")
    currency: Optional[str] = Field(None, min_length=3, max_length=3, description="Currency code")
    destination: Optional[str] = Field(None, description="Change destination")
    origin: Optional[str] = Field(None, description="Change origin city")


class TripReplanResponse(BaseModel):
    """Response after initiating trip re-planning"""
    success: bool
    job_id: str
    message: str
    trip_id: int
