"""
Worker for processing trip planning jobs in the background.
Uses synchronous operations to avoid event loop conflicts.
"""
import json
import logging
from typing import Dict, Any
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import redis

from app.schemas.job import JobStatusUpdate
from app.services.trip_planner import TripPlanner
from app.services.amadeus_service import AmadeusService
from app.core.config import settings
from app.models.trip import Trip
from app.models.job import Job

logger = logging.getLogger(__name__)


def start_trip_planning_job_sync(
        job_id: str,
        trip_request: Dict[str, Any]
) -> None:
    """
    Synchronous entry point for trip planning job.
    Runs entirely in sync mode to avoid event loop issues.

    Args:
        job_id: Job identifier
        trip_request: Trip planning request data
    """
    logger.info(f"Worker entry point: Job {job_id}")
    print(f"WORKER ENTRY: Job {job_id} starting", flush=True)

    # Create sync DB engine and session
    sync_db_url = settings.DATABASE_URL.replace('+asyncpg', '')  # Use psycopg2
    engine = create_engine(sync_db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)

    # Create sync Redis client
    redis_client = redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True
    )

    try:
        with SessionLocal() as db:
            # Get job to extract user_id
            job = db.query(Job).filter(Job.job_id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            user_id = job.user_id
            logger.info(f"Starting trip planning job: {job_id} for user: {user_id}")
            print(f"WORKER: Starting trip planning job: {job_id} for user: {user_id}", flush=True)

            # Update job status using sync operations
            _update_job_status_sync(db, redis_client, job_id, {
                "status": "running",
                "progress": 5,
                "current_step": "Analyzing your travel preferences..."
            })

            # Progress updates
            _update_job_status_sync(db, redis_client, job_id, {
                "progress": 10,
                "current_step": "Understanding your travel style and requirements..."
            })

            _update_job_status_sync(db, redis_client, job_id, {
                "progress": 20,
                "current_step": "Researching destinations that match your preferences..."
            })

            _update_job_status_sync(db, redis_client, job_id, {
                "progress": 40,
                "current_step": "Searching for the best flight options..."
            })

            _update_job_status_sync(db, redis_client, job_id, {
                "progress": 60,
                "current_step": "Finding ideal accommodations for your trip..."
            })

            _update_job_status_sync(db, redis_client, job_id, {
                "progress": 80,
                "current_step": "Creating your personalized itinerary..."
            })

            # Execute trip planning
            logger.info(f"Executing trip planner for job: {job_id}")

            amadeus_service = AmadeusService(
                api_key=settings.AMADEUS_API_KEY,
                api_secret=settings.AMADEUS_API_SECRET
            )

            trip_planner = TripPlanner(
                gemini_api_key=settings.GEMINI_API_KEY,
                amadeus_service=amadeus_service,
                redis_client=redis_client
            )

            user_request_text = trip_request.get("request", "")
            if not user_request_text:
                raise ValueError("Missing 'request' field in trip_request data")

            logger.info(f"Processing request: {user_request_text[:100]}...")
            print(f"WORKER: Processing request (length: {len(user_request_text)}): {user_request_text[:100]}...",
                  flush=True)

            # Execute trip planning (synchronous)
            result = trip_planner.plan_trip(user_request_text, trip_request)

            logger.info(f"Trip planning completed for job: {job_id}")

            if result:
                logger.info(f"Result keys: {list(result.keys())}")
                if 'flights' in result:
                    flight_count = result['flights'].get('count', 0) if isinstance(result['flights'], dict) else 0
                    logger.info(f"Flights found: {flight_count}")
                if 'hotels' in result:
                    hotel_count = len(result['hotels'].get('hotels', [])) if isinstance(result['hotels'], dict) else 0
                    logger.info(f"Hotels found: {hotel_count}")

            _update_job_status_sync(db, redis_client, job_id, {
                "progress": 95,
                "current_step": "Finalizing your trip plan..."
            })

            # Save or update trip to database with correct user_id
            trip_id = _save_trip_to_database_sync(db, job_id, result, trip_request, user_id)

            # For re-planning jobs, notify that the trip was updated
            if trip_request.get('trip_id'):
                logger.info(f"Re-planning complete - Trip {trip_id} updated with new plan")

            # Mark job as completed
            _complete_job_sync(db, redis_client, job_id, result, trip_id)

            logger.info(f"Job {job_id} completed successfully with trip_id: {trip_id}")
            print(f"WORKER: Job {job_id} completed successfully with trip_id: {trip_id}", flush=True)

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {str(e)}", exc_info=True)
        print(f"WORKER ERROR: Job {job_id} failed: {str(e)}", flush=True)

        try:
            with SessionLocal() as db:
                _fail_job_sync(db, redis_client, job_id, str(e))
        except Exception as fail_error:
            logger.error(f"Failed to mark job as failed: {str(fail_error)}")

    finally:
        redis_client.close()
        engine.dispose()


def _update_job_status_sync(
        db: Session,
        redis_client: redis.Redis,
        job_id: str,
        updates: Dict[str, Any]
) -> None:
    """Update job status in both DB and Redis synchronously."""
    # Update Redis
    key = f"job:{job_id}"
    redis_data = redis_client.get(key)

    if redis_data:
        data = json.loads(redis_data)
    else:
        # Initialize data if not exists
        data = {"job_id": job_id}

    data.update(updates)
    data['updated_at'] = datetime.now().isoformat()
    redis_client.setex(key, 3600, json.dumps(data))

    # Always publish progress event for SSE streaming
    channel = f"job:{job_id}:events"
    message = json.dumps(data)
    result = redis_client.publish(channel, message)
    logger.info(f"Published to {channel}, subscribers: {result}, progress: {data.get('progress', 'N/A')}")
    print(f"WORKER: Published progress update to {channel}, subscribers: {result}", flush=True)


def _complete_job_sync(
        db: Session,
        redis_client: redis.Redis,
        job_id: str,
        result_data: Dict[str, Any],
        trip_id: int
) -> None:
    """Mark job as completed synchronously."""
    # Update database
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if job:
        job.status = "completed"
        job.progress = 100
        job.result_data = result_data
        job.completed_at = datetime.now()
        db.commit()

    # Update Redis
    key = f"job:{job_id}"
    completion_data = {
        "job_id": job_id,
        "status": "completed",
        "progress": 100,
        "trip_id": trip_id,
        "updated_at": datetime.now().isoformat()
    }
    redis_client.setex(key, 3600, json.dumps(completion_data))

    # Publish completion event
    redis_client.publish(
        f"job:{job_id}:events",
        json.dumps(completion_data)
    )


def _fail_job_sync(
        db: Session,
        redis_client: redis.Redis,
        job_id: str,
        error_message: str
) -> None:
    """Mark job as failed synchronously."""
    # Update database
    job = db.query(Job).filter(Job.job_id == job_id).first()
    if job:
        job.status = "failed"
        job.error_message = error_message
        job.completed_at = datetime.now()
        db.commit()

    # Update Redis
    key = f"job:{job_id}"
    fail_data = {
        "job_id": job_id,
        "status": "failed",
        "error_message": error_message,
        "updated_at": datetime.now().isoformat()
    }
    redis_client.setex(key, 3600, json.dumps(fail_data))


def _save_trip_to_database_sync(
        db: Session,
        job_id: str,
        result: Dict[str, Any],
        trip_request: Dict[str, Any],
        user_id: str
) -> int:
    """
    Save trip to database synchronously with support for BOTH creation and updating.
    
    If trip_request contains 'trip_id', updates that existing trip.
    Otherwise, creates a new trip.
    """
    try:
        from datetime import timedelta
        
        trip_plan = result.get("trip_plan", {})
        trip_summary = trip_plan.get("trip_summary", {})
        preferences = result.get("preferences", {})
        destination_info = result.get("destination", {})
        
        destination = destination_info.get("city", trip_summary.get("destination", "Unknown"))
        
        # ============================================================================
        # IMPROVED DATE EXTRACTION
        # ============================================================================
        
        def parse_date_flexible(date_value):
            """Parse date from multiple formats"""
            if not date_value:
                return None
            
            # Already a datetime object
            if isinstance(date_value, datetime):
                return date_value
            
            # String - try multiple formats
            if isinstance(date_value, str):
                date_formats = [
                    "%Y-%m-%d",           # 2026-03-15
                    "%Y/%m/%d",           # 2026/03/15
                    "%d-%m-%Y",           # 15-03-2026
                    "%d/%m/%Y",           # 15/03/2026
                    "%B %d, %Y",          # March 15, 2026
                    "%b %d, %Y",          # Mar 15, 2026
                    "%Y-%m-%dT%H:%M:%S",  # 2026-03-15T00:00:00
                    "%Y-%m-%d %H:%M:%S",  # 2026-03-15 00:00:00
                ]
                
                for fmt in date_formats:
                    try:
                        return datetime.strptime(date_value, fmt)
                    except (ValueError, TypeError):
                        continue
                
                logger.warning(f"Could not parse date: {date_value}")
            
            return None
        
        # Try multiple sources for dates
        departure_date = None
        return_date = None
        
        # Source 1: trip_summary.travel_dates (primary)
        travel_dates = trip_summary.get("travel_dates", {})
        if travel_dates:
            departure_date = parse_date_flexible(travel_dates.get("departure"))
            return_date = parse_date_flexible(travel_dates.get("return"))
            logger.info(f"Dates from trip_summary.travel_dates: dep={departure_date}, ret={return_date}")
        
        # Source 2: preferences.dates (fallback)
        if not departure_date or not return_date:
            pref_dates = preferences.get("dates", {})
            if pref_dates:
                if not departure_date:
                    departure_date = parse_date_flexible(pref_dates.get("departure"))
                if not return_date:
                    return_date = parse_date_flexible(pref_dates.get("return"))
                logger.info(f"Dates from preferences.dates: dep={departure_date}, ret={return_date}")
        
        # Source 3: flight search params (additional fallback)
        if not departure_date or not return_date:
            flights = result.get("flights", {})
            search_params = flights.get("search_params", {})
            if search_params:
                if not departure_date:
                    departure_date = parse_date_flexible(search_params.get("departure_date"))
                if not return_date:
                    return_date = parse_date_flexible(search_params.get("return_date"))
                logger.info(f"Dates from flight search_params: dep={departure_date}, ret={return_date}")
        
        # Calculate or extract duration_days
        duration_days = trip_summary.get("duration_days")
        
        # If duration_days is missing but we have both dates, calculate it
        if not duration_days and departure_date and return_date:
            duration_days = (return_date - departure_date).days
            logger.info(f"Calculated duration_days from dates: {duration_days}")
        
        # If we have departure_date and duration but no return_date, calculate return_date
        if departure_date and duration_days and not return_date:
            return_date = departure_date + timedelta(days=duration_days)
            logger.info(f"Calculated return_date from departure + duration: {return_date}")
        
        # If we have return_date and duration but no departure_date, calculate departure_date
        if return_date and duration_days and not departure_date:
            departure_date = return_date - timedelta(days=duration_days)
            logger.info(f"Calculated departure_date from return - duration: {departure_date}")
        
        # Log final dates for debugging
        logger.info(f"FINAL DATES - Departure: {departure_date}, Return: {return_date}, Duration: {duration_days}")
        print(f"WORKER: FINAL DATES - Departure: {departure_date}, Return: {return_date}, Duration: {duration_days}", flush=True)
        
        # ============================================================================
        # TRIP NAME GENERATION
        # ============================================================================
        
        trip_name = f"{destination} Trip"
        if departure_date:
            try:
                month_year = departure_date.strftime("%B %Y")
                trip_name = f"{destination} {month_year}"
            except:
                pass
        
        # ============================================================================
        # EXTRACT OTHER FIELDS
        # ============================================================================
        
        # Extract travelers count as integer
        travelers_data = trip_summary.get("travelers", preferences.get("travelers", 1))
        if isinstance(travelers_data, dict):
            travelers_count = (
                travelers_data.get("adults", 1) + 
                travelers_data.get("children", 0) + 
                travelers_data.get("infants", 0)
            )
        else:
            travelers_count = travelers_data if isinstance(travelers_data, int) else 1
        
        # Extract budget
        budget_data = preferences.get("budget", {})
        if isinstance(budget_data, dict):
            budget_total = budget_data.get("total") or budget_data.get("amount")
            currency = budget_data.get("currency", "USD")
        else:
            budget_total = None
            currency = "USD"
        
        # ============================================================================
        # CHECK IF THIS IS AN UPDATE (REPLAN) OR NEW TRIP
        # ============================================================================
        
        existing_trip_id = trip_request.get('trip_id')
        
        if existing_trip_id:
            # UPDATE EXISTING TRIP
            logger.info(f"Re-planning: Updating existing trip {existing_trip_id}")
            print(f"WORKER: Re-planning - Updating existing trip {existing_trip_id}", flush=True)
            
            trip = db.query(Trip).filter(
                Trip.id == existing_trip_id,
                Trip.user_id == user_id
            ).first()
            
            if not trip:
                raise ValueError(f"Trip {existing_trip_id} not found for user {user_id}")
            
            # Update all fields with new data
            trip.destination = destination
            trip.country = destination_info.get("country")
            trip.origin = preferences.get("origin")
            trip.departure_date = departure_date
            trip.return_date = return_date
            trip.duration_days = duration_days
            trip.travelers_count = travelers_count
            trip.budget = budget_total
            trip.currency = currency
            trip.trip_plan = json.dumps(result) if isinstance(result, dict) else result
            trip.preferences = json.dumps(preferences) if isinstance(preferences, dict) else preferences
            trip.updated_at = datetime.now()
            
            # Keep the same trip_name unless destination changed
            if trip.destination != destination:
                trip.trip_name = trip_name
            
            logger.info(f"Updated trip {trip.id} with new plan")
            
        else:
            # CREATE NEW TRIP
            logger.info("Creating new trip")
            print("WORKER: Creating new trip", flush=True)
            
            trip = Trip(
                user_id=user_id,
                trip_name=trip_name,
                destination=destination,
                country=destination_info.get("country"),
                origin=preferences.get("origin"),
                departure_date=departure_date,
                return_date=return_date,
                duration_days=duration_days,
                travelers_count=travelers_count,
                budget=budget_total,
                currency=currency,
                trip_plan=json.dumps(result) if isinstance(result, dict) else result,
                preferences=json.dumps(preferences) if isinstance(preferences, dict) else preferences,
                status="planned"
            )
            
            db.add(trip)
        
        db.commit()
        db.refresh(trip)
        
        logger.info(f"Trip {'updated' if existing_trip_id else 'saved'} successfully with ID: {trip.id} for user: {user_id}")
        logger.info(f"  - Trip Name: {trip.trip_name}")
        logger.info(f"  - Departure: {trip.departure_date}")
        logger.info(f"  - Return: {trip.return_date}")
        logger.info(f"  - Duration: {trip.duration_days} days")
        print(f"WORKER: Trip {'updated' if existing_trip_id else 'saved'} with ID: {trip.id} for user: {user_id}", flush=True)
        print(f"WORKER:   - Departure: {trip.departure_date}, Return: {trip.return_date}, Duration: {trip.duration_days}", flush=True)
        
        return trip.id
        
    except Exception as e:
        logger.error(f"Error saving trip to database: {str(e)}", exc_info=True)
        db.rollback()
        raise
