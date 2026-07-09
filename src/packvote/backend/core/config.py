from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql://user:pass@localhost:5432/packvote"
    openai_api_key: str = ""
    langchain_api_key: str = ""
    langchain_project: str = "packvote"
    langchain_tracing_v2: str = "true"
    resend_api_key: str = ""
    resend_from_email: str = "packvote@resend.dev"
    secret_key: str = "change-me-in-production"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:8501"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
