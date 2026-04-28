"""
Moteur de recommandations nutritionnelles.
Génère un plan de repas sur 7 jours adapté au profil utilisateur.
"""
from typing import List, Dict, Any
import logging

from app.models.nutrition import (
    DayPlan,
    Meal,
    Macros,
    NutritionRecommendation,
    UserNutritionProfile,
    FoodItem,
    DietType,
)
from app.services.nlp import generate_nutrition_message

logger = logging.getLogger(__name__)

DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

# Base de repas par type de régime et objectif
MEAL_TEMPLATES: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "fat_loss": {
        "breakfast": [
            {"name": "Bol de flocons d'avoine aux fruits rouges", "foods": ["flocons d'avoine", "lait écrémé", "fraises", "myrtilles"], "macros": Macros(calories=320, proteins_g=14, carbs_g=52, fats_g=6)},
            {"name": "Œufs brouillés aux légumes", "foods": ["2 œufs", "épinards", "tomates cerises", "pain complet"], "macros": Macros(calories=280, proteins_g=18, carbs_g=22, fats_g=12)},
            {"name": "Yaourt grec aux graines de chia", "foods": ["yaourt grec 0%", "graines de chia", "miel", "kiwi"], "macros": Macros(calories=250, proteins_g=20, carbs_g=28, fats_g=4)},
        ],
        "lunch": [
            {"name": "Salade de poulet grillé quinoa", "foods": ["poulet grillé", "quinoa", "concombre", "tomates", "vinaigrette légère"], "macros": Macros(calories=420, proteins_g=38, carbs_g=35, fats_g=10)},
            {"name": "Soupe de lentilles aux légumes", "foods": ["lentilles corail", "carottes", "céleri", "épices"], "macros": Macros(calories=360, proteins_g=22, carbs_g=55, fats_g=4)},
            {"name": "Wrap de dinde aux crudités", "foods": ["blanc de dinde", "wrap blé complet", "laitue", "avocat", "concombre"], "macros": Macros(calories=400, proteins_g=30, carbs_g=38, fats_g=12)},
        ],
        "dinner": [
            {"name": "Saumon vapeur brocolis riz basmati", "foods": ["saumon", "brocolis", "riz basmati", "citron"], "macros": Macros(calories=450, proteins_g=35, carbs_g=42, fats_g=12)},
            {"name": "Filet de cabillaud légumes rôtis", "foods": ["cabillaud", "poivrons", "courgettes", "oignons", "herbes de Provence"], "macros": Macros(calories=320, proteins_g=32, carbs_g=22, fats_g=8)},
            {"name": "Wok de crevettes et légumes", "foods": ["crevettes", "pak choi", "champignons", "sauce soja légère", "gingembre"], "macros": Macros(calories=380, proteins_g=30, carbs_g=28, fats_g=10)},
        ],
        "snack": [
            {"name": "Amandes et pomme", "foods": ["amandes (30g)", "pomme"], "macros": Macros(calories=200, proteins_g=5, carbs_g=22, fats_g=11)},
            {"name": "Fromage blanc et framboises", "foods": ["fromage blanc 0%", "framboises"], "macros": Macros(calories=130, proteins_g=12, carbs_g=14, fats_g=1)},
        ],
    },
    "muscle_gain": {
        "breakfast": [
            {"name": "Pancakes protéinés banane", "foods": ["flocons d'avoine", "banane", "protéine whey", "œufs", "lait"], "macros": Macros(calories=520, proteins_g=38, carbs_g=62, fats_g=10)},
            {"name": "Omelette fromage épinards", "foods": ["3 œufs", "fromage râpé", "épinards", "pain de mie complet"], "macros": Macros(calories=480, proteins_g=34, carbs_g=28, fats_g=22)},
        ],
        "lunch": [
            {"name": "Riz poulet brocolis", "foods": ["riz complet", "blanc de poulet", "brocolis", "huile d'olive"], "macros": Macros(calories=620, proteins_g=52, carbs_g=68, fats_g=12)},
            {"name": "Pasta bolognaise light", "foods": ["pâtes complètes", "viande de bœuf maigre", "sauce tomate", "parmesan"], "macros": Macros(calories=580, proteins_g=42, carbs_g=72, fats_g=14)},
        ],
        "dinner": [
            {"name": "Steak haché patate douce haricots verts", "foods": ["steak haché 5%", "patate douce", "haricots verts", "moutarde"], "macros": Macros(calories=550, proteins_g=45, carbs_g=52, fats_g=14)},
            {"name": "Saumon riz complet asperges", "foods": ["saumon", "riz complet", "asperges", "citron"], "macros": Macros(calories=580, proteins_g=42, carbs_g=52, fats_g=18)},
        ],
        "snack": [
            {"name": "Shake protéiné banane amandes", "foods": ["protéine whey", "banane", "lait demi-écrémé", "beurre d'amande"], "macros": Macros(calories=380, proteins_g=32, carbs_g=38, fats_g=9)},
            {"name": "Tuna crackers", "foods": ["thon en conserve", "crackers complets", "fromage blanc"], "macros": Macros(calories=280, proteins_g=28, carbs_g=22, fats_g=6)},
        ],
    },
    "maintenance": {
        "breakfast": [
            {"name": "Tartines complètes avocat œuf poché", "foods": ["pain complet", "avocat", "œuf poché", "graines de sésame"], "macros": Macros(calories=400, proteins_g=18, carbs_g=38, fats_g=20)},
            {"name": "Bowl de chia fruits frais", "foods": ["graines de chia", "lait d'amande", "mangue", "kiwi", "granola"], "macros": Macros(calories=350, proteins_g=10, carbs_g=48, fats_g=14)},
        ],
        "lunch": [
            {"name": "Buddha bowl légumes pois chiches", "foods": ["pois chiches", "riz", "avocat", "carottes", "chou rouge", "tahini"], "macros": Macros(calories=500, proteins_g=20, carbs_g=62, fats_g=18)},
            {"name": "Tartine de saumon fumé", "foods": ["pain complet", "saumon fumé", "fromage frais", "concombre", "aneth"], "macros": Macros(calories=420, proteins_g=28, carbs_g=32, fats_g=16)},
        ],
        "dinner": [
            {"name": "Curry de légumes lentilles", "foods": ["lentilles", "tomates", "épinards", "lait de coco light", "épices curry"], "macros": Macros(calories=440, proteins_g=22, carbs_g=58, fats_g=12)},
            {"name": "Poulet rôti légumes du four", "foods": ["cuisse de poulet", "poivrons", "oignons", "pommes de terre", "romarin"], "macros": Macros(calories=480, proteins_g=36, carbs_g=42, fats_g=14)},
        ],
        "snack": [
            {"name": "Fruits secs et noix", "foods": ["noix de cajou", "raisins secs", "amandes"], "macros": Macros(calories=220, proteins_g=6, carbs_g=20, fats_g=14)},
            {"name": "Smoothie vert", "foods": ["épinards", "banane", "lait végétal", "graines de lin"], "macros": Macros(calories=180, proteins_g=5, carbs_g=32, fats_g=4)},
        ],
    },
}

OBJECTIVE_MAP = {
    "perte_de_poids": "fat_loss",
    "perte de poids": "fat_loss",
    "fat_loss": "fat_loss",
    "prise_de_masse": "muscle_gain",
    "prise de masse": "muscle_gain",
    "muscle_gain": "muscle_gain",
    "maintenance": "maintenance",
    "maintien": "maintenance",
    "endurance": "maintenance",
    "santé générale": "maintenance",
    "general_health": "maintenance",
}


def _filter_meals_for_diet(
    meals: List[Dict[str, Any]], diet_type: DietType, allergies: List[str]
) -> List[Dict[str, Any]]:
    """Filtre les repas incompatibles avec le régime ou les allergies."""
    excluded_by_diet: Dict[DietType, List[str]] = {
        DietType.vegan: ["poulet", "dinde", "bœuf", "saumon", "cabillaud", "crevettes", "thon", "saumon fumé", "whey", "lait", "fromage", "yaourt", "œuf", "œufs", "steak", "blanc de poulet", "viande"],
        DietType.vegetarian: ["poulet", "dinde", "bœuf", "saumon", "cabillaud", "crevettes", "thon", "saumon fumé", "steak", "blanc de poulet", "viande"],
        DietType.gluten_free: ["pain", "pâtes", "crackers", "wrap", "granola", "flocons d'avoine"],
        DietType.lactose_free: ["lait", "fromage", "yaourt", "fromage frais", "parmesan", "fromage râpé"],
    }

    exclusions = excluded_by_diet.get(diet_type, [])
    exclusions += [a.lower() for a in allergies]

    filtered = []
    for meal in meals:
        foods_lower = [f.lower() for f in meal["foods"]]
        if not any(exc in " ".join(foods_lower) for exc in exclusions):
            filtered.append(meal)
    return filtered or meals  # si tout est filtré, retourner tout (plutôt que rien)


def _compute_total_macros(meals: List[Meal]) -> Macros:
    total = Macros(calories=0, proteins_g=0, carbs_g=0, fats_g=0)
    for m in meals:
        total.calories += m.macros.calories
        total.proteins_g += m.macros.proteins_g
        total.carbs_g += m.macros.carbs_g
        total.fats_g += m.macros.fats_g
    return Macros(
        calories=round(total.calories, 1),
        proteins_g=round(total.proteins_g, 1),
        carbs_g=round(total.carbs_g, 1),
        fats_g=round(total.fats_g, 1),
    )


def _detect_imbalances(macros: Macros, target_calories: float, objective_key: str) -> str:
    """Détecte les déséquilibres nutritionnels par rapport aux AJR."""
    notes = []
    # AJR standards (base 2000 kcal, ajusté selon objectif)
    protein_ratio = macros.proteins_g * 4 / macros.calories if macros.calories else 0
    carb_ratio = macros.carbs_g * 4 / macros.calories if macros.calories else 0
    fat_ratio = macros.fats_g * 9 / macros.calories if macros.calories else 0

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

    if not notes:
        notes.append("✅ Équilibre nutritionnel satisfaisant selon votre profil")

    return " | ".join(notes)


async def build_weekly_nutrition_plan(
    profile: UserNutritionProfile,
) -> NutritionRecommendation:
    """Génère un plan nutritionnel hebdomadaire complet."""
    import random

    objective_key = OBJECTIVE_MAP.get(profile.objective.lower(), "maintenance")
    templates = MEAL_TEMPLATES.get(objective_key, MEAL_TEMPLATES["maintenance"])

    target_calories = profile.daily_calories_target or (
        1600 if objective_key == "fat_loss" else 2400 if objective_key == "muscle_gain" else 2000
    )

    weekly_plan: List[DayPlan] = []

    for i, day_name in enumerate(DAYS):
        day_meals: List[Meal] = []

        for meal_type in ["breakfast", "lunch", "dinner", "snack"]:
            options = templates.get(meal_type, [])
            options = _filter_meals_for_diet(options, profile.diet_type, profile.allergies)
            # Rotation : éviter la répétition exacte entre jours
            template = options[i % len(options)]

            # Exclure les aliments demandés par l'utilisateur
            if profile.excluded_foods:
                options_filtered = [
                    o for o in options
                    if not any(exc.lower() in " ".join(o["foods"]).lower() for exc in profile.excluded_foods)
                ]
                if options_filtered:
                    template = options_filtered[i % len(options_filtered)]

            day_meals.append(
                Meal(
                    name=template["name"],
                    meal_type=meal_type,
                    foods=template["foods"],
                    macros=template["macros"],
                )
            )

        total = _compute_total_macros(day_meals)
        weekly_plan.append(DayPlan(day=day_name, meals=day_meals, total_macros=total))

    # Calcul des macros moyennes sur la semaine
    avg_macros = Macros(
        calories=round(sum(d.total_macros.calories for d in weekly_plan) / 7, 1),
        proteins_g=round(sum(d.total_macros.proteins_g for d in weekly_plan) / 7, 1),
        carbs_g=round(sum(d.total_macros.carbs_g for d in weekly_plan) / 7, 1),
        fats_g=round(sum(d.total_macros.fats_g for d in weekly_plan) / 7, 1),
    )

    balance_notes = _detect_imbalances(avg_macros, target_calories, objective_key)
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
