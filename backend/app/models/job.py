"""
Job tracking models for async trip planning operations.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.models.base import Base


class Job(Base):
    """
    Tracks async job execution for trip planning.

    Jobs are stored both in PostgreSQL (for persistence) and Redis (for real-time status).
    """
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(50), unique=True, index=True, nullable=False)  # UUID for external reference
    user_id = Column(String(255), nullable=False, index=True)  # Keycloak UUID (changed from Integer)
    job_type = Column(String(50), nullable=False)  # e.g., "trip_planning"
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    current_step = Column(String(200))  # Current processing step description

    # Input and output data
    input_data = Column(JSON)  # Original request data
    result_data = Column(JSON)  # Final result when completed
    error_message = Column(Text)  # Error details if failed

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<Job(job_id='{self.job_id}', type='{self.job_type}', status='{self.status}')>"
