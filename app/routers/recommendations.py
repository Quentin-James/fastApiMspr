"""Router FastAPI — endpoint de health check."""
import logging

from fastapi import APIRouter, status

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Transverse"])


@router.get(
    "/health",
    summary="Health check",
    description="Endpoint de vérification de l'état du service (utile pour le monitoring côté Spring).",
    status_code=status.HTTP_200_OK,
)
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "mspr-ia-microservice",
        "version": "1.0.0",
    }
