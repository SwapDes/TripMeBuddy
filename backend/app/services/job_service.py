"""
Service for managing background jobs and their status.
"""
import json
import logging
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from app.models.job import Job
from app.schemas.job import JobCreate, JobResponse, JobStatusUpdate

logger = logging.getLogger(__name__)


class JobService:
    """Service for job management and real-time status streaming."""

    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis

    async def create_job(self, job_create: JobCreate) -> JobResponse:
        """
        Create a new job in database and Redis.

        Args:
            job_create: Job creation data

        Returns:
            JobResponse with job details
        """
        job_id = str(uuid4())

        # Create job in database
        job = Job(
            job_id=job_id,
            user_id=job_create.user_id,
            job_type=job_create.job_type,
            status="pending",
            progress=0,
            input_data=job_create.input_data
        )

        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        # Initialize job in Redis
        job_data = {
            "job_id": job_id,
            "user_id": job_create.user_id,
            "job_type": job_create.job_type,
            "status": "pending",
            "progress": 0,
            "created_at": datetime.now().isoformat()
        }
        await self.redis.setex(
            f"job:{job_id}",
            3600,  # 1 hour TTL
            json.dumps(job_data)
        )

        return self._job_to_response(job)

    async def get_job(self, job_id: str) -> Optional[JobResponse]:
        """
        Get job status from Redis (fast) or database (fallback).

        Args:
            job_id: Job identifier

        Returns:
            JobResponse or None if not found
        """
        # Try Redis first (fastest)
        redis_data = await self.redis.get(f"job:{job_id}")
        if redis_data:
            data = json.loads(redis_data)
            # Redis might not have all fields, fallback to DB for complete data
            if 'user_id' not in data or 'job_type' not in data:
                # Fetch from database for complete data
                result = await self.db.execute(
                    select(Job).where(Job.job_id == job_id)
                )
                job = result.scalar_one_or_none()
                if job:
                    return self._job_to_response(job)
                return None

            return JobResponse(
                job_id=job_id,
                user_id=data.get("user_id"),
                job_type=data.get("job_type"),
                status=data.get("status", "unknown"),
                progress=data.get("progress", 0),
                current_step=data.get("current_step"),
                error_message=data.get("error_message"),
                created_at=data.get("created_at")
            )

        # Fallback to database
        result = await self.db.execute(
            select(Job).where(Job.job_id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            return None

        return self._job_to_response(job)

    async def stream_job_progress(
            self,
            job_id: str,
            timeout: int = 300
    ) -> AsyncGenerator[str, None]:
        """
        Stream real-time job progress updates via Redis pub/sub.

        This is the CRITICAL fix - uses Redis SUBSCRIBE to listen for events
        published by the worker, ensuring subscribers > 0.

        Args:
            job_id: Job identifier
            timeout: Maximum time to wait for completion (seconds)

        Yields:
            SSE-formatted messages
        """
        channel = f"job:{job_id}:events"

        # Create pub/sub connection
        pubsub = self.redis.pubsub()

        try:
            # Subscribe to job events channel - THIS IS THE KEY FIX
            await pubsub.subscribe(channel)
            logger.info(f"Subscribed to {channel}")

            # Send initial status
            job = await self.get_job(job_id)
            if job:
                initial_data = {
                    'job_id': job_id,
                    'user_id': job.user_id,
                    'job_type': job.job_type,
                    'status': job.status,
                    'progress': job.progress,
                    'created_at': job.created_at.isoformat() if job.created_at else None
                }
                yield f"data: {json.dumps(initial_data)}\n\n"

            # Listen for messages with timeout
            start_time = asyncio.get_event_loop().time()

            while True:
                # Check timeout
                if asyncio.get_event_loop().time() - start_time > timeout:
                    logger.warning(f"SSE stream timeout for job {job_id}")
                    yield f"data: {json.dumps({'error': 'timeout'})}\n\n"
                    break

                try:
                    # Wait for message with short timeout to allow checking completion
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                        timeout=2.0
                    )

                    if message and message['type'] == 'message':
                        # Forward the message to SSE client
                        data = message['data']
                        if isinstance(data, bytes):
                            data = data.decode('utf-8')

                        logger.info(f"SSE forwarding message for job {job_id}")
                        yield f"data: {data}\n\n"

                        # Check if job completed
                        try:
                            msg_data = json.loads(data)
                            if msg_data.get('status') in ['completed', 'failed']:
                                logger.info(f"Job {job_id} {msg_data.get('status')}, closing SSE stream")
                                break
                        except json.JSONDecodeError:
                            pass

                except asyncio.TimeoutError:
                    # No message received, continue listening
                    continue

                # Small delay to prevent tight loop
                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Error in SSE stream for job {job_id}: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        finally:
            # Clean up subscription
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            logger.info(f"Closed SSE stream for job {job_id}")

    def _job_to_response(self, job: Job) -> JobResponse:
        """Convert Job model to JobResponse schema."""
        return JobResponse(
            job_id=job.job_id,
            user_id=job.user_id,
            job_type=job.job_type,
            status=job.status,
            progress=job.progress,
            current_step=None,
            error_message=job.error_message,
            created_at=job.created_at
        )
