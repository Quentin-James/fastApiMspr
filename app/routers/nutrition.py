"""Router FastAPI — recommandations nutritionnelles."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.database import get_db
from app.models.nutrition import (
    NutritionRecommendation,
    PhotoAnalysisResponse,
    UserNutritionProfile,
    Macros,
)
from app.repositories.recommendation_repository import RecommendationRepository
from app.services.nutrition_engine import build_weekly_nutrition_plan
from app.services.vision import analyze_food_image

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/nutrition", tags=["Nutrition"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE_MB = 10


def get_repo() -> RecommendationRepository:
    return RecommendationRepository(get_db())


@router.post(
    "/analyze-photo",
    response_model=PhotoAnalysisResponse,
    summary="Analyser une photo de repas",
    description=(
        "Accepte une image (multipart/form-data) et retourne les aliments détectés "
        "avec leurs macronutriments. Utilise Hugging Face en priorité, "
        "Google Vision API en fallback."
    ),
    status_code=status.HTTP_200_OK,
)
async def analyze_photo(
    file: Annotated[UploadFile, File(description="Image du repas (JPEG, PNG, WebP)")],
    repo: RecommendationRepository = Depends(get_repo),
) -> PhotoAnalysisResponse:
    # Validation du type MIME
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Type de fichier non supporté : {file.content_type}. Formats acceptés : JPEG, PNG, WebP.",
        )

    image_bytes = await file.read()

    # Validation de la taille
    if len(image_bytes) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image trop volumineuse (max {MAX_IMAGE_SIZE_MB} MB).",
        )

    try:
        foods, api_used = await analyze_food_image(image_bytes)
    except RuntimeError as exc:
        msg = str(exc)
        # Modèle HF en cours de chargement → indiquer de réessayer
        if "chargement" in msg or "loading" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=msg,
                headers={"Retry-After": "20"},
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=msg,
        )

    if not foods:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Aucun aliment détecté sur l'image. Essayez avec une photo plus nette.",
        )

    # Calcul des macros totales
    total_calories = sum((f.calories_per_100g or 0) * (f.quantity_g or 150) / 100 for f in foods)
    total_proteins = sum((f.proteins_g or 0) * (f.quantity_g or 150) / 100 for f in foods)
    total_carbs = sum((f.carbs_g or 0) * (f.quantity_g or 150) / 100 for f in foods)
    total_fats = sum((f.fats_g or 0) * (f.quantity_g or 150) / 100 for f in foods)
    avg_confidence = round(sum(f.confidence for f in foods) / len(foods), 3)

    total_macros = Macros(
        calories=round(total_calories, 1),
        proteins_g=round(total_proteins, 1),
        carbs_g=round(total_carbs, 1),
        fats_g=round(total_fats, 1),
    )

    response = PhotoAnalysisResponse(
        foods_detected=foods,
        total_macros=total_macros,
        analysis_api=api_used,
        confidence_avg=avg_confidence,
    )

    # Sauvegarder l'analyse en MongoDB (non bloquant)
    try:
        await repo.save_recommendation({
            "type": "photo_analysis",
            "patientId": "anonymous",
            "api_used": api_used,
            "confidence_score": avg_confidence,
            "foods_count": len(foods),
        })
    except Exception as exc:
        logger.warning("Impossible de sauvegarder l'analyse photo en MongoDB : %s", exc)

    return response


@router.post(
    "/recommend",
    response_model=NutritionRecommendation,
    summary="Générer un plan nutritionnel personnalisé sur 7 jours",
    description=(
        "Accepte le profil utilisateur (objectif, allergies, budget, régime) "
        "et retourne un plan de repas hebdomadaire avec analyse des déséquilibres. "
        "Le plan est sauvegardé en MongoDB."
    ),
    status_code=status.HTTP_201_CREATED,
)
async def recommend_nutrition(
    profile: UserNutritionProfile,
    repo: RecommendationRepository = Depends(get_repo),
) -> NutritionRecommendation:
    try:
        recommendation = await build_weekly_nutrition_plan(profile)
    except Exception as exc:
        logger.exception("Erreur lors de la génération du plan nutritionnel.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne : {str(exc)}",
        )

    # Persister en MongoDB (non bloquant)
    try:
        doc = recommendation.model_dump()
        doc["patientId"] = profile.patient_id
        doc["type"] = "nutrition_plan"
        recommendation_id = await repo.save_meal_plan(doc)
        logger.info("Plan nutritionnel sauvegardé : %s", recommendation_id)
    except Exception as exc:
        logger.warning("Impossible de sauvegarder le plan nutritionnel en MongoDB : %s", exc)

    return recommendation
