from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str
    TAVILY_API_KEY: str

    MODEL_CONFIG_PATH: str = "models.yaml"
    PLANNING_MODEL: str = "gpt-4-turbo"
    CRITIQUE_MODEL: str = "gpt-4"
    SYNTHESIS_MODEL: str = "gpt-4-turbo"
    LOG_LEVEL: str = "INFO"
    APP_NAME: str = "LLMHive"
    APP_VERSION: str = "1.1.0"
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()