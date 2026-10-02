import os
from celery import Celery
from backend.config import settings

# Initialize Celery app
# In production, use a durable broker like Redis or RabbitMQ
# For local dev fallback, we can use a local broker if available
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "sakshya_tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,  # Good for long running tasks like video processing
    task_acks_late=True,
)

@celery_app.task(bind=True, name="analyze_evidence_task")
def analyze_evidence_task(self, evidence_id: str, options: dict = None):
    """
    Celery background task for evidence analysis.
    This replaces FastAPI BackgroundTasks for production durability.
    """
    from backend.database import SessionLocal
    from backend.services.analysis import AnalysisService
    
    db = SessionLocal()
    try:
        service = AnalysisService(db)
        service.analyze(evidence_id, options or {})
    finally:
        db.close()
