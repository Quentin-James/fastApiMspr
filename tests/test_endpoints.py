"""Tests d'intégration — endpoints FastAPI (httpx.AsyncClient, APIs externes mockées)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.routers.nutrition import get_repo as nutrition_get_repo
from app.routers.sport import get_repo as sport_get_repo
from app.routers.recommendations import get_repo as rec_get_repo


# ─── Payloads de test ────────────────────────────────────────────────────────

NUTRITION_PROFILE_PAYLOAD = {
    "patient_id": "test_patient_001",
    "objective": "perte_de_poids",
    "allergies": [],
    "diet_type": "omnivore",
    "daily_calories_target": 1600,
    "excluded_foods": [],
}

SPORT_PROFILE_PAYLOAD = {
    "patient_id": "test_patient_001",
    "objective": "fat_loss",
    "fitness_level": "beginner",
    "equipment": "none",
    "available_days": ["lundi", "mercredi", "vendredi"],
    "limitations": [],
    "session_duration_max_minutes": 45,
}


def _make_mock_repo():
    """Crée un faux repo avec toutes les méthodes async."""
    repo = MagicMock()
    repo.save_recommendation = AsyncMock(return_value="mock_id_123")
    repo.save_meal_plan = AsyncMock(return_value="mock_id_123")
    repo.save_sport_program = AsyncMock(return_value="mock_id_123")
    repo.get_sport_program_by_id = AsyncMock(return_value=None)
    repo.update_sport_program_feedback = AsyncMock(return_value=True)
    repo.get_recommendations_by_patient = AsyncMock(return_value=[])
    repo.get_meal_plans_by_patient = AsyncMock(return_value=[])
    return repo


def _client_with_mocks(mock_repo=None, extra_patches=None):
    """Context helper : retourne un AsyncClient avec startup/shutdown et repos mockés."""
    if mock_repo:
        app.dependency_overrides[nutrition_get_repo] = lambda: mock_repo
        app.dependency_overrides[sport_get_repo] = lambda: mock_repo
        app.dependency_overrides[rec_get_repo] = lambda: mock_repo

    patches = [
        patch("app.main.connect_db", new_callable=AsyncMock),
        patch("app.main.close_db", new_callable=AsyncMock),
        patch("app.services.nlp._call_huggingface_nlp", new_callable=AsyncMock, return_value=None),
        patch("app.services.nlp._call_ollama", new_callable=AsyncMock, return_value=None),
    ]
    if extra_patches:
        patches.extend(extra_patches)
    return patches


async def _do_request(method, url, mock_repo=None, **kwargs):
    """Effectue une requête avec tous les mocks en place, retourne la réponse."""
    if mock_repo is None:
        mock_repo = _make_mock_repo()

    app.dependency_overrides[nutrition_get_repo] = lambda: mock_repo
    app.dependency_overrides[sport_get_repo] = lambda: mock_repo
    app.dependency_overrides[rec_get_repo] = lambda: mock_repo

    try:
        with patch("app.main.connect_db", new_callable=AsyncMock), \
             patch("app.main.close_db", new_callable=AsyncMock), \
             patch("app.services.nlp._call_huggingface_nlp", new_callable=AsyncMock, return_value=None), \
             patch("app.services.nlp._call_ollama", new_callable=AsyncMock, return_value=None):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                fn = getattr(ac, method)
                return await fn(url, **kwargs)
    finally:
        app.dependency_overrides.clear()


# ─── Health check ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check():
    response = await _do_request("get", "/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data


# ─── Nutrition recommend ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_nutrition_recommend_success():
    response = await _do_request("post", "/nutrition/recommend", json=NUTRITION_PROFILE_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == "test_patient_001"
    assert len(data["weekly_plan"]) == 7
    assert "nutritional_balance_notes" in data


@pytest.mark.asyncio
async def test_nutrition_recommend_muscle_gain():
    payload = {**NUTRITION_PROFILE_PAYLOAD, "objective": "prise_de_masse", "patient_id": "p002"}
    response = await _do_request("post", "/nutrition/recommend", json=payload)
    assert response.status_code == 201
    assert response.json()["patient_id"] == "p002"


@pytest.mark.asyncio
async def test_nutrition_recommend_vegan():
    payload = {**NUTRITION_PROFILE_PAYLOAD, "diet_type": "vegan", "patient_id": "p003"}
    response = await _do_request("post", "/nutrition/recommend", json=payload)
    assert response.status_code == 201
    assert len(response.json()["weekly_plan"]) == 7


# ─── Sport recommend ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sport_recommend_success():
    response = await _do_request("post", "/sport/recommend", json=SPORT_PROFILE_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == "test_patient_001"
    assert len(data["weekly_program"]) == 7
    assert "progression_notes" in data


@pytest.mark.asyncio
async def test_sport_recommend_muscle_gain_gym():
    payload = {
        **SPORT_PROFILE_PAYLOAD,
        "objective": "muscle_gain",
        "fitness_level": "advanced",
        "equipment": "gym",
        "available_days": ["lundi", "mardi", "jeudi", "vendredi"],
        "patient_id": "p_gym_001",
    }
    response = await _do_request("post", "/sport/recommend", json=payload)
    assert response.status_code == 201


# ─── Sport feedback ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sport_feedback_success():
    feedback_payload = {
        "rating": 4, "comment": "Bien mais un peu dur",
        "too_hard": False, "too_easy": False, "exercises_skipped": [],
    }
    response = await _do_request(
        "put", "/sport/feedback/507f1f77bcf86cd799439011", json=feedback_payload
    )
    assert response.status_code == 200
    assert response.json()["rating"] == 4


@pytest.mark.asyncio
async def test_sport_feedback_not_found():
    mock_repo = _make_mock_repo()
    mock_repo.update_sport_program_feedback = AsyncMock(return_value=False)
    feedback_payload = {"rating": 3, "too_hard": False, "too_easy": False, "exercises_skipped": []}
    response = await _do_request(
        "put", "/sport/feedback/invalid_id", mock_repo=mock_repo, json=feedback_payload
    )
    assert response.status_code == 404


# ─── Historique recommendations ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_recommendations_history():
    response = await _do_request("get", "/recommendations/test_patient_001")
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == "test_patient_001"
    assert "total" in data


@pytest.mark.asyncio
async def test_analyze_photo_invalid_content_type():
    response = await _do_request(
        "post", "/nutrition/analyze-photo",
        files={"file": ("test.pdf", b"fake_pdf_content", "application/pdf")},
    )
    assert response.status_code == 415
