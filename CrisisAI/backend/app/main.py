import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.routers import chat_router

# Configure logging at INFO level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize FastAPI app
app = FastAPI(
    title="CrisisAI Backend",
    version="1.0",
    description="Dual-sided AI crisis platform — Google Solution Challenge 2026"
)

# Add CORS middleware
# For development, we allow all origins. React dev server usually runs on localhost:5173.
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
        "react_dashboard": True
    }

# Mount routers
app.include_router(chat_router.router)

@app.on_event("startup")
async def startup_event():
    logging.info("CrisisAI backend started. Endpoints: /health, /api/v1/chat")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
