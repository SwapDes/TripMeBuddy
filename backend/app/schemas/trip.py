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
