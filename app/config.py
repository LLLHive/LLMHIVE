"""
Configuration module for LLMHive.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # --- ALL KEYS ARE NOW OPTIONAL ---
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None

    MODEL_CONFIG_PATH: str = "models.yaml"
    PLANNING_MODEL: str = "gpt-4-turbo"
    CRITIQUE_MODEL: str = "gpt-4"
    SYNTHESIS_MODEL: str = "gpt-4-turbo"
    LOG_LEVEL: str = "INFO"
    APP_NAME: str = "LLMHive"
    APP_VERSION: str = "1.3.0"  # Version bump for new feature
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8'
    )

settings = Settings()