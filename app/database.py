from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING
from app.config import settings
import logging

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_db() -> None:
    """Ouvre la connexion MongoDB et crée les index."""
    global _client, _db
    _client = AsyncIOMotorClient(settings.mongodb_url)
    _db = _client[settings.mongodb_db_name]

    # Index sur recommendations
    await _db.recommendations.create_index(
        [("patientId", ASCENDING), ("created_at", ASCENDING)]
    )
    # Index sur meal_plans
    await _db.meal_plans.create_index(
        [("patientId", ASCENDING), ("created_at", ASCENDING)]
    )
    # Index sur sport_programs
    await _db.sport_programs.create_index(
        [("patientId", ASCENDING), ("created_at", ASCENDING)]
    )

    logger.info("✅ Connexion MongoDB établie : %s / %s", settings.mongodb_url, settings.mongodb_db_name)


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
