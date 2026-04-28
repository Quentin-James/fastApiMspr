from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional, Any, Dict
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

    async def get_recommendations_by_patient(
        self, patient_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        cursor = (
            self.recommendations.find({"patientId": patient_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        # Sérialiser l'ObjectId en string
        for doc in docs:
            doc["_id"] = str(doc["_id"])
        return docs

    # ─── Plans nutritionnels ──────────────────────────────────────────────────

    async def save_meal_plan(self, data: Dict[str, Any]) -> str:
        data["created_at"] = data.get("created_at", datetime.utcnow())
        result = await self.meal_plans.insert_one(data)
        return str(result.inserted_id)

    async def get_meal_plans_by_patient(
        self, patient_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        cursor = (
            self.meal_plans.find({"patientId": patient_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        for doc in docs:
            doc["_id"] = str(doc["_id"])
        return docs

    # ─── Programmes sportifs ──────────────────────────────────────────────────

    async def save_sport_program(self, data: Dict[str, Any]) -> str:
        data["created_at"] = data.get("created_at", datetime.utcnow())
        result = await self.sport_programs.insert_one(data)
        return str(result.inserted_id)

    async def get_sport_program_by_id(self, program_id: str) -> Optional[Dict[str, Any]]:
        from bson import ObjectId
        try:
            oid = ObjectId(program_id)
        except Exception:
            return None
        doc = await self.sport_programs.find_one({"_id": oid})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def update_sport_program_feedback(
        self, program_id: str, feedback: Dict[str, Any]
    ) -> bool:
        from bson import ObjectId
        try:
            oid = ObjectId(program_id)
        except Exception:
            return False
        result = await self.sport_programs.update_one(
            {"_id": oid},
            {"$push": {"feedbacks": {**feedback, "submitted_at": datetime.utcnow()}}},
        )
        return result.modified_count > 0
