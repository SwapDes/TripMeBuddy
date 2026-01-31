"""
SQLAlchemy models for TripMeBuddy.
"""
from app.models.base import Base
from app.models.user import User
from app.models.travel import FlightSearch, HotelSearch, TripPreference, AIRecommendation
from app.models.trip import Trip
from app.models.job import Job

__all__ = [
    "Base",
    "User",
    "FlightSearch",
    "HotelSearch",
    "TripPreference",
    "AIRecommendation",
    "Trip",
    "Job",
]
