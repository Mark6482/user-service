from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "User Service"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str = "postgresql+asyncpg://root:root@localhost/user_service"
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()