import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging at INFO level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from the project root (.env)
# Path: backend/app/main.py -> backend/app -> backend -> Project Root
ROOT_DIR = Path(__file__).resolve().parents[2]
env_path = ROOT_DIR / ".env"

if env_path.exists():
    load_dotenv(env_path)
    logger.info(f"Loaded environment variables from: {env_path}")
else:
    logger.warning(f"No .env file found at: {env_path}")

# Diagnostics (Safe logging)
gemini_present = "GEMINI_API_KEY" in os.environ
groq_present = "GROQ_API_KEY" in os.environ
logger.info(f"Diagnostics: GEMINI_API_KEY present: {gemini_present} | GROQ_API_KEY present: {groq_present}")

# Now import the routers after env is loaded
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routers import chat_router, incident_router

# Initialize FastAPI app
app = FastAPI(
    title="CrisisAI Backend",
    version="1.0",
    description="Dual-sided AI crisis platform — Google Solution Challenge 2026"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    """
    Health check endpoint for CI/CD and dashboard monitoring.
    """
    return {
        "status": "ok", 
        "version": "1.0", 
        "react_dashboard": True,
        "api_keys_configured": gemini_present and groq_present
    }

# Mount routers
app.include_router(chat_router.router)
app.include_router(incident_router.router)

@app.on_event("startup")
async def startup_event():
    logger.info("CrisisAI backend started. Endpoints: /health, /api/v1/chat, /api/v1/incidents, /api/v1/query, /api/v1/ws")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
