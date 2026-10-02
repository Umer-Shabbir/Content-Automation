from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from app.models.enums import JobState, ErrorCategory

class StageMetric(BaseModel):
    stage_name: str
    duration_seconds: float = 0.0
    tokens_used: int = 0
    revisions_count: int = 0
    success: bool = True
    error_message: Optional[str] = None

class JobProgress(BaseModel):
    job_id: str
    current_stage: JobState = JobState.QUEUED
    percent_complete: float = 0.0
    stage_message: str = "Waiting in queue..."
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class Job(BaseModel):
    id: str
    batch_id: str
    topic: str
    preset_id: str
    preset_name: str
    status: JobState = JobState.QUEUED
    retry_count: int = 0
    max_retries: int = 3
    error_category: Optional[ErrorCategory] = None
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    output_directory: Optional[str] = None
    metrics: List[StageMetric] = Field(default_factory=list)

class Batch(BaseModel):
    id: str
    topic: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "IN_PROGRESS"
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    preset_quantities: Dict[str, int] = Field(default_factory=dict)
