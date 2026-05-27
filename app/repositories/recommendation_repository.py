from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Any, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RecommendationRepository:
    """Accès MongoDB pour les recommandations (nutrition + sport)."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.recommendations = db.recommendations
        self.meal_plans = db.meal_plans
        self.sport_programs = db.sport_programs
        self.user_profiles = db.user_profiles

    @staticmethod
    def _serialize(doc: Dict[str, Any] | None) -> Dict[str, Any] | None:
        if doc is None:
            return None

        out = dict(doc)
        if "_id" in out:
            out["id"] = str(out.pop("_id"))
        if "patientId" in out:
            out["patient_id"] = out.pop("patientId")
        return out

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

    async def list_meal_plans(self, patient_id: str, limit: int = 20) -> list[Dict[str, Any]]:
        cursor = (
            self.meal_plans
            .find({"patientId": patient_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        docs = [self._serialize(doc) async for doc in cursor]
        return [d for d in docs if d is not None]

    async def list_sport_programs(self, patient_id: str, limit: int = 20) -> list[Dict[str, Any]]:
        cursor = (
            self.sport_programs
            .find({"patientId": patient_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        docs = [self._serialize(doc) async for doc in cursor]
        return [d for d in docs if d is not None]

    async def upsert_user_profile(self, patient_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.utcnow()
        payload = {**data, "patientId": patient_id, "updated_at": now}

        await self.user_profiles.update_one(
            {"patientId": patient_id},
            {
                "$set": payload,
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )

        saved = await self.user_profiles.find_one({"patientId": patient_id})
        return self._serialize(saved) or {"patient_id": patient_id}

    async def get_user_profile(self, patient_id: str) -> Dict[str, Any] | None:
        doc = await self.user_profiles.find_one({"patientId": patient_id})
        return self._serialize(doc)

