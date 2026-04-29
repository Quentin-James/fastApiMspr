from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING
from app.config import settings
import logging

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_db() -> None:
    """Ouvre la connexion MongoDB et crée les index. Non bloquant si MongoDB est absent."""
    global _client, _db
    _client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=5000)
    _db = _client[settings.mongodb_db_name]

    try:
        await _db.recommendations.create_index(
            [("patientId", ASCENDING), ("created_at", ASCENDING)]
        )
        await _db.meal_plans.create_index(
            [("patientId", ASCENDING), ("created_at", ASCENDING)]
        )
        await _db.sport_programs.create_index(
            [("patientId", ASCENDING), ("created_at", ASCENDING)]
        )
        logger.info("Connexion MongoDB etablie : %s / %s", settings.mongodb_url, settings.mongodb_db_name)
    except Exception as exc:
        logger.warning("MongoDB non disponible (%s) — persistence desactivee, le service continue.", exc)


async def close_db() -> None:
    """Ferme la connexion MongoDB."""
    global _client
    if _client:
        _client.close()
        logger.info("🔌 Connexion MongoDB fermée.")


def get_db() -> AsyncIOMotorDatabase:
    """Retourne l'instance de la base de données courante."""
    if _db is None:
        raise RuntimeError("La base de données n'est pas initialisée. Appelez connect_db() d'abord.")
    return _db
