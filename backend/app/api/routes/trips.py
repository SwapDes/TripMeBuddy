from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging
from datetime import datetime
import json
import asyncio

from app.core.security import get_current_user
from app.core.database import get_async_db
from app.core.cache import get_redis
from app.schemas.trip import (
    TripCreate,
    TripUpdate,
    TripResponse,
    TripSummary,
    TripListResponse,
    TripReplanRequest,
    TripReplanResponse
)
from app.models.trip import Trip
from app.services.job_service import JobService, JobCreate
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trips", tags=["trips"])

"""
CRITICAL ROUTE ORDERING RULES:

FastAPI matches routes in the ORDER they are defined. 
More specific routes MUST come BEFORE less specific ones.

CORRECT ORDER:
1. Routes with NO path parameters (e.g., GET "")
2. Routes with SPECIFIC literal segments (e.g., POST "/{trip_id}/replan")  
3. Routes with ONLY path parameters (e.g., PUT "/{trip_id}")
"""


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string to datetime object"""
    if not date_str or date_str == "null":
        return None

    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None


# ============================================================================
# COLLECTION ROUTES (no path parameters)
# ============================================================================

@router.get("", response_model=TripListResponse)
async def list_trips(
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, description="Items per page"),
        status_filter: Optional[str] = Query(None, description="Filter by status"),
        favorites_only: bool = Query(False, description="Show only favorites"),
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db)
):
    """Get user's saved trips with pagination"""
    try:
        user_id = current_user.get("sub")

        # Build async query
        stmt = select(Trip).where(Trip.user_id == user_id)

        # Apply filters
        if status_filter:
            stmt = stmt.where(Trip.status == status_filter)

        if favorites_only:
            stmt = stmt.where(Trip.is_favorite == True)

        # Get total count
        count_stmt = select(Trip).where(Trip.user_id == user_id)
        if status_filter:
            count_stmt = count_stmt.where(Trip.status == status_filter)
        if favorites_only:
            count_stmt = count_stmt.where(Trip.is_favorite == True)

        count_result = await db.execute(count_stmt)
        total = len(count_result.scalars().all())

        # Apply pagination
        offset = (page - 1) * page_size
        stmt = stmt.order_by(Trip.created_at.desc()).offset(offset).limit(page_size)

        result = await db.execute(stmt)
        trips = result.scalars().all()

        # Parse JSON columns for each trip
        parsed_trips = []
        for trip in trips:
            if isinstance(trip.trip_plan, str):
                trip.trip_plan = json.loads(trip.trip_plan)
            if isinstance(trip.preferences, str):
                trip.preferences = json.loads(trip.preferences) if trip.preferences else None
            if isinstance(trip.selected_flight, str):
                trip.selected_flight = json.loads(trip.selected_flight) if trip.selected_flight else None
            if isinstance(trip.selected_hotel, str):
                trip.selected_hotel = json.loads(trip.selected_hotel) if trip.selected_hotel else None
            parsed_trips.append(trip)

        # Check if there are more pages
        has_more = (offset + len(parsed_trips)) < total

        return TripListResponse(
            trips=parsed_trips,
            total=total,
            page=page,
            page_size=page_size,
            has_more=has_more
        )

    except Exception as e:
        logger.error(f"Error listing trips: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list trips: {str(e)}"
        )


# ============================================================================
# SPECIFIC ACTION ROUTES (with literal path segments)
# MUST come BEFORE general /{trip_id} routes
# ============================================================================

@router.post("/{trip_id}/replan", response_model=TripReplanResponse)
async def replan_trip(
        trip_id: int,
        replan_request: TripReplanRequest,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db),
        redis: Redis = Depends(get_redis)
):
    """
    Re-plan trip with new parameters

    Creates a background job to regenerate the entire trip plan.
    Returns a job_id that can be used to track progress via SSE.
    """
    try:
        user_id = current_user.get("sub")
        logger.info(f"Re-planning trip {trip_id} for user {user_id}")

        # Fetch existing trip
        result = await db.execute(
            select(Trip).where(
                Trip.id == trip_id,
                Trip.user_id == user_id
            )
        )
        trip = result.scalar_one_or_none()

        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trip {trip_id} not found"
            )

        # Parse existing preferences with robust None handling
        preferences = {}
        if trip.preferences:
            if isinstance(trip.preferences, str):
                try:
                    preferences = json.loads(trip.preferences)
                except:
                    preferences = {}
            elif isinstance(trip.preferences, dict):
                preferences = trip.preferences

        # Ensure preferences is always a dict
        if not preferences:
            preferences = {}

        logger.info(f"Parsed preferences: {preferences}")

        # Build new trip request with robust None handling
        origin = replan_request.origin or trip.origin or "Unknown"
        destination = replan_request.destination or trip.destination or "Unknown"

        # Handle dates with proper None checks
        if replan_request.departure_date:
            departure_date = replan_request.departure_date
        elif trip.departure_date:
            departure_date = trip.departure_date.strftime('%Y-%m-%d')
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="departure_date is required"
            )

        if replan_request.return_date:
            return_date = replan_request.return_date
        elif trip.return_date:
            return_date = trip.return_date.strftime('%Y-%m-%d')
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="return_date is required"
            )

        travelers = replan_request.travelers_count or trip.travelers_count or 1
        budget = replan_request.budget or trip.budget or 1000
        currency = replan_request.currency or trip.currency or "USD"

        # Calculate duration
        try:
            dep_dt = datetime.strptime(departure_date, '%Y-%m-%d')
            ret_dt = datetime.strptime(return_date, '%Y-%m-%d')
            duration_days = (ret_dt - dep_dt).days
            if duration_days <= 0:
                raise ValueError("Return date must be after departure date")
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid dates: {str(e)}"
            )

        # Extract interests and travel style with safe defaults
        interests = preferences.get('interests', ['sightseeing']) if preferences else ['sightseeing']
        travel_style = preferences.get('travel_style', 'comfort') if preferences else 'comfort'

        # Ensure interests is a list
        if not isinstance(interests, list):
            interests = ['sightseeing']

        # Build natural language request for AI
        request_text = f"""Plan a {duration_days}-day trip to {destination} from {origin}.

Departure: {departure_date}
Return: {return_date}
Travelers: {travelers} adult(s)
Budget: {currency} {budget}

Interests: {', '.join(interests)}
Travel style: {travel_style}
"""

        logger.info(f"Generated request for AI")

        # Build job input data dict ONCE - used for both job creation and worker
        job_input_data = {
            "request": request_text,
            "trip_id": trip_id,
            "preferences": {
                "origin": origin,
                "destination_preferences": [destination],
                "budget": {"total": float(budget), "currency": currency},
                "duration": {"days": duration_days},
                "dates": {
                    "departure": departure_date,
                    "return": return_date
                },
                "travelers": {"adults": int(travelers)},
                "interests": interests,
                "travel_style": travel_style
            }
        }

        # Create trip planning job
        job_service = JobService(db, redis)
        job = await job_service.create_job(
            JobCreate(
                user_id=user_id,
                job_type="trip_replan",
                input_data=job_input_data
            )
        )

        logger.info(f"Re-planning job created: {job.job_id} for trip {trip_id}")

        # Submit to background executor - use job_input_data directly (not from job object)
        from app.workers.trip_planning_worker import start_trip_planning_job_sync
        from app.api.routes.jobs import _background_executor

        loop = asyncio.get_running_loop()
        loop.run_in_executor(
            _background_executor,
            start_trip_planning_job_sync,
            job.job_id,
            job_input_data  # Use the dict we built, not job.input_data
        )

        return TripReplanResponse(
            success=True,
            job_id=job.job_id,
            message=f"Re-planning trip {trip_id} in background. Monitor progress via /jobs/{job.job_id}/stream",
            trip_id=trip_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-planning trip {trip_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to replan trip: {str(e)}"
        )


@router.put("/{trip_id}/favorite", response_model=TripResponse)
async def toggle_favorite(
        trip_id: int,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db)
):
    """Toggle favorite status of a trip"""
    try:
        user_id = current_user.get("sub")

        result = await db.execute(
            select(Trip).where(
                Trip.id == trip_id,
                Trip.user_id == user_id
            )
        )
        trip = result.scalar_one_or_none()

        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trip {trip_id} not found"
            )

        trip.is_favorite = not trip.is_favorite
        await db.commit()
        await db.refresh(trip)

        return trip

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling favorite for trip {trip_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle favorite: {str(e)}"
        )


# ============================================================================
# GENERAL RESOURCE ROUTES (with path parameters only)
# MUST come AFTER specific action routes
# ============================================================================

@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
        trip_id: int,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db)
):
    """Get a specific trip by ID"""
    try:
        user_id = current_user.get("sub")
        logger.info(f"Fetching trip {trip_id} for user {user_id}")

        result = await db.execute(
            select(Trip).where(
                Trip.id == trip_id,
                Trip.user_id == user_id
            )
        )
        trip = result.scalar_one_or_none()

        if not trip:
            logger.warning(f"Trip {trip_id} not found for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trip {trip_id} not found"
            )

        # Parse JSON columns if they're strings
        if isinstance(trip.trip_plan, str):
            trip.trip_plan = json.loads(trip.trip_plan)

        if isinstance(trip.preferences, str):
            trip.preferences = json.loads(trip.preferences) if trip.preferences else None

        if isinstance(trip.selected_flight, str):
            trip.selected_flight = json.loads(trip.selected_flight) if trip.selected_flight else None

        if isinstance(trip.selected_hotel, str):
            trip.selected_hotel = json.loads(trip.selected_hotel) if trip.selected_hotel else None

        logger.info(f"Trip {trip_id} retrieved successfully")
        return trip

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trip {trip_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trip: {str(e)}"
        )


@router.put("/{trip_id}", response_model=TripResponse)
async def update_trip(
        trip_id: int,
        trip_update: TripUpdate,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Update trip metadata without re-planning

    Does NOT regenerate the trip plan. Use /replan endpoint for that.
    """
    try:
        user_id = current_user.get("sub")
        logger.info(f"Updating trip {trip_id} for user {user_id}")

        result = await db.execute(
            select(Trip).where(
                Trip.id == trip_id,
                Trip.user_id == user_id
            )
        )
        trip = result.scalar_one_or_none()

        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trip {trip_id} not found"
            )

        # Update fields that are provided
        update_data = trip_update.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == 'departure_date' and value:
                trip.departure_date = datetime.strptime(value, '%Y-%m-%d')
            elif field == 'return_date' and value:
                trip.return_date = datetime.strptime(value, '%Y-%m-%d')
            elif field in ['selected_flight', 'selected_hotel'] and value:
                setattr(trip, field, value)
            else:
                setattr(trip, field, value)

        # Calculate duration if both dates are set
        if trip.departure_date and trip.return_date:
            trip.duration_days = (trip.return_date - trip.departure_date).days

        trip.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(trip)

        # Parse JSON columns for response
        if isinstance(trip.trip_plan, str):
            trip.trip_plan = json.loads(trip.trip_plan)
        if isinstance(trip.preferences, str):
            trip.preferences = json.loads(trip.preferences) if trip.preferences else None
        if isinstance(trip.selected_flight, str):
            trip.selected_flight = json.loads(trip.selected_flight) if trip.selected_flight else None
        if isinstance(trip.selected_hotel, str):
            trip.selected_hotel = json.loads(trip.selected_hotel) if trip.selected_hotel else None

        logger.info(f"Trip {trip_id} updated successfully")
        return trip

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating trip {trip_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update trip: {str(e)}"
        )


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(
        trip_id: int,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db)
):
    """Delete a trip"""
    try:
        user_id = current_user.get("sub")

        result = await db.execute(
            select(Trip).where(
                Trip.id == trip_id,
                Trip.user_id == user_id
            )
        )
        trip = result.scalar_one_or_none()

        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trip {trip_id} not found"
            )

        await db.delete(trip)
        await db.commit()

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting trip {trip_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete trip: {str(e)}"
        )
