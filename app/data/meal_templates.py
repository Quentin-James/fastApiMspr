"""
Templates de repas et règles diététiques.

Responsabilité unique : définir les données du domaine nutritionnel.
Étendre ce fichier pour ajouter des objectifs, des repas ou des règles de régime
sans toucher à la logique du moteur nutritionnel.
"""
from typing import Any

from app.models.nutrition import DietType, Macros

DAYS: list[str] = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

# Correspondance objectif utilisateur → clé interne
OBJECTIVE_MAP: dict[str, str] = {
    "perte_de_poids":  "fat_loss",
    "perte de poids":  "fat_loss",
    "fat_loss":        "fat_loss",
    "prise_de_masse":  "muscle_gain",
    "prise de masse":  "muscle_gain",
    "muscle_gain":     "muscle_gain",
    "maintenance":     "maintenance",
    "maintien":        "maintenance",
    "endurance":       "maintenance",
    "santé générale":  "maintenance",
    "general_health":  "maintenance",
}

# Aliments exclus par type de régime (substring matching sur la liste foods du repas)
EXCLUDED_BY_DIET: dict[DietType, list[str]] = {
    DietType.vegan: [
        "poulet", "dinde", "bœuf", "saumon", "cabillaud", "crevettes", "thon",
        "saumon fumé", "whey", "lait", "fromage", "yaourt", "œuf", "œufs",
        "steak", "blanc de poulet", "viande",
    ],
    DietType.vegetarian: [
        "poulet", "dinde", "bœuf", "saumon", "cabillaud", "crevettes", "thon",
        "saumon fumé", "steak", "blanc de poulet", "viande",
    ],
    DietType.gluten_free: ["pain", "pâtes", "crackers", "wrap", "granola", "flocons d'avoine"],
    DietType.lactose_free: ["lait", "fromage", "yaourt", "fromage frais", "parmesan", "fromage râpé"],
}

# Calories cibles par défaut lorsque le profil ne précise pas daily_calories_target
DEFAULT_CALORIES: dict[str, float] = {
    "fat_loss":    1600.0,
    "muscle_gain": 2400.0,
    "maintenance": 2000.0,
}

MealTemplate = dict[str, Any]
MealSlot = dict[str, list[MealTemplate]]

MEAL_TEMPLATES: dict[str, MealSlot] = {
    "fat_loss": {
        "breakfast": [
            {
                "name": "Bol de flocons d'avoine aux fruits rouges",
                "foods": ["flocons d'avoine", "lait écrémé", "fraises", "myrtilles"],
                "macros": Macros(calories=320, proteins_g=14, carbs_g=52, fats_g=6),
            },
            {
                "name": "Œufs brouillés aux légumes",
                "foods": ["2 œufs", "épinards", "tomates cerises", "pain complet"],
                "macros": Macros(calories=280, proteins_g=18, carbs_g=22, fats_g=12),
            },
            {
                "name": "Yaourt grec aux graines de chia",
                "foods": ["yaourt grec 0%", "graines de chia", "miel", "kiwi"],
                "macros": Macros(calories=250, proteins_g=20, carbs_g=28, fats_g=4),
            },
        ],
        "lunch": [
            {
                "name": "Salade de poulet grillé quinoa",
                "foods": ["poulet grillé", "quinoa", "concombre", "tomates", "vinaigrette légère"],
                "macros": Macros(calories=420, proteins_g=38, carbs_g=35, fats_g=10),
            },
            {
                "name": "Soupe de lentilles aux légumes",
                "foods": ["lentilles corail", "carottes", "céleri", "épices"],
                "macros": Macros(calories=360, proteins_g=22, carbs_g=55, fats_g=4),
            },
            {
                "name": "Wrap de dinde aux crudités",
                "foods": ["blanc de dinde", "wrap blé complet", "laitue", "avocat", "concombre"],
                "macros": Macros(calories=400, proteins_g=30, carbs_g=38, fats_g=12),
            },
        ],
        "dinner": [
            {
                "name": "Saumon vapeur brocolis riz basmati",
                "foods": ["saumon", "brocolis", "riz basmati", "citron"],
                "macros": Macros(calories=450, proteins_g=35, carbs_g=42, fats_g=12),
            },
            {
                "name": "Filet de cabillaud légumes rôtis",
                "foods": ["cabillaud", "poivrons", "courgettes", "oignons", "herbes de Provence"],
                "macros": Macros(calories=320, proteins_g=32, carbs_g=22, fats_g=8),
            },
            {
                "name": "Wok de crevettes et légumes",
                "foods": ["crevettes", "pak choi", "champignons", "sauce soja légère", "gingembre"],
                "macros": Macros(calories=380, proteins_g=30, carbs_g=28, fats_g=10),
            },
        ],
        "snack": [
            {
                "name": "Amandes et pomme",
                "foods": ["amandes (30g)", "pomme"],
                "macros": Macros(calories=200, proteins_g=5, carbs_g=22, fats_g=11),
            },
            {
                "name": "Fromage blanc et framboises",
                "foods": ["fromage blanc 0%", "framboises"],
                "macros": Macros(calories=130, proteins_g=12, carbs_g=14, fats_g=1),
            },
        ],
    },
    "muscle_gain": {
        "breakfast": [
            {
                "name": "Pancakes protéinés banane",
                "foods": ["flocons d'avoine", "banane", "protéine whey", "œufs", "lait"],
                "macros": Macros(calories=520, proteins_g=38, carbs_g=62, fats_g=10),
            },
            {
                "name": "Omelette fromage épinards",
                "foods": ["3 œufs", "fromage râpé", "épinards", "pain de mie complet"],
                "macros": Macros(calories=480, proteins_g=34, carbs_g=28, fats_g=22),
            },
        ],
        "lunch": [
            {
                "name": "Riz poulet brocolis",
                "foods": ["riz complet", "blanc de poulet", "brocolis", "huile d'olive"],
                "macros": Macros(calories=620, proteins_g=52, carbs_g=68, fats_g=12),
            },
            {
                "name": "Pasta bolognaise",
                "foods": ["pâtes complètes", "viande de bœuf maigre", "sauce tomate", "parmesan"],
                "macros": Macros(calories=580, proteins_g=42, carbs_g=72, fats_g=14),
            },
        ],
        "dinner": [
            {
                "name": "Steak haché patate douce haricots verts",
                "foods": ["steak haché 5%", "patate douce", "haricots verts", "moutarde"],
                "macros": Macros(calories=550, proteins_g=45, carbs_g=52, fats_g=14),
            },
            {
                "name": "Saumon riz complet asperges",
                "foods": ["saumon", "riz complet", "asperges", "citron"],
                "macros": Macros(calories=580, proteins_g=42, carbs_g=52, fats_g=18),
            },
        ],
        "snack": [
            {
                "name": "Shake protéiné banane amandes",
                "foods": ["protéine whey", "banane", "lait demi-écrémé", "beurre d'amande"],
                "macros": Macros(calories=380, proteins_g=32, carbs_g=38, fats_g=9),
            },
            {
                "name": "Tuna crackers",
                "foods": ["thon en conserve", "crackers complets", "fromage blanc"],
                "macros": Macros(calories=280, proteins_g=28, carbs_g=22, fats_g=6),
            },
        ],
    },
    "maintenance": {
        "breakfast": [
            {
                "name": "Tartines complètes avocat œuf poché",
                "foods": ["pain complet", "avocat", "œuf poché", "graines de sésame"],
                "macros": Macros(calories=400, proteins_g=18, carbs_g=38, fats_g=20),
            },
            {
                "name": "Bowl de chia fruits frais",
                "foods": ["graines de chia", "lait d'amande", "mangue", "kiwi", "granola"],
                "macros": Macros(calories=350, proteins_g=10, carbs_g=48, fats_g=14),
            },
        ],
        "lunch": [
            {
                "name": "Buddha bowl légumes pois chiches",
                "foods": ["pois chiches", "riz", "avocat", "carottes", "chou rouge", "tahini"],
                "macros": Macros(calories=500, proteins_g=20, carbs_g=62, fats_g=18),
            },
            {
                "name": "Tartine de saumon fumé",
                "foods": ["pain complet", "saumon fumé", "fromage frais", "concombre", "aneth"],
                "macros": Macros(calories=420, proteins_g=28, carbs_g=32, fats_g=16),
            },
        ],
        "dinner": [
            {
                "name": "Curry de légumes lentilles",
                "foods": ["lentilles", "tomates", "épinards", "lait de coco light", "épices curry"],
                "macros": Macros(calories=440, proteins_g=22, carbs_g=58, fats_g=12),
            },
            {
                "name": "Poulet rôti légumes du four",
                "foods": ["cuisse de poulet", "poivrons", "oignons", "pommes de terre", "romarin"],
                "macros": Macros(calories=480, proteins_g=36, carbs_g=42, fats_g=14),
            },
        ],
        "snack": [
            {
                "name": "Fruits secs et noix",
                "foods": ["noix de cajou", "raisins secs", "amandes"],
                "macros": Macros(calories=220, proteins_g=6, carbs_g=20, fats_g=14),
            },
            {
                "name": "Smoothie vert",
                "foods": ["épinards", "banane", "lait végétal", "graines de lin"],
                "macros": Macros(calories=180, proteins_g=5, carbs_g=32, fats_g=4),
            },
        ],
    },
}
