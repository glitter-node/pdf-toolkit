from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_host: str = "127.0.0.1"
    app_port: int = 8013
    max_upload_mb: int = 30
    max_files: int = 10
    max_pages: int = 500
    max_concurrent_pdf_requests: int = Field(default=2, ge=1, le=16)
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
