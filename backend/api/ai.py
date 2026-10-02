from fastapi import APIRouter
from backend.ai.registry import model_registry

router = APIRouter()

@router.get("/ai/models")
def get_ai_models():
    """YOLO HEALTH CHECK and other models."""
    models = model_registry.get_all()
    return {
        "models": [
            {
                "model_id": m.model_id,
                "name": m.name,
                "version": m.version,
                "task": m.task,
                "status": m.status
            } for m in models
        ]
    }
