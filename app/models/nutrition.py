from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class DietType(str, Enum):
    omnivore = "omnivore"
    vegetarian = "vegetarian"
    vegan = "vegan"
    keto = "keto"
    gluten_free = "gluten_free"
    lactose_free = "lactose_free"


class FoodItem(BaseModel):
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    calories_per_100g: Optional[float] = None
    proteins_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fats_g: Optional[float] = None
    quantity_g: Optional[float] = None

    @property
    def total_calories(self) -> Optional[float]:
        if self.calories_per_100g is not None and self.quantity_g is not None:
            return round(self.calories_per_100g * self.quantity_g / 100, 2)
        return None


class Macros(BaseModel):
    calories: float
    proteins_g: float
    carbs_g: float
    fats_g: float
    fiber_g: Optional[float] = None


class PhotoAnalysisResponse(BaseModel):
    foods_detected: List[FoodItem]
    total_macros: Macros
    analysis_api: str
    confidence_avg: float


class UserNutritionProfile(BaseModel):
    patient_id: str
    objective: str = Field(description="ex: perte_de_poids, prise_de_masse, maintenance")
    allergies: List[str] = Field(default_factory=list)
    budget_weekly_eur: Optional[float] = None
    diet_type: DietType = DietType.omnivore
    daily_calories_target: Optional[float] = None
    excluded_foods: List[str] = Field(default_factory=list)
    clerk_user_id: Optional[str] = Field(
        default=None,
        description="ID Clerk (user_xxx) - enrichit depuis Java et push le resultat",
    )


class Meal(BaseModel):
    name: str
    meal_type: str
    foods: List[str]
    macros: Macros
    recipe_hint: Optional[str] = None


class DayPlan(BaseModel):
    day: str
    meals: List[Meal]
    total_macros: Macros


class NutritionRecommendation(BaseModel):
    patient_id: str
    weekly_plan: List[DayPlan]
    nutritional_balance_notes: str
    personalized_message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    api_used: str = "huggingface"
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.85)
