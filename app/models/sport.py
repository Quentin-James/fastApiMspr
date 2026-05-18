from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class FitnessLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class SportObjective(str, Enum):
    fat_loss = "fat_loss"
    muscle_gain = "muscle_gain"
    endurance = "endurance"
    general_health = "general_health"
    flexibility = "flexibility"


class Equipment(str, Enum):
    none = "none"
    home = "home"
    gym = "gym"


class Exercise(BaseModel):
    name: str
    sets: Optional[int] = None
    reps: Optional[str] = None  # "8-12" ou "30s"
    duration_minutes: Optional[int] = None
    rest_seconds: int = 60
    description: str
    muscles_targeted: List[str]
    contraindications: List[str] = Field(default_factory=list)


class WorkoutSession(BaseModel):
    day: str
    session_type: str  # strength, cardio, HIIT, recovery, rest
    duration_minutes: int
    exercises: List[Exercise]
    notes: Optional[str] = None


class UserSportProfile(BaseModel):
    patient_id: str
    objective: SportObjective
    fitness_level: FitnessLevel
    equipment: Equipment
    available_days: List[str] = Field(
        description="ex: ['lundi', 'mercredi', 'vendredi']"
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="ex: ['douleur genou droit', 'hernie discale']",
    )
    session_duration_max_minutes: int = 60
    # Identifiant Clerk : si fourni, FastAPI enrichit le profil depuis Java
    # et pousse le résultat vers Java après génération.
    clerk_user_id: Optional[str] = Field(
        default=None,
        description="ID Clerk de l'utilisateur (user_xxx) pour l'intégration Java",
    )


class SportRecommendation(BaseModel):
    patient_id: str
    weekly_program: List[WorkoutSession]
    progression_notes: str
    personalized_message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    api_used: str = "internal_engine"
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.90)


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5, description="Note de 1 à 5")
    comment: Optional[str] = None
    too_hard: bool = False
    too_easy: bool = False
    exercises_skipped: List[str] = Field(default_factory=list)
