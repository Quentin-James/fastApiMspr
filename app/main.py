"""
Point d'entrée du microservice IA (FastAPI).
Lancer : uvicorn app.main:app --reload --port 8085
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.database import connect_db, close_db
from app.routers import nutrition, sport, recommendations

# ─── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO if settings.app_env != "production" else logging.WARNING,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ─── Rate limiter ─────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])

# ─── Application FastAPI ──────────────────────────────────────────────────────

app = FastAPI(
    title="MSPR IA — Microservice de recommandations",
    description=(
        "Microservice Python / FastAPI fournissant des recommandations nutritionnelles "
        "et sportives personnalisées via Hugging Face, Google Vision API et un moteur "
        "de règles multi-critères. Données persistées en MongoDB."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={"name": "Équipe MSPR", "email": "jamesquentin46@gmail.com"},
    license_info={"name": "MIT"},
)

# ─── Rate limiting ────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ─── Événements lifecycle ─────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    logger.info("🚀 Démarrage du microservice IA (env=%s, port=%s).", settings.app_env, settings.app_port)
    await connect_db()


@app.on_event("shutdown")
async def shutdown():
    await close_db()
    logger.info("🛑 Arrêt du microservice IA.")

# ─── Gestion globale des erreurs ──────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Erreur non gérée : %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur. Veuillez réessayer."},
    )

# ─── Routers ─────────────────────────────────────────────────────────────────

app.include_router(nutrition.router)
app.include_router(sport.router)
app.include_router(recommendations.router)
