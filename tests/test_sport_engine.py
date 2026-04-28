"""Tests unitaires — sport_engine.py (logique pure, sans réseau)."""
import pytest
from unittest.mock import AsyncMock, patch

from app.models.sport import (
    Equipment,
    FeedbackRequest,
    FitnessLevel,
    SportObjective,
    UserSportProfile,
)
from app.services.sport_engine import (
    _filter_exercises,
    _compute_progression_notes,
    build_weekly_sport_program,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def beginner_fat_loss_profile():
    return UserSportProfile(
        patient_id="sport_patient_001",
        objective=SportObjective.fat_loss,
        fitness_level=FitnessLevel.beginner,
        equipment=Equipment.none,
        available_days=["lundi", "mercredi", "vendredi"],
        limitations=[],
        session_duration_max_minutes=45,
    )


@pytest.fixture
def advanced_gym_profile():
    return UserSportProfile(
        patient_id="sport_patient_002",
        objective=SportObjective.muscle_gain,
        fitness_level=FitnessLevel.advanced,
        equipment=Equipment.gym,
        available_days=["lundi", "mardi", "jeudi", "vendredi", "samedi"],
        limitations=["douleur genou droit"],
        session_duration_max_minutes=90,
    )


@pytest.fixture
def beginner_with_back_pain():
    return UserSportProfile(
        patient_id="sport_patient_003",
        objective=SportObjective.general_health,
        fitness_level=FitnessLevel.beginner,
        equipment=Equipment.home,
        available_days=["mardi", "jeudi", "samedi"],
        limitations=["hernie discale", "douleur lombaire"],
        session_duration_max_minutes=30,
    )


# ─── Tests _filter_exercises ─────────────────────────────────────────────────

def test_filter_exercises_no_equipment_excludes_gym():
    exercises = _filter_exercises(
        SportObjective.fat_loss, FitnessLevel.intermediate, Equipment.none, []
    )
    for ex in exercises:
        assert ex["equipment"] in ["none"], f"Exercice gym trouvé : {ex['name']}"


def test_filter_exercises_beginner_excludes_advanced():
    exercises = _filter_exercises(
        SportObjective.general_health, FitnessLevel.beginner, Equipment.gym, []
    )
    for ex in exercises:
        assert "beginner" in ex["level"], f"Exercice trop avancé : {ex['name']}"


def test_filter_exercises_excludes_contraindications():
    exercises = _filter_exercises(
        SportObjective.fat_loss, FitnessLevel.intermediate, Equipment.none,
        ["douleur genou droit"]
    )
    for ex in exercises:
        contras = [c.lower() for c in ex["contraindications"]]
        assert not any("genou" in c for c in contras), \
            f"Exercice contre-indiqué trouvé : {ex['name']}"


def test_filter_exercises_gym_includes_all():
    exercises = _filter_exercises(
        SportObjective.muscle_gain, FitnessLevel.advanced, Equipment.gym, []
    )
    assert len(exercises) > 3


# ─── Tests _compute_progression_notes ────────────────────────────────────────

def test_progression_notes_beginner():
    notes = _compute_progression_notes(FitnessLevel.beginner, SportObjective.fat_loss)
    assert "technique" in notes.lower() or "charge" in notes.lower()


def test_progression_notes_with_easy_feedback():
    feedbacks = [FeedbackRequest(rating=5, too_easy=True)]
    notes = _compute_progression_notes(FitnessLevel.intermediate, SportObjective.general_health, feedbacks)
    assert "intensité" in notes.lower() or "📈" in notes


def test_progression_notes_with_hard_feedback():
    feedbacks = [FeedbackRequest(rating=2, too_hard=True)]
    notes = _compute_progression_notes(FitnessLevel.beginner, SportObjective.general_health, feedbacks)
    assert "réduisez" in notes.lower() or "📉" in notes


# ─── Tests build_weekly_sport_program ────────────────────────────────────────

@pytest.mark.asyncio
async def test_build_weekly_program_returns_7_days(beginner_fat_loss_profile):
    with patch("app.services.sport_engine.generate_sport_message", new_callable=AsyncMock) as mock_msg:
        mock_msg.return_value = "Allez courage !"
        result = await build_weekly_sport_program(beginner_fat_loss_profile)

    assert len(result.weekly_program) == 7
    assert result.patient_id == "sport_patient_001"


@pytest.mark.asyncio
async def test_build_weekly_program_respects_available_days(beginner_fat_loss_profile):
    with patch("app.services.sport_engine.generate_sport_message", new_callable=AsyncMock) as mock_msg:
        mock_msg.return_value = "Super !"
        result = await build_weekly_sport_program(beginner_fat_loss_profile)

    rest_days = [s for s in result.weekly_program if s.session_type == "Repos"]
    active_days = [s for s in result.weekly_program if s.session_type != "Repos"]
    # 3 jours disponibles → 3 séances actives max, 4 repos
    assert len(active_days) <= 3
    assert len(rest_days) >= 4


@pytest.mark.asyncio
async def test_build_weekly_program_excludes_contraindicated_exercises(advanced_gym_profile):
    with patch("app.services.sport_engine.generate_sport_message", new_callable=AsyncMock) as mock_msg:
        mock_msg.return_value = "Go !"
        result = await build_weekly_sport_program(advanced_gym_profile)

    for session in result.weekly_program:
        for exercise in session.exercises:
            for contra in exercise.contraindications:
                assert "genou" not in contra.lower(), \
                    f"Exercice contre-indiqué trouvé : {exercise.name}"


@pytest.mark.asyncio
async def test_build_weekly_program_with_back_pain(beginner_with_back_pain):
    with patch("app.services.sport_engine.generate_sport_message", new_callable=AsyncMock) as mock_msg:
        mock_msg.return_value = "Prenez soin de vous !"
        result = await build_weekly_sport_program(beginner_with_back_pain)

    # Vérifier qu'aucun exercice contre-indiqué pour hernie discale n'est inclus
    for session in result.weekly_program:
        for exercise in session.exercises:
            for contra in exercise.contraindications:
                assert "hernie" not in contra.lower() and "lombaire" not in contra.lower(), \
                    f"Exercice contre-indiqué inclus : {exercise.name}"
