from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    mongodb_url: str = "mongodb://localhost:27017"
    weather_api_key: str = "your_default_api_key"
    port: int = 8000
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings=Settings()