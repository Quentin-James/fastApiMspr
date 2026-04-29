"""
Base de données des exercices sportifs avec leurs métadonnées.

Responsabilité unique : définir le catalogue d'exercices.
Étendre ce fichier pour ajouter des exercices sans toucher au moteur sportif.

Structure de chaque exercice :
  name            : nom affiché
  sets            : nombre de séries
  reps            : répétitions (str) ou None si durée fixe
  duration_minutes: durée fixe (cardio, yoga) ou None
  rest_seconds    : repos entre séries
  description     : consigne d'exécution
  muscles_targeted: groupes musculaires sollicités
  equipment       : "none" | "home" | "gym"
  level           : ["beginner"] | ["intermediate"] | ["beginner", "intermediate", "advanced"] …
  objectives      : sous-ensemble de fat_loss / muscle_gain / endurance / general_health / flexibility
  contraindications: termes médicaux exclus si présents dans les limitations du patient
"""
from typing import Any

ExerciseData = dict[str, Any]

EXERCISE_DB: dict[str, ExerciseData] = {
    # ── Renforcement sans matériel ────────────────────────────────────────────
    "push_up": {
        "name": "Pompes",
        "sets": 3, "reps": "8-15", "duration_minutes": None, "rest_seconds": 60,
        "description": "Position planche, baisser le buste en fléchissant les coudes, remonter.",
        "muscles_targeted": ["pectoraux", "triceps", "épaules"],
        "equipment": "none",
        "level": ["beginner", "intermediate", "advanced"],
        "objectives": ["muscle_gain", "general_health"],
        "contraindications": ["douleur épaule", "tunnel carpien"],
    },
    "squat": {
        "name": "Squat",
        "sets": 3, "reps": "12-15", "duration_minutes": None, "rest_seconds": 60,
        "description": "Pieds largeur épaules, descendre les fessiers au niveau des genoux, remonter.",
        "muscles_targeted": ["quadriceps", "fessiers", "ischio-jambiers"],
        "equipment": "none",
        "level": ["beginner", "intermediate", "advanced"],
        "objectives": ["muscle_gain", "fat_loss", "general_health"],
        "contraindications": ["douleur genou", "hernie discale"],
    },
    "plank": {
        "name": "Planche isométrique",
        "sets": 3, "reps": "30s", "duration_minutes": None, "rest_seconds": 45,
        "description": "Position planche avant-bras, maintenir le gainage en contractant abdos et fessiers.",
        "muscles_targeted": ["abdominaux", "dorsaux", "épaules"],
        "equipment": "none",
        "level": ["beginner", "intermediate", "advanced"],
        "objectives": ["general_health", "fat_loss"],
        "contraindications": ["hernie discale", "douleur lombaire"],
    },
    "lunge": {
        "name": "Fentes",
        "sets": 3, "reps": "10 par jambe", "duration_minutes": None, "rest_seconds": 60,
        "description": "Avancer une jambe, fléchir les deux genoux, revenir. Alterner.",
        "muscles_targeted": ["quadriceps", "fessiers", "ischio-jambiers"],
        "equipment": "none",
        "level": ["beginner", "intermediate"],
        "objectives": ["muscle_gain", "fat_loss"],
        "contraindications": ["douleur genou"],
    },
    "burpee": {
        "name": "Burpee",
        "sets": 3, "reps": "10-15", "duration_minutes": None, "rest_seconds": 90,
        "description": "Debout → pompe → saut vertical. Cardio intense full body.",
        "muscles_targeted": ["full body", "cardio"],
        "equipment": "none",
        "level": ["intermediate", "advanced"],
        "objectives": ["fat_loss", "endurance"],
        "contraindications": ["douleur genou", "douleur épaule", "hernie discale"],
    },
    "mountain_climber": {
        "name": "Grimpeur de montagne",
        "sets": 3, "reps": "20 par côté", "duration_minutes": None, "rest_seconds": 45,
        "description": "Position planche, ramener alternativement les genoux vers la poitrine.",
        "muscles_targeted": ["abdominaux", "hip flexors", "cardio"],
        "equipment": "none",
        "level": ["intermediate", "advanced"],
        "objectives": ["fat_loss", "endurance"],
        "contraindications": ["hernie discale", "tunnel carpien"],
    },
    "glute_bridge": {
        "name": "Pont fessier",
        "sets": 3, "reps": "15-20", "duration_minutes": None, "rest_seconds": 45,
        "description": "Allongé sur le dos, pieds à plat, soulever le bassin en contractant les fessiers.",
        "muscles_targeted": ["fessiers", "ischio-jambiers", "lombaires"],
        "equipment": "none",
        "level": ["beginner", "intermediate"],
        "objectives": ["general_health", "fat_loss"],
        "contraindications": [],
    },
    "dead_bug": {
        "name": "Dead Bug",
        "sets": 3, "reps": "8 par côté", "duration_minutes": None, "rest_seconds": 45,
        "description": "Allongé sur le dos, bras tendus, étendre bras et jambe opposés simultanément.",
        "muscles_targeted": ["abdominaux profonds", "stabilisateurs"],
        "equipment": "none",
        "level": ["beginner", "intermediate"],
        "objectives": ["general_health"],
        "contraindications": ["hernie discale"],
    },
    # ── Renforcement avec matériel maison ────────────────────────────────────
    "tricep_dip": {
        "name": "Dips triceps (chaise)",
        "sets": 3, "reps": "10-15", "duration_minutes": None, "rest_seconds": 60,
        "description": "Mains sur une chaise derrière soi, fléchir les coudes pour descendre.",
        "muscles_targeted": ["triceps", "épaules"],
        "equipment": "home",
        "level": ["beginner", "intermediate"],
        "objectives": ["muscle_gain"],
        "contraindications": ["douleur épaule", "tunnel carpien"],
    },
    # ── Cardio ───────────────────────────────────────────────────────────────
    "jogging": {
        "name": "Jogging",
        "sets": 1, "reps": None, "duration_minutes": 30, "rest_seconds": 0,
        "description": "Course légère à allure modérée, conversation possible.",
        "muscles_targeted": ["cardio", "jambes"],
        "equipment": "none",
        "level": ["beginner", "intermediate", "advanced"],
        "objectives": ["fat_loss", "endurance", "general_health"],
        "contraindications": ["douleur genou", "douleur cheville"],
    },
    "hiit_run": {
        "name": "Fractionné HIIT",
        "sets": 8, "reps": "30s sprint / 30s marche", "duration_minutes": None, "rest_seconds": 0,
        "description": "Alterner sprint intense et marche active pendant 8 cycles.",
        "muscles_targeted": ["cardio", "jambes"],
        "equipment": "none",
        "level": ["intermediate", "advanced"],
        "objectives": ["fat_loss", "endurance"],
        "contraindications": ["douleur genou", "douleur cheville", "problème cardiaque"],
    },
    "jump_squat": {
        "name": "Squat sauté",
        "sets": 3, "reps": "12", "duration_minutes": None, "rest_seconds": 90,
        "description": "Squat classique avec saut explosif à la remontée.",
        "muscles_targeted": ["quadriceps", "fessiers", "cardio"],
        "equipment": "none",
        "level": ["intermediate", "advanced"],
        "objectives": ["fat_loss", "endurance"],
        "contraindications": ["douleur genou"],
    },
    "jump_rope": {
        "name": "Corde à sauter",
        "sets": 5, "reps": "2 minutes", "duration_minutes": None, "rest_seconds": 60,
        "description": "Sauts à la corde à rythme régulier.",
        "muscles_targeted": ["cardio", "mollets", "épaules"],
        "equipment": "home",
        "level": ["intermediate", "advanced"],
        "objectives": ["fat_loss", "endurance"],
        "contraindications": ["douleur genou", "douleur cheville"],
    },
    # ── Salle ────────────────────────────────────────────────────────────────
    "bench_press": {
        "name": "Développé couché",
        "sets": 4, "reps": "8-10", "duration_minutes": None, "rest_seconds": 90,
        "description": "Allongé sur banc, barre à largeur d'épaules, descendre à la poitrine.",
        "muscles_targeted": ["pectoraux", "triceps", "épaules"],
        "equipment": "gym",
        "level": ["intermediate", "advanced"],
        "objectives": ["muscle_gain"],
        "contraindications": ["douleur épaule"],
    },
    "deadlift": {
        "name": "Soulevé de terre",
        "sets": 4, "reps": "6-8", "duration_minutes": None, "rest_seconds": 120,
        "description": "Soulever la barre depuis le sol, dos droit, en poussant avec les jambes.",
        "muscles_targeted": ["ischio-jambiers", "fessiers", "dorsaux", "lombaires"],
        "equipment": "gym",
        "level": ["intermediate", "advanced"],
        "objectives": ["muscle_gain"],
        "contraindications": ["hernie discale", "douleur lombaire"],
    },
    "pull_up": {
        "name": "Traction",
        "sets": 3, "reps": "5-10", "duration_minutes": None, "rest_seconds": 90,
        "description": "Suspendu à la barre, tirer le buste jusqu'à ce que le menton dépasse.",
        "muscles_targeted": ["dorsaux", "biceps", "épaules"],
        "equipment": "gym",
        "level": ["intermediate", "advanced"],
        "objectives": ["muscle_gain"],
        "contraindications": ["douleur épaule", "épicondylite"],
    },
    "leg_press": {
        "name": "Presse à cuisses",
        "sets": 4, "reps": "10-12", "duration_minutes": None, "rest_seconds": 90,
        "description": "Assis dans la machine, pousser la plateforme sans verrouiller les genoux.",
        "muscles_targeted": ["quadriceps", "fessiers"],
        "equipment": "gym",
        "level": ["beginner", "intermediate", "advanced"],
        "objectives": ["muscle_gain", "fat_loss"],
        "contraindications": [],
    },
    "cable_row": {
        "name": "Tirage poulie assis",
        "sets": 3, "reps": "12", "duration_minutes": None, "rest_seconds": 75,
        "description": "Assis face à la poulie basse, tirer la barre vers l'abdomen.",
        "muscles_targeted": ["dorsaux", "biceps", "trapèzes"],
        "equipment": "gym",
        "level": ["beginner", "intermediate", "advanced"],
        "objectives": ["muscle_gain"],
        "contraindications": ["hernie discale"],
    },
    # ── Récupération ─────────────────────────────────────────────────────────
    "yoga_stretch": {
        "name": "Yoga / étirements",
        "sets": 1, "reps": None, "duration_minutes": 20, "rest_seconds": 0,
        "description": "Série d'étirements dynamiques et statiques pour la récupération musculaire.",
        "muscles_targeted": ["full body"],
        "equipment": "none",
        "level": ["beginner", "intermediate", "advanced"],
        "objectives": ["general_health", "fat_loss", "endurance", "muscle_gain"],
        "contraindications": [],
    },
    "foam_rolling": {
        "name": "Foam Rolling",
        "sets": 1, "reps": None, "duration_minutes": 15, "rest_seconds": 0,
        "description": "Auto-massage avec rouleau mousse pour relâcher les tensions musculaires.",
        "muscles_targeted": ["full body"],
        "equipment": "home",
        "level": ["beginner", "intermediate", "advanced"],
        "objectives": ["general_health", "muscle_gain"],
        "contraindications": [],
    },
    "walking": {
        "name": "Marche active",
        "sets": 1, "reps": None, "duration_minutes": 40, "rest_seconds": 0,
        "description": "Marche à allure soutenue (5-6 km/h), idéale pour la récupération active.",
        "muscles_targeted": ["cardio léger", "jambes"],
        "equipment": "none",
        "level": ["beginner", "intermediate", "advanced"],
        "objectives": ["general_health", "fat_loss"],
        "contraindications": ["douleur cheville sévère"],
    },
}

# Exercices de récupération disponibles (sous-ensemble du catalogue)
RECOVERY_EXERCISE_KEYS: list[str] = ["yoga_stretch", "walking", "foam_rolling"]
