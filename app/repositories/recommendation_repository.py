from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Any, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RecommendationRepository:
    """Accès MongoDB pour les recommandations (nutrition + sport)."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.recommendations = db.recommendations
        self.meal_plans = db.meal_plans
        self.sport_programs = db.sport_programs

    # ─── Recommandations génériques ───────────────────────────────────────────

    async def save_recommendation(self, data: Dict[str, Any]) -> str:
        data["created_at"] = data.get("created_at", datetime.utcnow())
        result = await self.recommendations.insert_one(data)
        logger.info("Recommandation sauvegardée : %s", result.inserted_id)
        return str(result.inserted_id)

    # ─── Plans nutritionnels ──────────────────────────────────────────────────

    async def save_meal_plan(self, data: Dict[str, Any]) -> str:
        data["created_at"] = data.get("created_at", datetime.utcnow())
        result = await self.meal_plans.insert_one(data)
        return str(result.inserted_id)

    # ─── Programmes sportifs ──────────────────────────────────────────────────

    async def save_sport_program(self, data: Dict[str, Any]) -> str:
        data["created_at"] = data.get("created_at", datetime.utcnow())
        result = await self.sport_programs.insert_one(data)
        return str(result.inserted_id)

