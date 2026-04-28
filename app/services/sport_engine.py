"""
Moteur de recommandations sportives.
Génère un programme sportif hebdomadaire adapté au profil utilisateur.
Inclut : multi-critères, progression adaptative, rotation des exercices.
"""
from typing import List, Dict, Any, Tuple
import logging
import random

from app.models.sport import (
    Exercise,
    FeedbackRequest,
    FitnessLevel,
    SportObjective,
    Equipment,
    SportRecommendation,
    UserSportProfile,
    WorkoutSession,
)
from app.services.nlp import generate_sport_message

logger = logging.getLogger(__name__)

# ─── Base d'exercices ─────────────────────────────────────────────────────────

EXERCISE_DB: Dict[str, Dict[str, Any]] = {
    # Renforcement - sans matériel
    "push_up": {"name": "Pompes", "sets": 3, "reps": "8-15", "rest_seconds": 60, "description": "Position planche, baisser le buste en fléchissant les coudes, remonter en tendant les bras.", "muscles_targeted": ["pectoraux", "triceps", "épaules"], "equipment": "none", "level": ["beginner", "intermediate", "advanced"], "objectives": ["muscle_gain", "general_health"], "contraindications": ["douleur épaule", "tunnel carpien"]},
    "squat": {"name": "Squat", "sets": 3, "reps": "12-15", "rest_seconds": 60, "description": "Pieds largeur épaules, descendre les fessiers jusqu'au niveau des genoux, remonter.", "muscles_targeted": ["quadriceps", "fessiers", "ischio-jambiers"], "equipment": "none", "level": ["beginner", "intermediate", "advanced"], "objectives": ["muscle_gain", "fat_loss", "general_health"], "contraindications": ["douleur genou", "hernie discale"]},
    "plank": {"name": "Planche isométrique", "sets": 3, "reps": "30s", "rest_seconds": 45, "description": "Position planche sur les avant-bras, maintenir le gainage en contractant abdominaux et fessiers.", "muscles_targeted": ["abdominaux", "dorsaux", "épaules"], "equipment": "none", "level": ["beginner", "intermediate", "advanced"], "objectives": ["general_health", "fat_loss"], "contraindications": ["hernie discale", "douleur lombaire"]},
    "lunge": {"name": "Fentes", "sets": 3, "reps": "10 par jambe", "rest_seconds": 60, "description": "Avancer une jambe, fléchir les deux genoux, revenir en position initiale. Alterner.", "muscles_targeted": ["quadriceps", "fessiers", "ischio-jambiers"], "equipment": "none", "level": ["beginner", "intermediate"], "objectives": ["muscle_gain", "fat_loss"], "contraindications": ["douleur genou"]},
    "burpee": {"name": "Burpee", "sets": 3, "reps": "10-15", "rest_seconds": 90, "description": "Position debout → pompe → saut vertical. Exercice cardio intense full body.", "muscles_targeted": ["full body", "cardio"], "equipment": "none", "level": ["intermediate", "advanced"], "objectives": ["fat_loss", "endurance"], "contraindications": ["douleur genou", "douleur épaule", "hernie discale"]},
    "mountain_climber": {"name": "Grimpeur de montagne", "sets": 3, "reps": "20 par côté", "rest_seconds": 45, "description": "Position planche, ramener alternativement les genoux vers la poitrine rapidement.", "muscles_targeted": ["abdominaux", "hip flexors", "cardio"], "equipment": "none", "level": ["intermediate", "advanced"], "objectives": ["fat_loss", "endurance"], "contraindications": ["hernie discale", "tunnel carpien"]},
    "glute_bridge": {"name": "Pont fessier", "sets": 3, "reps": "15-20", "rest_seconds": 45, "description": "Allongé sur le dos, pieds à plat, soulever le bassin en contractant les fessiers.", "muscles_targeted": ["fessiers", "ischio-jambiers", "lombaires"], "equipment": "none", "level": ["beginner", "intermediate"], "objectives": ["general_health", "fat_loss"], "contraindications": []},
    "tricep_dip": {"name": "Dips triceps (chaise)", "sets": 3, "reps": "10-15", "rest_seconds": 60, "description": "Mains posées sur une chaise derrière soi, fléchir les coudes pour descendre et remonter.", "muscles_targeted": ["triceps", "épaules"], "equipment": "home", "level": ["beginner", "intermediate"], "objectives": ["muscle_gain"], "contraindications": ["douleur épaule", "tunnel carpien"]},
    "jump_squat": {"name": "Squat sauté", "sets": 3, "reps": "12", "rest_seconds": 90, "description": "Squat classique avec saut explosif à la remontée.", "muscles_targeted": ["quadriceps", "fessiers", "cardio"], "equipment": "none", "level": ["intermediate", "advanced"], "objectives": ["fat_loss", "endurance"], "contraindications": ["douleur genou"]},
    "dead_bug": {"name": "Dead Bug", "sets": 3, "reps": "8 par côté", "rest_seconds": 45, "description": "Allongé sur le dos, bras tendus vers le plafond, étendre bras et jambe opposés simultanément.", "muscles_targeted": ["abdominaux profonds", "stabilisateurs"], "equipment": "none", "level": ["beginner", "intermediate"], "objectives": ["general_health"], "contraindications": ["hernie discale"]},
    # Cardio
    "jogging": {"name": "Jogging", "sets": 1, "reps": None, "duration_minutes": 30, "rest_seconds": 0, "description": "Course légère à allure modérée, conversation possible.", "muscles_targeted": ["cardio", "jambes"], "equipment": "none", "level": ["beginner", "intermediate", "advanced"], "objectives": ["fat_loss", "endurance", "general_health"], "contraindications": ["douleur genou", "douleur cheville"]},
    "hiit_run": {"name": "Fractionné HIIT", "sets": 8, "reps": "30s sprint / 30s marche", "rest_seconds": 0, "description": "Alterner sprint intense et marche active pendant 8 cycles.", "muscles_targeted": ["cardio", "jambes"], "equipment": "none", "level": ["intermediate", "advanced"], "objectives": ["fat_loss", "endurance"], "contraindications": ["douleur genou", "douleur cheville", "problème cardiaque"]},
    "jump_rope": {"name": "Corde à sauter", "sets": 5, "reps": "2 minutes", "rest_seconds": 60, "description": "Sauts à la corde à rythme régulier.", "muscles_targeted": ["cardio", "mollets", "épaules"], "equipment": "home", "level": ["intermediate", "advanced"], "objectives": ["fat_loss", "endurance"], "contraindications": ["douleur genou", "douleur cheville"]},
    # Salle
    "bench_press": {"name": "Développé couché", "sets": 4, "reps": "8-10", "rest_seconds": 90, "description": "Allongé sur banc, barre à la largeur des épaules, descendre jusqu'à la poitrine et repousser.", "muscles_targeted": ["pectoraux", "triceps", "épaules"], "equipment": "gym", "level": ["intermediate", "advanced"], "objectives": ["muscle_gain"], "contraindications": ["douleur épaule"]},
    "deadlift": {"name": "Soulevé de terre", "sets": 4, "reps": "6-8", "rest_seconds": 120, "description": "Soulever la barre depuis le sol en maintenant le dos droit, en poussant avec les jambes.", "muscles_targeted": ["ischio-jambiers", "fessiers", "dorsaux", "lombaires"], "equipment": "gym", "level": ["intermediate", "advanced"], "objectives": ["muscle_gain"], "contraindications": ["hernie discale", "douleur lombaire"]},
    "pull_up": {"name": "Traction", "sets": 3, "reps": "5-10", "rest_seconds": 90, "description": "Suspendu à la barre, tirer le buste vers le haut jusqu'à ce que le menton dépasse la barre.", "muscles_targeted": ["dorsaux", "biceps", "épaules"], "equipment": "gym", "level": ["intermediate", "advanced"], "objectives": ["muscle_gain"], "contraindications": ["douleur épaule", "épicondylite"]},
    "leg_press": {"name": "Presse à cuisses", "sets": 4, "reps": "10-12", "rest_seconds": 90, "description": "Assis dans la machine, pousser la plateforme avec les pieds sans verrouiller les genoux.", "muscles_targeted": ["quadriceps", "fessiers"], "equipment": "gym", "level": ["beginner", "intermediate", "advanced"], "objectives": ["muscle_gain", "fat_loss"], "contraindications": []},
    "cable_row": {"name": "Tirage poulie assis", "sets": 3, "reps": "12", "rest_seconds": 75, "description": "Assis face à la poulie basse, tirer la barre vers l'abdomen en contractant les dorsaux.", "muscles_targeted": ["dorsaux", "biceps", "trapèzes"], "equipment": "gym", "level": ["beginner", "intermediate", "advanced"], "objectives": ["muscle_gain"], "contraindications": ["hernie discale"]},
    # Récupération
    "yoga_stretch": {"name": "Yoga / étirements", "sets": 1, "reps": None, "duration_minutes": 20, "rest_seconds": 0, "description": "Série d'étirements dynamiques et statiques pour favoriser la récupération musculaire.", "muscles_targeted": ["full body"], "equipment": "none", "level": ["beginner", "intermediate", "advanced"], "objectives": ["general_health", "fat_loss", "endurance", "muscle_gain"], "contraindications": []},
    "foam_rolling": {"name": "Foam Rolling", "sets": 1, "reps": None, "duration_minutes": 15, "rest_seconds": 0, "description": "Auto-massage avec rouleau mousse pour relâcher les tensions musculaires.", "muscles_targeted": ["full body"], "equipment": "home", "level": ["beginner", "intermediate", "advanced"], "objectives": ["general_health", "muscle_gain"], "contraindications": []},
    "walking": {"name": "Marche active", "sets": 1, "reps": None, "duration_minutes": 40, "rest_seconds": 0, "description": "Marche à allure soutenue (5-6 km/h), idéale pour la récupération active.", "muscles_targeted": ["cardio léger", "jambes"], "equipment": "none", "level": ["beginner", "intermediate", "advanced"], "objectives": ["general_health", "fat_loss"], "contraindications": ["douleur cheville sévère"]},
}


def _filter_exercises(
    objective: SportObjective,
    level: FitnessLevel,
    equipment: Equipment,
    limitations: List[str],
) -> List[Dict[str, Any]]:
    """Filtre les exercices selon les critères du profil."""
    filtered = []
    limitations_lower = [l.lower() for l in limitations]

    for key, ex in EXERCISE_DB.items():
        # Vérifier l'équipement
        if equipment == Equipment.none and ex["equipment"] not in ["none"]:
            continue
        if equipment == Equipment.home and ex["equipment"] not in ["none", "home"]:
            continue
        # Gym autorise tout

        # Vérifier le niveau
        if level.value not in ex["level"]:
            continue

        # Vérifier l'objectif
        if objective.value not in ex["objectives"]:
            continue

        # Vérifier les contre-indications
        excluded = False
        for contra in ex["contraindications"]:
            if any(lim in contra.lower() or contra.lower() in lim for lim in limitations_lower):
                excluded = True
                break
        if excluded:
            continue

        filtered.append({**ex, "key": key})

    return filtered


def _build_session(
    session_type: str,
    day: str,
    available_exercises: List[Dict[str, Any]],
    duration_max: int,
    week_index: int = 0,
) -> WorkoutSession:
    """Construit une séance à partir des exercices disponibles."""
    # Rotation des exercices selon la semaine pour éviter la répétition exacte
    rotated = available_exercises[week_index % len(available_exercises):] + available_exercises[:week_index % len(available_exercises)]

    selected: List[Exercise] = []
    total_duration = 0

    for ex_data in rotated:
        if total_duration >= duration_max:
            break
        ex_duration = ex_data.get("duration_minutes") or (
            (ex_data.get("sets", 1) * (
                int(str(ex_data.get("reps", "10")).split("-")[0].replace("s", "").replace(" par", "").split()[0] or "1") * 3 + ex_data.get("rest_seconds", 60)
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
        notes=f"Semaine de départ — progressez 5 % chaque semaine.",
    )


def _compute_progression_notes(
    level: FitnessLevel, objective: SportObjective, feedbacks: List[FeedbackRequest] = []
) -> str:
    """Calcule les notes de progression adaptative."""
    base = {
        FitnessLevel.beginner: "Commencez avec des charges légères. Maîtrisez la technique avant d'augmenter l'intensité.",
        FitnessLevel.intermediate: "Augmentez la charge de 2,5-5 % dès que vous réussissez la fourchette de répétitions haute sur 2 séances.",
        FitnessLevel.advanced: "Variez les techniques (drop-sets, super-sets) et ciblez une surcharge progressive de 1-3 % par semaine.",
    }
    note = base[level]

    if feedbacks:
        avg_rating = sum(f.rating for f in feedbacks) / len(feedbacks)
        if avg_rating >= 4 and any(f.too_easy for f in feedbacks):
            note += " | 📈 Retours positifs : augmentez l'intensité dès la prochaine séance."
        elif avg_rating <= 2 and any(f.too_hard for f in feedbacks):
            note += " | 📉 Programme trop difficile : réduisez la charge de 10-15 % et progressez plus graduellement."

    return note


async def build_weekly_sport_program(
    profile: UserSportProfile,
    previous_feedbacks: List[FeedbackRequest] = [],
) -> SportRecommendation:
    """Génère un programme sportif hebdomadaire complet."""
    available_exercises = _filter_exercises(
        profile.objective,
        profile.fitness_level,
        profile.equipment,
        profile.limitations,
    )

    # Ajouter yoga/récupération comme fallback toujours disponible
    recovery_exercises = [
        {**EXERCISE_DB["yoga_stretch"], "key": "yoga_stretch"},
        {**EXERCISE_DB["walking"], "key": "walking"},
    ]

    weekly_sessions: List[WorkoutSession] = []
    all_days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

    session_types = {
        SportObjective.fat_loss: ["HIIT / Cardio", "Renforcement", "Cardio léger", "HIIT / Cardio", "Renforcement"],
        SportObjective.muscle_gain: ["Renforcement", "Renforcement", "Récupération active", "Renforcement", "Renforcement"],
        SportObjective.endurance: ["Cardio", "Cardio", "Récupération", "Cardio long", "Cardio"],
        SportObjective.general_health: ["Renforcement", "Cardio", "Récupération", "Renforcement", "Cardio"],
        SportObjective.flexibility: ["Stretching", "Renforcement léger", "Yoga", "Stretching", "Renforcement léger"],
    }

    type_cycle = session_types.get(profile.objective, session_types[SportObjective.general_health])
    available_days = profile.available_days

    for i, day_name in enumerate(all_days):
        day_lower = day_name.lower()
        if not any(avail.lower()[:3] in day_lower[:3] for avail in available_days):
            # Jour de repos
            weekly_sessions.append(WorkoutSession(
                day=day_name,
                session_type="Repos",
                duration_minutes=0,
                exercises=[],
                notes="Jour de repos. Hydratez-vous et dormez suffisamment.",
            ))
            continue

        # Compter les séances prévues jusqu'ici
        session_idx = sum(1 for s in weekly_sessions if s.session_type != "Repos")
        session_type = type_cycle[session_idx % len(type_cycle)]

        if "Récupération" in session_type or "Yoga" in session_type or "Stretching" in session_type:
            exs = recovery_exercises if not available_exercises else (recovery_exercises + available_exercises[:3])
        else:
            exs = available_exercises if available_exercises else recovery_exercises

        if not exs:
            exs = recovery_exercises

        session = _build_session(
            session_type=session_type,
            day=day_name,
            available_exercises=exs,
            duration_max=profile.session_duration_max_minutes,
            week_index=i,
        )
        weekly_sessions.append(session)

    progression_notes = _compute_progression_notes(
        profile.fitness_level, profile.objective, previous_feedbacks
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
