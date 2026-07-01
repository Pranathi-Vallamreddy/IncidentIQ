"""Application configuration (env-driven, with safe defaults for local dev)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    # Gemini model id. Overridable via GEMINI_MODEL. gemini-1.5-* is retired;
    # gemini-2.5-flash is the current fast/cheap default.
    gemini_model: str = "gemini-2.5-flash"
    cors_origins: str = "http://localhost:5173,http://localhost:4173"
    # Regex of allowed origins. Defaults to any *.vercel.app deployment so the
    # frontend works without pinning its exact URL. Set to "" to disable, or
    # tighten via CORS_ORIGINS with an explicit list.
    cors_origin_regex: str = r"https://.*\.vercel\.app"
    database_url: str = "sqlite:///./incidentiq.db"

    # Engine defaults (overridable via the Settings page / AppSettings row).
    default_sensitivity: float = 0.6

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_enabled(self) -> bool:
        return bool(self.gemini_api_key)


settings = Settings()
