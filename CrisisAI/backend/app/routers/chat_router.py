import logging
from fastapi import APIRouter, HTTPException
from backend.app.models.chat_models import ChatRequest, ChatResponse
from backend.app.services.agents.classifier_agent import classify

# Logger setup
logger = logging.getLogger(__name__)

# APIRouter setup
router = APIRouter(
    prefix="/api/v1",
    tags=["chat"]
)

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main endpoint for citizen emergency queries.
    Currently a stub implementation that calls the classifier agent.
    RAG and full response pipeline will be integrated in Day 2.
    """
    logger.info(f"Received chat request for session: {request.session_id}")
    
    try:
        # Call the classifier agent to determine crisis type and severity
        # We pass the query for classification
        classification = await classify(request.query)
        
        crisis_type = classification.get("crisis_type", "unknown")
        severity = classification.get("severity", "MEDIUM")
        confidence = classification.get("confidence", 0.5)
        
        # Build the stub response
        # RAG and protocols will be integrated in the next phase
        response_text = (
            f"Stub response. RAG and full pipeline coming in Day 2. "
            f"Crisis classified as: {crisis_type}, severity: {severity}"
        )
        
        return ChatResponse(
            session_id=request.session_id,
            response=response_text,
            crisis_type=crisis_type,
            severity=severity,
            emergency_numbers=["112", "108"],  # Standard Indian emergency + medical
            sources=["stub: classifier-only response"],
            confidence=confidence,
            next_state="IMMEDIATE_ACTION",
            stream=False
        )
        
    except Exception as e:
        logger.error(f"Error in chat_endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="Internal classification error"
        )
