from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import date, datetime


# ============================================================================
# FLIGHT SCHEMAS
# ============================================================================

class FlightSearchRequest(BaseModel):
    """Request schema for flight search"""
    origin: str = Field(..., min_length=3, max_length=3, description="Origin IATA code (e.g., DEL)")
    destination: str = Field(..., min_length=3, max_length=3, description="Destination IATA code")
    departure_date: str = Field(..., description="Departure date in YYYY-MM-DD format")
    return_date: Optional[str] = Field(None, description="Return date in YYYY-MM-DD format (optional)")
    adults: int = Field(default=1, ge=1, le=9, description="Number of adult passengers")
    max_results: int = Field(default=10, ge=1, le=50)


class FlightOffer(BaseModel):
    """Parsed flight offer from Amadeus"""
    id: str
    price: float
    currency: str
    departure_time: str
    arrival_time: str
    duration: str
    stops: int
    airline: str
    flight_number: str
    origin: str
    destination: str


class FlightSearchResponse(BaseModel):
    """Response for flight search"""
    success: bool
    count: int
    data: List[Dict] = []
    error: Optional[str] = None


class HotelSearchRequest(BaseModel):
    """Request schema for hotel search"""
    city_code: str = Field(..., min_length=3, max_length=3, description="IATA city code (e.g., BKK)")
    check_in_date: str = Field(..., description="Check-in date (YYYY-MM-DD)")
    check_out_date: str = Field(..., description="Check-out date (YYYY-MM-DD)")
    adults: int = Field(default=1, ge=1, le=9, description="Number of adult guests")
    radius: int = Field(default=5, ge=1, le=50, description="Search radius")
    radius_unit: str = Field(default="KM", pattern="^(KM|MILE)$")
    max_results: int = Field(default=10, ge=1, le=50)


class HotelSearchResponse(BaseModel):
    """Response model for hotel search"""
    success: bool
    data: List[Dict] = []
    count: int = 0
    message: Optional[str] = None
    error: Optional[str] = None


class LocationSearchRequest(BaseModel):
    """Request schema for location autocomplete"""
    keyword: str = Field(..., min_length=2, max_length=100, description="Search keyword")
    max_results: int = Field(default=10, ge=1, le=20)


class LocationSearchResponse(BaseModel):
    """Response schema for location search"""
    success: bool
    data: List[Dict[str, Any]]
    count: int

    class Config:
        from_attributes = True


class AIRecommendationRequest(BaseModel):
    """Request schema for AI travel recommendations"""
    budget: Optional[float] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    interests: List[str] = []
    travel_style: Optional[str] = None
    duration_days: Optional[int] = None
    departure_date: Optional[str] = None
    return_date: Optional[str] = None
    origin: Optional[str] = None
    preferred_destinations: Optional[List[str]] = None
    additional_requirements: Optional[str] = None


class AIRecommendationResponse(BaseModel):
    """Response schema for AI recommendations"""
    recommendation_id: int
    user_query: str
    recommendation: Dict[str, Any]
    model_used: str
    created_at: datetime

    class Config:
        from_attributes = True


class TripPlanRequest(BaseModel):
    """Request for full AI-powered trip planning"""
    request: str = Field(..., description="Natural language description of trip desires", min_length=10)
    preferences: Optional[Dict] = None

    class Config:
        json_schema_extra = {
            "example": {
                "request": "Plan a 7-day beach vacation in Southeast Asia for 2 adults, budget $2000, departing from Delhi in March"
            }
        }


class TripPlanResponse(BaseModel):
    """Response for AI-powered trip planning"""
    success: bool
    trip_plan: Optional[Dict] = None
    flights: Optional[List[Dict]] = None
    hotels: Optional[List[Dict]] = None
    recommendations: Optional[Dict] = None
    message: Optional[str] = None
    error: Optional[str] = None
