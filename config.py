"""Configuration management using environment variables."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


class Config:
    """Application configuration."""

    # LLM API Keys
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    PROXYPAL_KEY=os.getenv("PROXYPAL_KEY")
    # OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    # ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    # Model defaults gemini-2.5-flash
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
