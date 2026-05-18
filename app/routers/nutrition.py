"""Router FastAPI — recommandations nutritionnelles."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.database import get_db
from app.models.nutrition import (
    DietType,
    Macros,
    NutritionRecommendation,
    PhotoAnalysisResponse,
    UserNutritionProfile,
)
from app.repositories.recommendation_repository import RecommendationRepository
from app.services.nutrition_engine import build_weekly_nutrition_plan
from app.services.spring_client import fetch_patient_profile, push_recommendation
from app.services.vision import analyze_food_image

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/nutrition", tags=["Nutrition"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE_MB = 10


def get_repo() -> RecommendationRepository:
    return RecommendationRepository(get_db())


# ─── Analyse photo ────────────────────────────────────────────────────────────

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
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Type de fichier non supporté : {file.content_type}. Formats acceptés : JPEG, PNG, WebP.",
        )

    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image trop volumineuse (max {MAX_IMAGE_SIZE_MB} MB).",
        )

    try:
        foods, api_used = await analyze_food_image(image_bytes)
    except RuntimeError as exc:
        msg = str(exc)
        if "chargement" in msg or "loading" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=msg,
                headers={"Retry-After": "20"},
            )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=msg)

    if not foods:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Aucun aliment détecté sur l'image. Essayez avec une photo plus nette.",
        )

    total_calories = sum((f.calories_per_100g or 0) * (f.quantity_g or 150) / 100 for f in foods)
    total_proteins  = sum((f.proteins_g or 0)       * (f.quantity_g or 150) / 100 for f in foods)
    total_carbs     = sum((f.carbs_g or 0)           * (f.quantity_g or 150) / 100 for f in foods)
    total_fats      = sum((f.fats_g or 0)            * (f.quantity_g or 150) / 100 for f in foods)
    avg_confidence  = round(sum(f.confidence for f in foods) / len(foods), 3)

    response = PhotoAnalysisResponse(
        foods_detected=foods,
        total_macros=Macros(
            calories=round(total_calories, 1),
            proteins_g=round(total_proteins, 1),
            carbs_g=round(total_carbs, 1),
            fats_g=round(total_fats, 1),
        ),
        analysis_api=api_used,
        confidence_avg=avg_confidence,
    )

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


# ─── Plan nutritionnel ────────────────────────────────────────────────────────

@router.post(
    "/recommend",
    response_model=NutritionRecommendation,
    summary="Générer un plan nutritionnel personnalisé sur 7 jours",
    description=(
        "Accepte le profil utilisateur et retourne un plan de repas hebdomadaire. "
        "Si clerk_user_id est fourni : enrichit le profil depuis le backend Java "
        "(allergies, régime, calories cibles) et pousse le résultat vers Java après génération."
    ),
    status_code=status.HTTP_201_CREATED,
)
async def recommend_nutrition(
    profile: UserNutritionProfile,
    repo: RecommendationRepository = Depends(get_repo),
) -> NutritionRecommendation:

    # ── 1. Enrichissement depuis Java si clerk_user_id fourni ────────────────
    patient_id_java: int | None = None

    if profile.clerk_user_id:
        java_profile = await fetch_patient_profile(profile.clerk_user_id)
        if java_profile:
            patient_id_java = java_profile.patient_id
            logger.info(
                "Profil Java récupéré pour clerk=%s (patient_id=%s)",
                profile.clerk_user_id, patient_id_java,
            )
            updates: dict = {}

            # Allergies Java → fusionner avec celles déclarées dans la requête
            if java_profile.allergies:
                java_allergies = [a.strip().lower() for a in java_profile.allergies.split(",") if a.strip()]
                merged = list({*[a.lower() for a in profile.allergies], *java_allergies})
                updates["allergies"] = merged

            # Régime alimentaire Java → si la requête n'a pas précisé de régime
            if java_profile.dietary_restrictions and profile.diet_type == DietType.omnivore:
                restriction_map = {
                    "vegan":        DietType.vegan,
                    "vegetarian":   DietType.vegetarian,
                    "gluten":       DietType.gluten_free,
                    "gluten_free":  DietType.gluten_free,
                    "lactose":      DietType.lactose_free,
                    "lactose_free": DietType.lactose_free,
                }
                r = java_profile.dietary_restrictions.lower()
                for key, diet in restriction_map.items():
                    if key in r:
                        updates["diet_type"] = diet
                        break

            # Calories cibles Java → si non précisé dans la requête
            if java_profile.daily_caloric_intake and not profile.daily_calories_target:
                updates["daily_calories_target"] = float(java_profile.daily_caloric_intake)

            if updates:
                profile = profile.model_copy(update=updates)

    # ── 2. Génération du plan ────────────────────────────────────────────────
    try:
        recommendation = await build_weekly_nutrition_plan(profile)
    except Exception as exc:
        logger.exception("Erreur lors de la génération du plan nutritionnel.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne : {str(exc)}",
        )

    # ── 3. Persistance MongoDB ───────────────────────────────────────────────
    try:
        doc = recommendation.model_dump()
        doc["patientId"] = profile.patient_id
        doc["type"] = "nutrition_plan"
        recommendation_id = await repo.save_meal_plan(doc)
        logger.info("Plan nutritionnel sauvegardé MongoDB : %s", recommendation_id)
    except Exception as exc:
        logger.warning("Impossible de sauvegarder en MongoDB : %s", exc)

    # ── 4. Push vers Java (non bloquant) ─────────────────────────────────────
    if profile.clerk_user_id:
        await push_recommendation(
            clerk_user_id        = profile.clerk_user_id,
            recommendation_type  = "nutrition",
            content              = recommendation.model_dump(),
            personalized_message = recommendation.personalized_message,
            objective            = profile.objective,
            api_used             = recommendation.api_used,
            confidence_score     = recommendation.confidence_score,
            patient_id           = patient_id_java,
        )

    return recommendation
