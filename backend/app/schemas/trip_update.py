from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from app.models.trip import TripStatus


class TripUpdateRequest(BaseModel):
    status: Optional[TripStatus] = None
    budget: Optional[float] = Field(None, gt=0, description="Budget must be positive")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    user_notes: Optional[str] = Field(None, max_length=1000)

    class Config:
        json_schema_extra = {
            "example": {
                "status": "booked",
                "budget": 2500.00,
                "start_date": "2024-06-15",
                "end_date": "2024-06-22",
                "user_notes": "Updated budget and confirmed booking"
            }
        }
