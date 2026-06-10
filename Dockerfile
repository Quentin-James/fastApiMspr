# ─── Étape 1 : builder ───────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ─── Étape 2 : image finale ───────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copier les packages depuis le builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copier le code source
COPY app/ ./app/

# Variables d'environnement par défaut (surchargées via docker-compose ou --env-file)
ENV APP_ENV=production \
    APP_PORT=8085 \
    MONGODB_URL=mongodb://mongo:27017 \
    MONGODB_DB_NAME=mspr_ia

EXPOSE ${APP_PORT}

# Utilisateur non-root pour la sécurité
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:'+(import os; os.environ.get('PORT','8085'))+'/health').raise_for_status()" || exit 1

# Render injecte $PORT ; fallback 8085 pour les autres environnements
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8085} --workers 2"]
