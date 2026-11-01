from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./roadmaps.db"
    secret_key: str = "dev-secret-change-me"
    access_token_minutes: int = 60 * 24 * 7

    anthropic_api_key: str = ""
    planner_model: str = "claude-sonnet-4-6"
    day_model: str = "claude-sonnet-4-6"
    quiz_model: str = "claude-haiku-4-5"

    max_days: int = 180
    days_per_module: int = 6
    llm_workers: int = 4
    max_active_roadmaps_per_user: int = 2

    frontend_url: str = "http://localhost:5173"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""


settings = Settings()
