import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API settings
API_TITLE = "PDF Result Page Finder API"
API_VERSION = "1.0.0"

# AI Service Configuration
DEFAULT_AI_SERVICE = os.getenv("DEFAULT_AI_SERVICE").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# OCR Configuration
DEFAULT_OCR_SERVICE = os.getenv("DEFAULT_OCR_SERVICE").lower() if os.getenv("DEFAULT_OCR_SERVICE") else None

# Result Type Configuration
RESULT_TYPE = os.getenv("RESULT_TYPE", "single_page").lower()
MULTI_PAGE_RESULT_TYPE = os.getenv("MULTI_PAGE_RESULT_TYPE", "consolidated").lower()

# AWS Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME", "results-sharing")
AWS_ENABLED = os.getenv("AWS_ENABLED", "true").lower() == "true"

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
# Control whether to send files directly to Telegram or use AWS S3 URLs
TELEGRAM_USE_S3_URL = os.getenv("TELEGRAM_USE_S3_URL", "true").lower() == "true"

# Testing Mode Configuration
TESTING_MODE = os.getenv("TESTING_MODE", "false").lower() == "true"

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# CORS settings
CORS_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",  # For frontend development
    "http://127.0.0.1:3000",  # For frontend development
    "*"  # Allow all origins in development
]
CORS_CREDENTIALS = True
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

# File cleanup settings
FILE_CLEANUP_AGE = 3600  # 1 hour in seconds 