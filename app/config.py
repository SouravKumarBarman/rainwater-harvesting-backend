from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_url: str = "mongodb://localhost:27017"
    weather_api_key: str = "your_default_api_key"
    port: int = 8000
    jwt_secret_key: str = "change-me-in-production"
    jwt_refresh_secret_key: str = "change-me-too-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    cookie_secure: bool = False
    serpapi_api_key: str | None = None
    shopping_country: str = "in"
    shopping_language: str = "en"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
