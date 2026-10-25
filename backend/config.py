import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Config:
    # Flask Core
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-fallback-secret-key-health-agent-2026")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-fallback-secret-2026")
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", 24))
    PORT = int(os.getenv("PORT", 5000))
    HOST = os.getenv("HOST", "0.0.0.0")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

    # Database
    DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()
    SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL", "")
    SQLITE_DB_PATH = BASE_DIR / os.getenv("SQLITE_DB_PATH", "database/ai_health.db")
    ORACLE_USER = os.getenv("ORACLE_USER", "ai_health_user")
    ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "")
    ORACLE_DSN = os.getenv("ORACLE_DSN", "localhost:1521/XEPDB1")
    ORACLE_CONFIG_DIR = os.getenv("ORACLE_CONFIG_DIR", None)
    ORACLE_WALLET_PASSWORD = os.getenv("ORACLE_WALLET_PASSWORD", None)

    # DigiLocker / API Setu
    DIGILOCKER_ENV = os.getenv("DIGILOCKER_ENV", "sandbox")
    DIGILOCKER_CLIENT_ID = os.getenv("DIGILOCKER_CLIENT_ID", "demo_client_id_aihealth")
    DIGILOCKER_CLIENT_SECRET = os.getenv("DIGILOCKER_CLIENT_SECRET", "demo_client_secret_aihealth")
    DIGILOCKER_REDIRECT_URI = os.getenv(
        "DIGILOCKER_REDIRECT_URI", "http://127.0.0.1:5000/api/doctor/digilocker/callback"
    )
    DIGILOCKER_AUTH_URL = os.getenv(
        "DIGILOCKER_AUTH_URL", "https://api.digitallocker.gov.in/public/oauth2/1/authorize"
    )
    DIGILOCKER_TOKEN_URL = os.getenv(
        "DIGILOCKER_TOKEN_URL", "https://api.digitallocker.gov.in/public/oauth2/1/token"
    )
    DIGILOCKER_DOC_URL = os.getenv(
        "DIGILOCKER_DOC_URL", "https://api.digitallocker.gov.in/public/oauth2/1/xml/issued"
    )

    # AI Configuration
    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "med-ai")

    # Security & Uploads
    UPLOAD_FOLDER = BASE_DIR / os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))  # 10 MB
    ALLOWED_EXTENSIONS = set(os.getenv("ALLOWED_EXTENSIONS", "pdf,png,jpg,jpeg").split(","))
    BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", 10))
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1")
    CORS_ORIGINS = [orig.strip() for orig in os.getenv("CORS_ORIGINS", "*").split(",")]
