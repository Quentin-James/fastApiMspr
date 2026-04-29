"""
Moteur de recommandations nutritionnelles.

Responsabilité : générer un plan de repas hebdomadaire à partir d'un profil utilisateur.
Les données (templates de repas, règles diététiques) sont dans app/data/meal_templates.py.
"""
import logging
from typing import List, Dict, Any

from app.data.meal_templates import (
    DAYS,
    DEFAULT_CALORIES,
    EXCLUDED_BY_DIET,
    MEAL_TEMPLATES,
    OBJECTIVE_MAP,
)
from app.models.nutrition import (
    DayPlan,
    DietType,
    Macros,
    Meal,
    NutritionRecommendation,
    UserNutritionProfile,
)
from app.services.nlp import generate_nutrition_message

logger = logging.getLogger(__name__)


# ─── Filtrage ─────────────────────────────────────────────────────────────────

def _filter_meals_for_diet(
    meals: List[Dict[str, Any]],
    diet_type: DietType,
    allergies: List[str],
) -> List[Dict[str, Any]]:
    """Retire les repas incompatibles avec le régime ou les allergies déclarées."""
    exclusions = EXCLUDED_BY_DIET.get(diet_type, []) + [a.lower() for a in allergies]
    filtered = [
        meal for meal in meals
        if not any(exc in " ".join(f.lower() for f in meal["foods"]) for exc in exclusions)
    ]
    return filtered or meals  # si tout est filtré, retourner tout plutôt que rien


# ─── Calcul des macros ────────────────────────────────────────────────────────

def _compute_total_macros(meals: List[Meal]) -> Macros:
    """Additionne les macros de tous les repas d'un jour."""
    return Macros(
        calories=round(sum(m.macros.calories for m in meals), 1),
        proteins_g=round(sum(m.macros.proteins_g for m in meals), 1),
        carbs_g=round(sum(m.macros.carbs_g for m in meals), 1),
        fats_g=round(sum(m.macros.fats_g for m in meals), 1),
    )


# ─── Détection des déséquilibres ─────────────────────────────────────────────

def _detect_imbalances(macros: Macros, target_calories: float, objective_key: str) -> str:
    """
    Évalue les ratios macronutriments par rapport aux recommandations ANSES/OMS.
    Retourne une chaîne de notes séparées par « | ».
    """
    if macros.calories == 0:
        return "⚠️ Aucune calorie détectée."

    protein_ratio = macros.proteins_g * 4 / macros.calories
    carb_ratio    = macros.carbs_g    * 4 / macros.calories
    fat_ratio     = macros.fats_g     * 9 / macros.calories

    notes: List[str] = []

    if objective_key == "fat_loss":
        if protein_ratio < 0.25:
            notes.append("⚠️ Apport protéique insuffisant pour préserver la masse musculaire (objectif : ≥ 25 %)")
        if carb_ratio > 0.55:
            notes.append("⚠️ Glucides légèrement élevés pour un objectif de perte de poids")
    elif objective_key == "muscle_gain":
        if protein_ratio < 0.30:
            notes.append("⚠️ Augmentez l'apport protéique (objectif : ≥ 30 % des calories)")
        if macros.calories < target_calories * 0.9:
            notes.append("⚠️ Surplus calorique insuffisant pour la prise de masse")
    else:
        if protein_ratio < 0.15:
            notes.append("⚠️ Apport protéique bas (objectif : ≥ 15 %)")

    if fat_ratio > 0.40:
        notes.append("⚠️ Apport en lipides élevé (objectif : ≤ 35 %)")

    return " | ".join(notes) if notes else "✅ Équilibre nutritionnel satisfaisant selon votre profil"


# ─── Point d'entrée public ────────────────────────────────────────────────────

async def build_weekly_nutrition_plan(profile: UserNutritionProfile) -> NutritionRecommendation:
    """Génère un plan nutritionnel hebdomadaire complet à partir du profil patient."""
    objective_key  = OBJECTIVE_MAP.get(profile.objective.lower(), "maintenance")
    templates      = MEAL_TEMPLATES.get(objective_key, MEAL_TEMPLATES["maintenance"])
    target_calories = profile.daily_calories_target or DEFAULT_CALORIES.get(objective_key, 2000.0)

    weekly_plan: List[DayPlan] = []

    for i, day_name in enumerate(DAYS):
        day_meals: List[Meal] = []

        for meal_type in ("breakfast", "lunch", "dinner", "snack"):
            options = _filter_meals_for_diet(
                templates.get(meal_type, []),
                profile.diet_type,
                profile.allergies,
            )

            # Exclure les aliments blacklistés par le patient
            if profile.excluded_foods:
                filtered = [
                    o for o in options
                    if not any(
                        exc.lower() in " ".join(o["foods"]).lower()
                        for exc in profile.excluded_foods
                    )
                ]
                if filtered:
                    options = filtered

            # Rotation cyclique pour éviter la répétition exacte entre jours
            template = options[i % len(options)]
            day_meals.append(Meal(
                name=template["name"],
                meal_type=meal_type,
                foods=template["foods"],
                macros=template["macros"],
            ))

        weekly_plan.append(DayPlan(
            day=day_name,
            meals=day_meals,
            total_macros=_compute_total_macros(day_meals),
        ))

    avg_macros = Macros(
        calories=round(sum(d.total_macros.calories for d in weekly_plan) / 7, 1),
        proteins_g=round(sum(d.total_macros.proteins_g for d in weekly_plan) / 7, 1),
        carbs_g=round(sum(d.total_macros.carbs_g for d in weekly_plan) / 7, 1),
        fats_g=round(sum(d.total_macros.fats_g for d in weekly_plan) / 7, 1),
    )

    balance_notes        = _detect_imbalances(avg_macros, target_calories, objective_key)
    personalized_message = await generate_nutrition_message(
        profile.objective, balance_notes, profile.patient_id
    )

    return NutritionRecommendation(
        patient_id=profile.patient_id,
        weekly_plan=weekly_plan,
        nutritional_balance_notes=balance_notes,
        personalized_message=personalized_message,
        api_used="nutrition_engine",
        confidence_score=0.88,
    )
