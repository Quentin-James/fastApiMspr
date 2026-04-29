"""
Base de données nutritionnelle des aliments.
Clés en minuscules, sans accents, compatibles avec les labels ImageNet / Hugging Face.

Responsabilité unique : fournir les données nutritionnelles.
Étendre ce fichier pour ajouter de nouveaux aliments sans toucher aux services.
"""

# Grammes assumés par défaut lorsque la portion n'est pas détectée
DEFAULT_QUANTITY_G: float = 150.0

# Données affichées quand aucune API vision n'est disponible (mode développement)
MOCK_FOODS: list[dict] = [
    {"label": "chicken", "score": 0.82},
    {"label": "broccoli", "score": 0.74},
    {"label": "rice", "score": 0.68},
]

# Base nutritionnelle : calories / protéines / glucides / lipides pour 100 g
FOOD_NUTRITION_DB: dict[str, dict] = {
    # ── Féculents / céréales ─────────────────────────────────────────────────
    "pizza":        {"calories_per_100g": 266, "proteins_g": 11,  "carbs_g": 33, "fats_g": 10},
    "bread":        {"calories_per_100g": 265, "proteins_g": 9,   "carbs_g": 49, "fats_g": 3.2},
    "bagel":        {"calories_per_100g": 250, "proteins_g": 10,  "carbs_g": 48, "fats_g": 1.5},
    "rice":         {"calories_per_100g": 130, "proteins_g": 2.7, "carbs_g": 28, "fats_g": 0.3},
    "pasta":        {"calories_per_100g": 131, "proteins_g": 5,   "carbs_g": 25, "fats_g": 1.1},
    "spaghetti":    {"calories_per_100g": 131, "proteins_g": 5,   "carbs_g": 25, "fats_g": 1.1},
    "noodle":       {"calories_per_100g": 138, "proteins_g": 4.5, "carbs_g": 25, "fats_g": 2},
    "waffle":       {"calories_per_100g": 291, "proteins_g": 8,   "carbs_g": 37, "fats_g": 13},
    "pancake":      {"calories_per_100g": 227, "proteins_g": 6,   "carbs_g": 28, "fats_g": 10},
    "french loaf":  {"calories_per_100g": 270, "proteins_g": 9,   "carbs_g": 52, "fats_g": 2},
    # ── Protéines animales ───────────────────────────────────────────────────
    "chicken":      {"calories_per_100g": 165, "proteins_g": 31, "carbs_g": 0,   "fats_g": 3.6},
    "hen":          {"calories_per_100g": 165, "proteins_g": 31, "carbs_g": 0,   "fats_g": 3.6},
    "steak":        {"calories_per_100g": 271, "proteins_g": 26, "carbs_g": 0,   "fats_g": 18},
    "beef":         {"calories_per_100g": 250, "proteins_g": 26, "carbs_g": 0,   "fats_g": 17},
    "pork":         {"calories_per_100g": 242, "proteins_g": 27, "carbs_g": 0,   "fats_g": 14},
    "ham":          {"calories_per_100g": 145, "proteins_g": 17, "carbs_g": 2,   "fats_g": 7},
    "sausage":      {"calories_per_100g": 301, "proteins_g": 13, "carbs_g": 2,   "fats_g": 27},
    "salmon":       {"calories_per_100g": 208, "proteins_g": 20, "carbs_g": 0,   "fats_g": 13},
    "fish":         {"calories_per_100g": 130, "proteins_g": 22, "carbs_g": 0,   "fats_g": 4},
    "tuna":         {"calories_per_100g": 132, "proteins_g": 28, "carbs_g": 0,   "fats_g": 1},
    "shrimp":       {"calories_per_100g": 85,  "proteins_g": 18, "carbs_g": 0,   "fats_g": 1},
    "egg":          {"calories_per_100g": 155, "proteins_g": 13, "carbs_g": 1.1, "fats_g": 11},
    # ── Produits laitiers ────────────────────────────────────────────────────
    "cheese":       {"calories_per_100g": 402, "proteins_g": 25, "carbs_g": 1.3, "fats_g": 33},
    "yogurt":       {"calories_per_100g": 59,  "proteins_g": 10, "carbs_g": 3.6, "fats_g": 0.4},
    "milk":         {"calories_per_100g": 61,  "proteins_g": 3.2,"carbs_g": 4.8, "fats_g": 3.3},
    "ice cream":    {"calories_per_100g": 207, "proteins_g": 3.5,"carbs_g": 24,  "fats_g": 11},
    # ── Fruits ──────────────────────────────────────────────────────────────
    "apple":        {"calories_per_100g": 52,  "proteins_g": 0.3,"carbs_g": 14,  "fats_g": 0.2},
    "banana":       {"calories_per_100g": 89,  "proteins_g": 1.1,"carbs_g": 23,  "fats_g": 0.3},
    "orange":       {"calories_per_100g": 47,  "proteins_g": 0.9,"carbs_g": 12,  "fats_g": 0.1},
    "strawberry":   {"calories_per_100g": 32,  "proteins_g": 0.7,"carbs_g": 8,   "fats_g": 0.3},
    "lemon":        {"calories_per_100g": 29,  "proteins_g": 1.1,"carbs_g": 9,   "fats_g": 0.3},
    "fig":          {"calories_per_100g": 74,  "proteins_g": 0.8,"carbs_g": 19,  "fats_g": 0.3},
    "pineapple":    {"calories_per_100g": 50,  "proteins_g": 0.5,"carbs_g": 13,  "fats_g": 0.1},
    "pomegranate":  {"calories_per_100g": 83,  "proteins_g": 1.7,"carbs_g": 19,  "fats_g": 1.2},
    # ── Légumes ─────────────────────────────────────────────────────────────
    "salad":        {"calories_per_100g": 15,  "proteins_g": 1.3,"carbs_g": 2.9, "fats_g": 0.2},
    "broccoli":     {"calories_per_100g": 34,  "proteins_g": 2.8,"carbs_g": 7,   "fats_g": 0.4},
    "mushroom":     {"calories_per_100g": 22,  "proteins_g": 3.1,"carbs_g": 3.3, "fats_g": 0.3},
    "cauliflower":  {"calories_per_100g": 25,  "proteins_g": 1.9,"carbs_g": 5,   "fats_g": 0.3},
    "corn":         {"calories_per_100g": 86,  "proteins_g": 3.2,"carbs_g": 19,  "fats_g": 1.2},
    "artichoke":    {"calories_per_100g": 53,  "proteins_g": 3,  "carbs_g": 11,  "fats_g": 0.2},
    "cucumber":     {"calories_per_100g": 16,  "proteins_g": 0.7,"carbs_g": 3.6, "fats_g": 0.1},
    "bell pepper":  {"calories_per_100g": 31,  "proteins_g": 1,  "carbs_g": 6,   "fats_g": 0.3},
    # ── Plats composés / snacks ──────────────────────────────────────────────
    "burger":       {"calories_per_100g": 295, "proteins_g": 17, "carbs_g": 24,  "fats_g": 14},
    "hotdog":       {"calories_per_100g": 290, "proteins_g": 11, "carbs_g": 23,  "fats_g": 18},
    "sandwich":     {"calories_per_100g": 250, "proteins_g": 12, "carbs_g": 30,  "fats_g": 9},
    "soup":         {"calories_per_100g": 50,  "proteins_g": 3,  "carbs_g": 7,   "fats_g": 1.5},
    "guacamole":    {"calories_per_100g": 152, "proteins_g": 2,  "carbs_g": 9,   "fats_g": 13},
    "carbonara":    {"calories_per_100g": 320, "proteins_g": 15, "carbs_g": 38,  "fats_g": 12},
    "lasagna":      {"calories_per_100g": 135, "proteins_g": 8,  "carbs_g": 13,  "fats_g": 5},
    "burrito":      {"calories_per_100g": 206, "proteins_g": 8,  "carbs_g": 26,  "fats_g": 8},
    "taco":         {"calories_per_100g": 218, "proteins_g": 9,  "carbs_g": 23,  "fats_g": 10},
    "sushi":        {"calories_per_100g": 150, "proteins_g": 6,  "carbs_g": 26,  "fats_g": 2},
    # ── Pâtisseries / desserts ───────────────────────────────────────────────
    "chocolate":    {"calories_per_100g": 546, "proteins_g": 5,  "carbs_g": 60,  "fats_g": 31},
    "cake":         {"calories_per_100g": 347, "proteins_g": 5,  "carbs_g": 56,  "fats_g": 12},
    "donut":        {"calories_per_100g": 452, "proteins_g": 5,  "carbs_g": 51,  "fats_g": 25},
    "pretzel":      {"calories_per_100g": 380, "proteins_g": 9,  "carbs_g": 80,  "fats_g": 3},
    # ── Graisses / condiments ────────────────────────────────────────────────
    "avocado":      {"calories_per_100g": 160, "proteins_g": 2,  "carbs_g": 9,   "fats_g": 15},
    "butter":       {"calories_per_100g": 717, "proteins_g": 0.9,"carbs_g": 0.1, "fats_g": 81},
}
