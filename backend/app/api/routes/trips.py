from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging
from datetime import datetime

from app.core.security import get_current_user
from app.core.database import get_async_db
from app.schemas.trip import (
    TripCreate,
    TripUpdate,
    TripResponse,
    TripSummary,
    TripListResponse
)
from app.models.trip import Trip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trips", tags=["trips"])


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string to datetime object"""
    if not date_str or date_str == "null":
        return None

    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
        trip_id: int,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Get a specific trip by ID

    Returns complete trip details including full trip plan
    """
    try:
        user_id = current_user.get("sub")
        logger.info(f"Fetching trip {trip_id} for user {user_id}")

        # Use async query
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
            import json
            trip.trip_plan = json.loads(trip.trip_plan)
        
        if isinstance(trip.preferences, str):
            import json
            trip.preferences = json.loads(trip.preferences) if trip.preferences else None
        
        if isinstance(trip.selected_flight, str):
            import json
            trip.selected_flight = json.loads(trip.selected_flight) if trip.selected_flight else None
        
        if isinstance(trip.selected_hotel, str):
            import json
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


@router.get("", response_model=TripListResponse)
async def list_trips(
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(10, ge=1, le=100, description="Items per page"),
        status_filter: Optional[str] = Query(None, description="Filter by status"),
        favorites_only: bool = Query(False, description="Show only favorites"),
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db)
):
    """
    Get user's saved trips with pagination
    """
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
        import json
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
