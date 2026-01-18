from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class TripPreference(Base):
    """User's travel preferences for AI recommendations"""
    __tablename__ = "trip_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), index=True, nullable=False)

    # Preferences
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    preferred_destinations = Column(JSON, nullable=True)  # List of cities/countries
    interests = Column(JSON, nullable=True)  # List of interests (beach, culture, adventure, etc.)
    travel_style = Column(String(100), nullable=True)  # luxury, budget, backpacker, etc.
    preferred_airlines = Column(JSON, nullable=True)
    preferred_hotel_chains = Column(JSON, nullable=True)
    dietary_restrictions = Column(JSON, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FlightSearch(Base):
    """Log of flight searches for analytics"""
    __tablename__ = "flight_searches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), index=True, nullable=False)

    # Search parameters
    origin = Column(String(10), nullable=False)
    destination = Column(String(10), nullable=False)
    departure_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime, nullable=True)
    adults = Column(Integer, default=1)

    # Search results metadata
    results_count = Column(Integer, default=0)
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    avg_price = Column(Float, nullable=True)

    # Raw response for analytics
    search_response = Column(JSON, nullable=True)

    # Metadata
    search_timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class HotelSearch(Base):
    """Log of hotel searches for analytics"""
    __tablename__ = "hotel_searches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), index=True, nullable=False)

    # Search parameters
    city_code = Column(String(10), nullable=False)
    city_name = Column(String(255), nullable=True)
    check_in_date = Column(DateTime, nullable=False)
    check_out_date = Column(DateTime, nullable=False)
    adults = Column(Integer, default=1)

    # Search results metadata
    results_count = Column(Integer, default=0)
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    avg_price = Column(Float, nullable=True)

    # Raw response for analytics
    search_response = Column(JSON, nullable=True)

    # Metadata
    search_timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class AIRecommendation(Base):
    """AI-generated travel recommendations"""
    __tablename__ = "ai_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), index=True, nullable=False)

    # User query
    user_query = Column(Text, nullable=False)

    # AI response
    recommendation = Column(JSON, nullable=False)  # Structured recommendation from Gemini
    model_used = Column(String(100), default="gemini-2.0-flash-exp")

    # Context
    context_data = Column(JSON, nullable=True)  # Additional context used for recommendation

    # User feedback
    user_rating = Column(Integer, nullable=True)  # 1-5 rating
    user_feedback = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)