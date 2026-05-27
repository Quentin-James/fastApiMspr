from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UserProfileUpdate(BaseModel):
    objective: str | None = Field(default=None, description="Objectif santé utilisateur")
    diet_type: str | None = Field(default=None, description="Régime alimentaire")
    allergies: list[str] | None = Field(default=None, description="Allergies déclarées")
    excluded_foods: list[str] | None = Field(default=None, description="Aliments exclus")
    budget_weekly_eur: float | None = Field(default=None, ge=0)
    daily_calories_target: float | None = Field(default=None, ge=0)
    equipment: str | None = Field(default=None, description="Niveau d'équipement sportif")
    available_days: list[str] | None = Field(default=None, description="Jours disponibles")
    limitations: list[str] | None = Field(default=None, description="Limitations physiques")


class UserProfileDocument(BaseModel):
    id: str | None = None
    patient_id: str
    objective: str | None = None
    diet_type: str | None = None
    allergies: list[str] = Field(default_factory=list)
    excluded_foods: list[str] = Field(default_factory=list)
    budget_weekly_eur: float | None = None
    daily_calories_target: float | None = None
    equipment: str | None = None
    available_days: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserRecommendationsResponse(BaseModel):
    patient_id: str
    meal_plans: list[dict[str, Any]] = Field(default_factory=list)
    sport_programs: list[dict[str, Any]] = Field(default_factory=list)
