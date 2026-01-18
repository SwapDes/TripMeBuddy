from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.core.security import get_current_user
from app.core.database import get_db
from app.core.config import settings
from app.services.amadeus_service import AmadeusService
from app.schemas.travel import (
    FlightSearchRequest,
    FlightSearchResponse,
    HotelSearchRequest,
    HotelSearchResponse,
    LocationSearchRequest,
    LocationSearchResponse,
    AIRecommendationRequest,
    AIRecommendationResponse,
)
from app.models.travel import FlightSearch, HotelSearch
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/travel", tags=["travel"])


# Initialize Amadeus service
def get_amadeus_service() -> AmadeusService:
    """Get Amadeus service instance"""
    return AmadeusService(
        api_key=settings.AMADEUS_API_KEY,
        api_secret=settings.AMADEUS_API_SECRET
    )


@router.post("/flights/search", response_model=FlightSearchResponse)
async def search_flights(
        request: FlightSearchRequest,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db),
        amadeus: AmadeusService = Depends(get_amadeus_service)
):
    """
    Search for flight offers using Amadeus API

    - **origin**: Origin airport IATA code (e.g., DEL)
    - **destination**: Destination airport IATA code (e.g., BKK)
    - **departure_date**: Departure date (YYYY-MM-DD)
    - **return_date**: Optional return date (YYYY-MM-DD)
    - **adults**: Number of adult passengers (1-9)
    - **max_results**: Maximum number of results (1-50)
    """
    try:
        logger.info(f"Flight search request: {request.origin} -> {request.destination}")

        # Search flights via Amadeus
        result = amadeus.search_flights(
            origin=request.origin.upper(),
            destination=request.destination.upper(),
            departure_date=request.departure_date,
            return_date=request.return_date,
            adults=request.adults,
            max_results=request.max_results
        )

        # Log search to database for analytics
        try:
            flight_search = FlightSearch(
                user_id=current_user.get("sub"),
                origin=request.origin.upper(),
                destination=request.destination.upper(),
                departure_date=datetime.strptime(request.departure_date, "%Y-%m-%d"),
                return_date=datetime.strptime(request.return_date, "%Y-%m-%d") if request.return_date else None,
                adults=request.adults,
                results_count=result.get("count", 0),
                search_response=result.get("data", [])[:5] if result.get("success") else None
                # Store only first 5 for analytics
            )

            # Calculate price statistics if results exist
            if result.get("success") and result.get("data"):
                prices = []
                for offer in result["data"]:
                    try:
                        price = float(offer.get("price", {}).get("total", 0))
                        if price > 0:
                            prices.append(price)
                    except (ValueError, TypeError):
                        continue

                if prices:
                    flight_search.min_price = min(prices)
                    flight_search.max_price = max(prices)
                    flight_search.avg_price = sum(prices) / len(prices)

            db.add(flight_search)
            db.commit()
            logger.info("Flight search logged to database")

        except Exception as db_error:
            logger.error(f"Failed to log flight search: {db_error}")
            db.rollback()

        return FlightSearchResponse(
            success=result.get("success", False),
            count=result.get("count", 0),
            data=result.get("data", []),
            error=result.get("error")
        )

    except Exception as e:
        logger.error(f"Flight search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Flight search failed: {str(e)}"
        )


@router.post("/hotels/search", response_model=HotelSearchResponse)
async def search_hotels(
        request: HotelSearchRequest,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db),
        amadeus: AmadeusService = Depends(get_amadeus_service)
):
    """
    Search for hotel offers using Amadeus API

    - **city_code**: IATA city code (e.g., BKK)
    - **check_in_date**: Check-in date (YYYY-MM-DD)
    - **check_out_date**: Check-out date (YYYY-MM-DD)
    - **adults**: Number of adult guests (1-9)
    - **radius**: Search radius
    - **radius_unit**: KM or MILE
    - **max_results**: Maximum number of results (1-50)
    """
    try:
        logger.info(f"Hotel search request: {request.city_code}")

        # Search hotels via Amadeus
        result = amadeus.search_hotels(
            city_code=request.city_code.upper(),
            check_in_date=request.check_in_date,
            check_out_date=request.check_out_date,
            adults=request.adults,
            radius=request.radius,
            radius_unit=request.radius_unit,
            max_results=request.max_results
        )

        # Log search to database for analytics
        try:
            hotel_search = HotelSearch(
                user_id=current_user.get("sub"),
                city_code=request.city_code.upper(),
                check_in_date=datetime.strptime(request.check_in_date, "%Y-%m-%d"),
                check_out_date=datetime.strptime(request.check_out_date, "%Y-%m-%d"),
                adults=request.adults,
                results_count=result.get("count", 0),
                search_response=result.get("data", [])[:5] if result.get("success") else None
            )

            # Calculate price statistics if results exist
            if result.get("success") and result.get("data"):
                prices = []
                for hotel in result["data"]:
                    try:
                        offers = hotel.get("offers", [])
                        if offers:
                            price = float(offers[0].get("price", {}).get("total", 0))
                            if price > 0:
                                prices.append(price)
                    except (ValueError, TypeError):
                        continue

                if prices:
                    hotel_search.min_price = min(prices)
                    hotel_search.max_price = max(prices)
                    hotel_search.avg_price = sum(prices) / len(prices)

            db.add(hotel_search)
            db.commit()
            logger.info("Hotel search logged to database")

        except Exception as db_error:
            logger.error(f"Failed to log hotel search: {db_error}")
            db.rollback()

        return HotelSearchResponse(
            success=result.get("success", False),
            data=result.get("data", []),
            count=result.get("count", 0),
            message=result.get("message"),
            error=result.get("error")
        )

    except Exception as e:
        logger.error(f"Hotel search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hotel search failed: {str(e)}"
        )


@router.get("/locations", response_model=LocationSearchResponse)
async def search_locations(
        q: str,
        max_results: int = 10,
        current_user: dict = Depends(get_current_user),
        amadeus: AmadeusService = Depends(get_amadeus_service)
):
    """
    Search for airports and cities (autocomplete)

    - **q**: Search keyword (minimum 2 characters)
    - **max_results**: Maximum number of results (1-20)
    """
    try:
        if len(q) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search keyword must be at least 2 characters"
            )

        logger.info(f"Location search request: {q}")

        result = amadeus.search_locations(
            keyword=q,
            max_results=min(max_results, 20)
        )

        return LocationSearchResponse(
            success=result.get("success", False),
            data=result.get("data", []),
            count=result.get("count", 0)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Location search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Location search failed: {str(e)}"
        )


@router.post("/recommendations")
async def get_ai_recommendations(
        request: AIRecommendationRequest,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Get AI-powered travel recommendations (Placeholder for Week 4 Phase 3)

    This endpoint will be fully implemented when we integrate Gemini API in Phase 3.
    For now, it returns a placeholder response.
    """
    return {
        "message": "AI recommendations endpoint - to be implemented in Phase 3",
        "status": "placeholder",
        "received_preferences": {
            "budget": request.budget,
            "interests": request.interests,
            "travel_style": request.travel_style,
            "origin": request.origin
        }
    }


@router.get("/price-analysis")
async def get_price_analysis(
        origin: str,
        destination: str,
        departure_date: str,
        current_user: dict = Depends(get_current_user),
        amadeus: AmadeusService = Depends(get_amadeus_service)
):
    """
    Get price analysis and insights for a flight route

    - **origin**: Origin airport IATA code
    - **destination**: Destination airport IATA code
    - **departure_date**: Departure date (YYYY-MM-DD)
    """
    try:
        logger.info(f"Price analysis request: {origin} -> {destination}")

        result = amadeus.get_flight_price_analysis(
            origin=origin.upper(),
            destination=destination.upper(),
            departure_date=departure_date
        )

        return result

    except Exception as e:
        logger.error(f"Price analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Price analysis failed: {str(e)}"
        )
