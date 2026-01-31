from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Trip(Base):
    """User's saved trip plans"""
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), index=True, nullable=False)

    # Trip identification
    trip_name = Column(String(255), nullable=False)
    destination = Column(String(255), nullable=False)
    country = Column(String(100), nullable=True)

    # Trip details
    origin = Column(String(100), nullable=True)
    departure_date = Column(DateTime, nullable=True)
    return_date = Column(DateTime, nullable=True)
    duration_days = Column(Integer, nullable=True)
    travelers_count = Column(Integer, default=1)

    # Budget
    budget = Column(Float, nullable=True)
    currency = Column(String(10), default="USD")

    # Complete trip plan (JSON)
    trip_plan = Column(JSON, nullable=False)  # Full plan from TripPlanner

    # Preferences used (for regeneration)
    preferences = Column(JSON, nullable=True)

    # Flight and hotel data
    selected_flight = Column(JSON, nullable=True)
    selected_hotel = Column(JSON, nullable=True)

    # Status
    is_booked = Column(Boolean, default=False)
    is_favorite = Column(Boolean, default=False)
    status = Column(String(50), default="planned")  # planned, booked, completed, cancelled

    # Notes
    user_notes = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Trip(id={self.id}, name='{self.trip_name}', destination='{self.destination}')>"
