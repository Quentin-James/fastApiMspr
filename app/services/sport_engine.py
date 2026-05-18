"""
Moteur de recommandations sportives.

Responsabilité : générer un programme hebdomadaire adapté au profil utilisateur.
Les données (catalogue d'exercices) sont dans app/data/exercise_db.py.
"""
import logging
from typing import List, Dict, Any

from app.data.exercise_db import EXERCISE_DB, RECOVERY_EXERCISE_KEYS
from app.models.sport import (
    Equipment,
    Exercise,
    FeedbackRequest,
    FitnessLevel,
    SportObjective,
    SportRecommendation,
    UserSportProfile,
    WorkoutSession,
)
from app.services.nlp import generate_sport_message, interpret_physical_limitations

logger = logging.getLogger(__name__)

# Type de séance par objectif (5 types pour les 5 jours actifs max)
SESSION_TYPES: dict[SportObjective, list[str]] = {
    SportObjective.fat_loss:      ["HIIT / Cardio", "Renforcement", "Cardio léger", "HIIT / Cardio", "Renforcement"],
    SportObjective.muscle_gain:   ["Renforcement", "Renforcement", "Récupération active", "Renforcement", "Renforcement"],
    SportObjective.endurance:     ["Cardio", "Cardio", "Récupération", "Cardio long", "Cardio"],
    SportObjective.general_health:["Renforcement", "Cardio", "Récupération", "Renforcement", "Cardio"],
    SportObjective.flexibility:   ["Stretching", "Renforcement léger", "Yoga", "Stretching", "Renforcement léger"],
}

ALL_DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


# ─── Filtrage ─────────────────────────────────────────────────────────────────

def _filter_exercises(
    objective: SportObjective,
    level: FitnessLevel,
    equipment: Equipment,
    limitations: List[str],
    excluded_keywords: List[str] = [],
) -> List[Dict[str, Any]]:
    """
    Filtre le catalogue selon équipement, niveau, objectif et limitations physiques.

    Couche 1 — contraindications hardcodées (substring bidirectionnel avec les limitations).
    Couche 2 — mots-clés sémantiques issus du LLM (muscles, noms, descriptions).
    """
    limitations_lower = [l.lower() for l in limitations]
    filtered = []

    for key, ex in EXERCISE_DB.items():
        # Équipement
        if equipment == Equipment.none and ex["equipment"] != "none":
            continue
        if equipment == Equipment.home and ex["equipment"] == "gym":
            continue

        # Niveau
        if level.value not in ex["level"]:
            continue

        # Objectif
        if objective.value not in ex["objectives"]:
            continue

        # Couche 1 : contra-indications hardcodées
        if any(
            lim in contra.lower() or contra.lower() in lim
            for contra in ex["contraindications"]
            for lim in limitations_lower
        ):
            continue

        # Couche 2 : mots-clés sémantiques LLM
        if excluded_keywords:
            searchable = (
                " ".join(ex["muscles_targeted"]).lower()
                + " " + ex.get("name", "").lower()
                + " " + ex.get("description", "").lower()
            )
            if any(kw in searchable for kw in excluded_keywords):
                continue

        filtered.append({**ex, "key": key})

    return filtered


# ─── Construction d'une séance ────────────────────────────────────────────────

def _build_session(
    session_type: str,
    day: str,
    exercises: List[Dict[str, Any]],
    duration_max: int,
    week_index: int = 0,
) -> WorkoutSession:
    """Sélectionne et ordonne les exercices pour une séance dans la limite de durée."""
    # Rotation pour éviter la répétition exacte d'une semaine à l'autre
    rotated = exercises[week_index % len(exercises):] + exercises[:week_index % len(exercises)]

    selected: List[Exercise] = []
    total_duration = 0

    for ex_data in rotated:
        if total_duration >= duration_max:
            break

        ex_duration = ex_data.get("duration_minutes") or (
            (ex_data.get("sets", 1) * (
                int(str(ex_data.get("reps", "10")).split("-")[0]
                    .replace("s", "").replace(" par", "").split()[0] or "1") * 3
                + ex_data.get("rest_seconds", 60)
            )) // 60 + 3
        )
        total_duration += ex_duration

        selected.append(Exercise(
            name=ex_data["name"],
            sets=ex_data.get("sets"),
            reps=str(ex_data["reps"]) if ex_data.get("reps") else None,
            duration_minutes=ex_data.get("duration_minutes"),
            rest_seconds=ex_data.get("rest_seconds", 60),
            description=ex_data["description"],
            muscles_targeted=ex_data["muscles_targeted"],
            contraindications=ex_data.get("contraindications", []),
        ))

    return WorkoutSession(
        day=day,
        session_type=session_type,
        duration_minutes=min(total_duration, duration_max),
        exercises=selected,
        notes="Semaine de départ — progressez 5 % chaque semaine.",
    )


# ─── Progression adaptative ───────────────────────────────────────────────────

def _compute_progression_notes(
    level: FitnessLevel,
    objective: SportObjective,
    feedbacks: List[FeedbackRequest] = [],
) -> str:
    """Génère les conseils de progression, adaptés aux retours utilisateur."""
    base = {
        FitnessLevel.beginner:     "Commencez avec des charges légères. Maîtrisez la technique avant d'augmenter l'intensité.",
        FitnessLevel.intermediate: "Augmentez la charge de 2,5-5 % dès que vous réussissez la fourchette haute sur 2 séances.",
        FitnessLevel.advanced:     "Variez les techniques (drop-sets, super-sets) et ciblez une surcharge de 1-3 % par semaine.",
    }
    note = base[level]

    if feedbacks:
        avg_rating = sum(f.rating for f in feedbacks) / len(feedbacks)
        if avg_rating >= 4 and any(f.too_easy for f in feedbacks):
            note += " | 📈 Retours positifs : augmentez l'intensité dès la prochaine séance."
        elif avg_rating <= 2 and any(f.too_hard for f in feedbacks):
            note += " | 📉 Programme trop difficile : réduisez la charge de 10-15 % et progressez plus graduellement."

    return note


# ─── Point d'entrée public ────────────────────────────────────────────────────

async def build_weekly_sport_program(
    profile: UserSportProfile,
    previous_feedbacks: List[FeedbackRequest] = [],
) -> SportRecommendation:
    """Génère un programme sportif hebdomadaire complet à partir du profil patient."""
    excluded_keywords = await interpret_physical_limitations(profile.limitations)

    available_exercises = _filter_exercises(
        profile.objective,
        profile.fitness_level,
        profile.equipment,
        profile.limitations,
        excluded_keywords=excluded_keywords,
    )

    # Exercices de récupération filtrés par les mots-clés sémantiques
    recovery_pool = [{**EXERCISE_DB[k], "key": k} for k in RECOVERY_EXERCISE_KEYS]
    recovery_exercises = [
        ex for ex in recovery_pool
        if not excluded_keywords or not any(
            kw in (
                " ".join(ex["muscles_targeted"]).lower()
                + " " + ex.get("name", "").lower()
                + " " + ex.get("description", "").lower()
            )
            for kw in excluded_keywords
        )
    ] or recovery_pool[:1]  # au minimum le yoga si tout est filtré

    type_cycle    = SESSION_TYPES.get(profile.objective, SESSION_TYPES[SportObjective.general_health])
    available_days = profile.available_days
    weekly_sessions: List[WorkoutSession] = []

    for i, day_name in enumerate(ALL_DAYS):
        day_lower = day_name.lower()

        if not any(avail.lower()[:3] in day_lower[:3] for avail in available_days):
            weekly_sessions.append(WorkoutSession(
                day=day_name,
                session_type="Repos",
                duration_minutes=0,
                exercises=[],
                notes="Jour de repos. Hydratez-vous et dormez suffisamment.",
            ))
            continue

        session_idx  = sum(1 for s in weekly_sessions if s.session_type != "Repos")
        session_type = type_cycle[session_idx % len(type_cycle)]
        is_recovery  = any(t in session_type for t in ("Récupération", "Yoga", "Stretching"))

        exs = (recovery_exercises + available_exercises[:3]) if is_recovery else (available_exercises or recovery_exercises)

        weekly_sessions.append(_build_session(
            session_type=session_type,
            day=day_name,
            exercises=exs or recovery_exercises,
            duration_max=profile.session_duration_max_minutes,
            week_index=i,
        ))

    progression_notes = _compute_progression_notes(profile.fitness_level, profile.objective, previous_feedbacks)

    if profile.limitations:
        lim_str = ", ".join(profile.limitations)
        kw_str  = ", ".join(excluded_keywords[:8]) if excluded_keywords else None
        progression_notes += (
            f" | Limitations prises en compte : {lim_str}"
            + (f" (zones exclues : {kw_str})." if kw_str else ".")
        )

    personalized_message = await generate_sport_message(
        profile.objective.value,
        profile.fitness_level.value,
        progression_notes,
    )

    return SportRecommendation(
        patient_id=profile.patient_id,
        weekly_program=weekly_sessions,
        progression_notes=progression_notes,
        personalized_message=personalized_message,
        api_used="sport_engine",
        confidence_score=0.90,
    )
