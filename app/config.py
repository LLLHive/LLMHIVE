"""
Configuration module for LLMHive.

This file centralizes settings for the application, including API keys,
model parameters, and other operational configurations.
It uses Pydantic's BaseSettings to load configuration from environment
variables, making it easy to manage settings in different environments
(development, staging, production).
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """
    Defines the application's configuration settings.
    Reads settings from environment variables. For example, to set the
    OpenAI API key, define an environment variable named `OPENAI_API_KEY`.
    """
    # API Keys for various LLM providers
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "your_anthropic_api_key_here")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "your_google_api_key_here")

    # Model configuration file path
    MODEL_CONFIG_PATH: str = "models.yaml"

    # Default models for core tasks
    PLANNING_MODEL: str = "gpt-4-turbo"
    CRITIQUE_MODEL: str = "gpt-4"
    SYNTHESIS_MODEL: str = "gpt-4-turbo"

    # Database and Cache configuration
    DATABASE_URL: str = "sqlite:///./llmhive.db"
    REDIS_URL: str = "redis://localhost:6379"

    # Logging configuration
    LOG_LEVEL: str = "INFO"

    # Application settings
    APP_NAME: str = "LLMHive"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    DEFAULT_MODEL: str = "gpt-4" # Default model for general tasks

    class Config:
        # This allows loading variables from a .env file for local development
        env_file = ".env"
        env_file_encoding = 'utf-8'

# Instantiate the settings object to be used throughout the application
settings = Settings()
