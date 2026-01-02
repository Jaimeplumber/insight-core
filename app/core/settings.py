from pydantic_settings import BaseSettings
from pydantic import SecretStr

class Settings(BaseSettings):
    database_url: str
    database_url_sync: str

    internal_api_key: SecretStr
    vertical: str = "fitness"
    env: str = "dev"

    class Config:
        env_file = ".env"

settings = Settings()
