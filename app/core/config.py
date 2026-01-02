from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    # Config general
    ENV: str = Field("development", env="ENV")
    DEBUG: bool = Field(True, env="DEBUG")
    
    # Database
    POSTGRES_HOST: str = Field("localhost", env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(5432, env="POSTGRES_PORT")
    POSTGRES_DB: str = Field("reddit_insights", env="POSTGRES_DB")
    POSTGRES_USER: str = Field("user", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field("password", env="POSTGRES_PASSWORD")

    # Redis cache
    REDIS_URL: str = Field("redis://localhost:6379/0", env="REDIS_URL")

    # API keys (ejemplo)
    OPENAI_API_KEY: str = Field("", env="OPENAI_API_KEY")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Singleton para usar en todo el proyecto
settings = Settings()