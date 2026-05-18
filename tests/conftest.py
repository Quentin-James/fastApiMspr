"""Configuration et fixtures pytest communes."""
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db


# ─── Event loop ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ─── Mock MongoDB ─────────────────────────────────────────────────────────────

def _make_mock_db():
    """Crée un mock complet de la base MongoDB."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="mock_id_123"))
    mock_collection.find = MagicMock(return_value=MagicMock(
        sort=MagicMock(return_value=MagicMock(
            limit=MagicMock(return_value=MagicMock(
                to_list=AsyncMock(return_value=[])
            ))
        ))
    ))
    mock_collection.find_one = AsyncMock(return_value=None)
    mock_collection.update_one = AsyncMock(return_value=MagicMock(modified_count=1))
    mock_collection.create_index = AsyncMock(return_value=None)

    mock_db.recommendations = mock_collection
    mock_db.meal_plans = mock_collection
    mock_db.sport_programs = mock_collection
    return mock_db


@pytest.fixture
def mock_db():
    return _make_mock_db()


@pytest_asyncio.fixture
async def client(mock_db) -> AsyncGenerator[AsyncClient, None]:
    """Client HTTP de test avec MongoDB mocké."""
    with patch("app.database.connect_db", new_callable=AsyncMock), \
         patch("app.database.close_db", new_callable=AsyncMock), \
         patch("app.database._db", mock_db), \
         patch("app.routers.nutrition.get_repo", return_value=MagicMock(
             save_recommendation=AsyncMock(return_value="mock_id"),
             save_meal_plan=AsyncMock(return_value="mock_id"),
         )), \
         patch("app.routers.sport.get_repo", return_value=MagicMock(
             save_sport_program=AsyncMock(return_value="mock_id"),
             get_sport_program_by_id=AsyncMock(return_value=None),
             update_sport_program_feedback=AsyncMock(return_value=True),
         )), \
         patch("app.routers.recommendations.get_repo", return_value=MagicMock(
             get_recommendations_by_patient=AsyncMock(return_value=[]),
             get_meal_plans_by_patient=AsyncMock(return_value=[]),
         )):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
