from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    app_port: int = 8085

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "mspr_ia"

    # Hugging Face
    huggingface_api_token: str = ""
    huggingface_food_model: str = "google/vit-base-patch16-224"

    # Google Vision API
    google_vision_api_key: str = ""

    # Backend Spring Boot
    spring_backend_url: str = "http://localhost:8084"

    # NLP / Ollama
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:8080,http://localhost:5173/"

    # Rate limiting
    rate_limit: str = "10/minute"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]


settings = Settings()
