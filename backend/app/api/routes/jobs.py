"""
API endpoints for job management and async trip planning.
"""
import logging
import asyncio
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.database import get_async_db
from app.core.cache import get_redis
from app.core.security import get_current_user
from app.schemas.job import JobCreate, JobResponse
from app.schemas.travel import TripPlanRequest
from app.services.job_service import JobService
from app.workers.trip_planning_worker import start_trip_planning_job_sync


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Create a dedicated thread pool for background jobs
_background_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="trip-worker")


@router.post("/trip-planning", response_model=JobResponse)
async def create_trip_planning_job(
        trip_request: TripPlanRequest,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db),
        redis: Redis = Depends(get_redis)
) -> JobResponse:
    """
    Create an async trip planning job.

    Returns immediately with a job_id that can be used to track progress.
    The actual trip planning runs in the background.

    Args:
        trip_request: Trip planning request data
        current_user: Authenticated user from JWT
        db: Database session
        redis: Redis client

    Returns:
        JobResponse with job_id and initial status
    """
    try:
        user_id = current_user.get("sub")
        logger.info(f"Creating trip planning job for user: {user_id}")

        # Create job in database and Redis
        job_service = JobService(db, redis)
        job = await job_service.create_job(
            JobCreate(
                user_id=user_id,  # Get from authenticated user
                job_type="trip_planning",
                input_data=trip_request.model_dump()
            )
        )

        logger.info(f"Job created with ID: {job.job_id}")

        # Submit job to thread pool - runs in separate thread with own event loop
        loop = asyncio.get_running_loop()
        loop.run_in_executor(
            _background_executor,
            start_trip_planning_job_sync,
            job.job_id,
            trip_request.model_dump()
        )

        logger.info(f"Background task submitted to executor for job: {job.job_id}")

        return job

    except Exception as e:
        logger.error(f"Error creating trip planning job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create trip planning job: {str(e)}"
        )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(
        job_id: str,
        db: AsyncSession = Depends(get_async_db),
        redis: Redis = Depends(get_redis)
) -> JobResponse:
    """
    Get the current status of a job.

    Args:
        job_id: Job identifier
        db: Database session
        redis: Redis client

    Returns:
        JobResponse with current status and progress
    """
    try:
        job_service = JobService(db, redis)
        job = await job_service.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )

        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/{job_id}/stream")
async def stream_job_progress(
        job_id: str,
        db: AsyncSession = Depends(get_async_db),
        redis: Redis = Depends(get_redis)
):
    """
    Stream real-time progress updates for a job via Server-Sent Events (SSE).

    The stream will send progress updates as they occur and automatically close
    when the job completes or fails.

    Args:
        job_id: Job identifier
        db: Database session
        redis: Redis client

    Returns:
        StreamingResponse with SSE events
    """
    try:
        # Verify job exists
        job_service = JobService(db, redis)
        job = await job_service.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )

        logger.info(f"Starting SSE stream for job: {job_id}")

        # Return SSE stream
        return StreamingResponse(
            job_service.stream_job_progress(job_id, timeout=300),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable buffering in nginx
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming job progress: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stream job progress: {str(e)}"
        )
