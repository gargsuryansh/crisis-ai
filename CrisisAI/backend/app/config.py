import os
from typing import List

# CrisisAI Backend Configuration
# Centralized access for all environment variables

# AI API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Google Cloud Settings
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "crisisai-2026")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./service_account.json")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# Data Sources
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

# Vector Database (FAISS) - Online
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "data/embeddings/faiss_index_768.bin")
FAISS_METADATA_PATH = os.getenv("FAISS_METADATA_PATH", "data/embeddings/metadata_768.json")

# Vector Database (FAISS) - Offline/Mobile
FAISS_INDEX_PATH_OFFLINE = os.getenv("FAISS_INDEX_PATH_OFFLINE", "data/embeddings/faiss_index_384.bin")
FAISS_METADATA_PATH_OFFLINE = os.getenv("FAISS_METADATA_PATH_OFFLINE", "data/embeddings/metadata_384.json")

# Vector Database (ChromaDB)
# WARNING: CHROMA_PERSIST_DIR must NEVER be /tmp as it is volatile.
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

# Firebase & Backend
FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "./firebase_service_account.json")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")

def validate_required_keys():
    """
    Validates that essential API keys are present in the environment.
    Raises RuntimeError for critical missing keys.
    Prints a warning for non-critical missing keys.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("CRITICAL: GEMINI_API_KEY is missing. AI features will not work.")
    
    if not GROQ_API_KEY:
        raise RuntimeError("CRITICAL: GROQ_API_KEY is missing. Fallback AI features will not work.")
    
    if not TWITTER_BEARER_TOKEN:
        print("WARNING: TWITTER_BEARER_TOKEN is missing. Twitter scraping features will be limited.")

# Auto-validate if this module is imported directly for testing (optional)
# if __name__ == "__main__":
#     validate_required_keys()
