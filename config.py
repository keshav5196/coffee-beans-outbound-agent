"""Configuration settings for the voice agent."""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Provider Selection
    llm_provider: str = "groq"  # Options: "groq" or "gemini"

    # Groq API
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"  # Fast and capable

    # Google Gemini API
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"  # Options: gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash

    # Twilio
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    server_base_url: str = "http://localhost:8000"
    debug: bool = False

    # Agent settings
    max_conversation_turns: int = 15
    conversation_timeout_seconds: int = 300  # 5 minutes


# Global settings instance
settings = Settings()

# Legacy compatibility exports for main.py
TWILIO_ACCOUNT_SID = settings.twilio_account_sid
TWILIO_AUTH_TOKEN = settings.twilio_auth_token
TWILIO_PHONE_NUMBER = settings.twilio_phone_number
HOST = settings.app_host
PORT = settings.app_port
SERVER_BASE_URL = settings.server_base_url
AGENT_GREETING = "Hello! This is an AI assistant from CoffeeBeans Consulting. We help companies implement AI solutions, Blockchain applications, and modernize their technology infrastructure. I wanted to reach out and see if you'd be interested in learning about our services. Do you have a couple of minutes to chat?"
