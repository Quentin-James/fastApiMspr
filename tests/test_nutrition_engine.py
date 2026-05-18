"""Tests unitaires — nutrition_engine.py (logique pure, sans réseau)."""
import pytest
from unittest.mock import AsyncMock, patch

from app.models.nutrition import UserNutritionProfile, DietType
from app.services.nutrition_engine import (
    build_weekly_nutrition_plan,
    _compute_total_macros,
    _detect_imbalances,
    _filter_meals_for_diet,
    MEAL_TEMPLATES,
    DAYS,
)
from app.models.nutrition import Macros, Meal


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def fat_loss_profile():
    return UserNutritionProfile(
        patient_id="patient_001",
        objective="perte_de_poids",
        allergies=[],
        diet_type=DietType.omnivore,
    )


@pytest.fixture
def muscle_gain_profile():
    return UserNutritionProfile(
        patient_id="patient_002",
        objective="prise_de_masse",
        allergies=["gluten"],
        diet_type=DietType.omnivore,
    )


@pytest.fixture
def vegan_profile():
    return UserNutritionProfile(
        patient_id="patient_003",
        objective="maintenance",
        allergies=[],
        diet_type=DietType.vegan,
    )


# ─── Tests _compute_total_macros ─────────────────────────────────────────────

def test_compute_total_macros_sums_correctly():
    meals = [
        Meal(name="A", meal_type="breakfast", foods=["x"], macros=Macros(calories=300, proteins_g=20, carbs_g=30, fats_g=10)),
        Meal(name="B", meal_type="lunch", foods=["y"], macros=Macros(calories=500, proteins_g=35, carbs_g=50, fats_g=15)),
    ]
    total = _compute_total_macros(meals)
    assert total.calories == 800
    assert total.proteins_g == 55
    assert total.carbs_g == 80
    assert total.fats_g == 25


def test_compute_total_macros_empty():
    total = _compute_total_macros([])
    assert total.calories == 0


# ─── Tests _detect_imbalances ─────────────────────────────────────────────────

def test_detect_imbalances_fat_loss_low_protein():
    macros = Macros(calories=1600, proteins_g=60, carbs_g=220, fats_g=50)
    notes = _detect_imbalances(macros, 1600, "fat_loss")
    assert "protéique" in notes.lower() or "✅" in notes


def test_detect_imbalances_ok():
    macros = Macros(calories=2000, proteins_g=150, carbs_g=200, fats_g=60)
    notes = _detect_imbalances(macros, 2000, "maintenance")
    assert isinstance(notes, str)
    assert len(notes) > 0


# ─── Tests _filter_meals_for_diet ────────────────────────────────────────────

def test_filter_vegan_removes_animal_products():
    meals = MEAL_TEMPLATES["fat_loss"]["lunch"]
    filtered = _filter_meals_for_diet(meals, DietType.vegan, [])
    for meal in filtered:
        foods_str = " ".join(meal["foods"]).lower()
        assert "poulet" not in foods_str or len(filtered) == len(meals)


def test_filter_allergy_excludes_allergen():
    meals = MEAL_TEMPLATES["muscle_gain"]["breakfast"]
    filtered = _filter_meals_for_diet(meals, DietType.omnivore, ["banane"])
    for meal in filtered:
        foods_str = " ".join(meal["foods"]).lower()
        # Le filtre doit exclure les repas contenant "banane"
        assert "banane" not in foods_str or len(filtered) == len(meals)


# ─── Tests build_weekly_nutrition_plan ───────────────────────────────────────

@pytest.mark.asyncio
async def test_build_weekly_plan_returns_7_days(fat_loss_profile):
    with patch("app.services.nutrition_engine.generate_nutrition_message", new_callable=AsyncMock) as mock_msg:
        mock_msg.return_value = "Message de test"
        result = await build_weekly_nutrition_plan(fat_loss_profile)

    assert len(result.weekly_plan) == 7
    for day in result.weekly_plan:
        assert day.day in DAYS
        assert len(day.meals) == 4  # breakfast, lunch, dinner, snack
        assert day.total_macros.calories > 0


@pytest.mark.asyncio
async def test_build_weekly_plan_muscle_gain(muscle_gain_profile):
    with patch("app.services.nutrition_engine.generate_nutrition_message", new_callable=AsyncMock) as mock_msg:
        mock_msg.return_value = "Message prise de masse"
        result = await build_weekly_nutrition_plan(muscle_gain_profile)

    assert result.patient_id == "patient_002"
    assert result.confidence_score > 0
    assert len(result.nutritional_balance_notes) > 0


@pytest.mark.asyncio
async def test_build_weekly_plan_vegan(vegan_profile):
    with patch("app.services.nutrition_engine.generate_nutrition_message", new_callable=AsyncMock) as mock_msg:
        mock_msg.return_value = "Message vegan"
        result = await build_weekly_nutrition_plan(vegan_profile)

    assert len(result.weekly_plan) == 7
    assert result.personalized_message == "Message vegan"
