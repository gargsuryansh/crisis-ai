from typing import Optional, List, Literal
from pydantic import BaseModel

# CrisisAI Chat Models
# Pydantic models matching shared/contracts/chat_request.json and chat_response.json

class Location(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None

class ChatRequest(BaseModel):
    session_id: str
    query: str
    mode: Literal["online", "offline"]
    location: Location
    conversation_state: Literal[
        "INTAKE", 
        "TRIAGE", 
        "IMMEDIATE_ACTION", 
        "MONITORING", 
        "ESCALATION", 
        "POST_CRISIS"
    ]
    language_hint: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str
    crisis_type: Literal[
        "fire", 
        "medical", 
        "flood", 
        "earthquake", 
        "snakebite", 
        "accident", 
        "chemical", 
        "violence", 
        "unknown"
    ]
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    emergency_numbers: List[str]
    sources: List[str]
    confidence: float
    next_state: str
    stream: bool
