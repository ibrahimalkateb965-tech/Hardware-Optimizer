import os
import secrets
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"
LOGS_DIR = BASE_DIR / "logs"
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"

SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Load .env
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

class Settings:
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8555"))
    
    # OpenCode Go / GLM-5.3-Flash API
    OPENCODE_GO_API_KEY: str = os.getenv("OPENCODE_GO_API_KEY", "")
    OPENCODE_GO_BASE_URL: str = os.getenv(
        "OPENCODE_GO_BASE_URL", "https://opencode.ai/inference/go/openai/v1"
    )
    OPENCODE_GO_MODEL: str = os.getenv("OPENCODE_GO_MODEL", "glm-5.3-flash")
    
    # Environment & Sandbox mode
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    SANDBOX_MODE: bool = os.getenv("SANDBOX_MODE", "false").lower() in ("true", "1", "yes")
    
    # Cryptographic Ephemeral Session Token (Generated on every boot)
    SESSION_TOKEN: str = secrets.token_urlsafe(32)
    
    # SQLite Database File
    DB_PATH: Path = BASE_DIR / "sessions" / "optimizer_ledger.db"

settings = Settings()
