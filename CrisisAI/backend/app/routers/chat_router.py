import logging
import traceback
import re
import json
import asyncio
from typing import List, Dict, Any, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.app.models.chat_models import ChatRequest, ChatResponse
from backend.app.services.agents.classifier_agent import classify
from backend.app.services.rag_service import RAGService
from backend.app.services.gemini_client import GeminiClient
from backend.app.services.agents.verification_agent import verify

# Logger setup
logger = logging.getLogger(__name__)

# APIRouter setup
router = APIRouter(
    prefix="/api/v1",
    tags=["chat"]
)

# Global instances for singleton pattern (Lazy initialization)
_rag_service: Optional[RAGService] = None
_gemini_client: Optional[GeminiClient] = None

def get_rag_service() -> RAGService:
    """Lazily initializes and returns the RAGService."""
    global _rag_service
    if _rag_service is None:
        logger.info("Lazily initializing RAGService...")
        _rag_service = RAGService()
    return _rag_service

def get_gemini_client() -> GeminiClient:
    """Lazily initializes and returns the GeminiClient."""
    global _gemini_client
    if _gemini_client is None:
        logger.info("Lazily initializing GeminiClient...")
        _gemini_client = GeminiClient()
    return _gemini_client

def collect_emergency_numbers(retrieved_context: List[Dict[str, Any]]) -> List[str]:
    """
    Robustly extracts and normalizes emergency numbers from retrieved protocols.
    Supports plain lists, nested dicts, and objects with 'number' keys.
    """
    final_numbers = ["112"]
    seen = {"112"}

    def add_number(val: Any):
        if val is None:
            return
        
        # Convert to string and clean
        s_val = str(val).strip()
        
        # If it looks like a stringified dict or list, ignore it
        if s_val.startswith("{") or s_val.startswith("["):
            return
            
        # Extract digits. Standard Indian emergency numbers: 112, 108, 101, 104
        cleaned = re.sub(r"[^\d]", "", s_val)
        
        # Only add if it's a valid looking number (at least 3 digits) and not already seen
        if cleaned and len(cleaned) >= 3 and cleaned not in seen:
            final_numbers.append(cleaned)
            seen.add(cleaned)

    def walk(obj: Any):
        if obj is None:
            return
        if isinstance(obj, (str, int, float)):
            add_number(obj)
        elif isinstance(obj, dict):
            # Prioritize 'number' key if it exists
            if "number" in obj:
                add_number(obj["number"])
            # Recursively walk values to find other numbers
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    for item in retrieved_context:
        # Check standard fields found in protocols
        walk(item.get("emergency_numbers"))
        walk(item.get("emergency_number"))

    return final_numbers

def collect_sources(retrieved_context: List[Dict[str, Any]]) -> List[str]:
    """
    Extracts and formats source information from retrieved protocols.
    """
    final_sources = []
    seen = set()

    for p in retrieved_context:
        src_data = p.get("source")
        if not src_data:
            # Fallback to protocol title if no source metadata
            title = p.get("title", "CrisisAI Emergency Protocol")
            if title not in seen:
                final_sources.append(title)
                seen.add(title)
            continue

        # Handle list of sources or single source
        sources_to_process = src_data if isinstance(src_data, list) else [src_data]
        
        for s in sources_to_process:
            val = ""
            if isinstance(s, dict):
                org = s.get("org", "")
                title = s.get("document_title", "")
                val = f"{org} - {title}" if org and title else (org or title)
            elif isinstance(s, str):
                val = s
            
            if val and val not in seen:
                final_sources.append(val)
                seen.add(val)
    
    if not final_sources:
        final_sources = ["CrisisAI Emergency Protocols"]
        
    return final_sources

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main endpoint for citizen emergency queries.
    Implements the full RAG-powered chat pipeline.
    """
    logger.info(f"Received chat request for session: {request.session_id} | Query: '{request.query[:50]}...'")
    
    try:
        # Step 1: CLASSIFY
        classification = await classify(request.query)
        crisis_type = classification.get("crisis_type", "unknown")
        severity = classification.get("severity", "MEDIUM")
        confidence = classification.get("confidence", 0.5)
        logger.info(f"Step 1: Classification complete. Type: {crisis_type}, Severity: {severity}")

        # Step 2: RAG RETRIEVE
        retrieved = []
        try:
            service = get_rag_service()
            retrieved = await service.retrieve(request.query, crisis_type=crisis_type, top_k=5)
            logger.info(f"Step 2: Retrieval complete. Found {len(retrieved)} relevant protocols.")
        except Exception:
            logger.exception("Step 2: Retrieval failed.")
            retrieved = []

        # Step 3: BUILD PROMPT
        system_instructions = (
            "You are CrisisAI, an Indian emergency response assistant.\n"
            "Your goal is to provide immediate, life-saving guidance to citizens in distress.\n\n"
            "INSTRUCTIONS:\n"
            "- Provide step-by-step numbered guidance.\n"
            "- Use simple, clear language that a panicking person can follow.\n"
            "- Include relevant emergency numbers prominently.\n"
            "- Be concise but thorough; do not waste time with pleasantries.\n"
            "- Do not recommend dangerous actions.\n"
            "- If the user's query or the detected language is Hindi, respond in Hindi.\n"
        )

        context_text = ""
        if retrieved:
            context_text = "### VERIFIED EMERGENCY PROTOCOLS:\n"
            for i, p in enumerate(retrieved, 1):
                context_text += f"Protocol {i}: {p.get('title')}\n"
                context_text += f"Situation: {p.get('situation')}\n"
                context_text += "Steps to follow:\n"
                for step in p.get("steps", []):
                    context_text += f"- {step}\n"
                
                avoid = p.get("what_to_avoid", [])
                if avoid:
                    context_text += f"DO NOT: {', '.join(avoid)}\n"
                
                nums = p.get("emergency_numbers", [])
                if nums:
                    context_text += f"Relevant numbers: {', '.join(nums)}\n"
                
                src = p.get("source", "CrisisAI Official")
                context_text += f"Source: {src}\n\n"

        prompt = (
            f"{system_instructions}\n"
            f"{context_text}\n"
            f"### CURRENT CRISIS INFO:\n"
            f"- Classified Type: {crisis_type}\n"
            f"- Severity: {severity}\n"
            f"- User Location: lat={request.location.lat}, lng={request.location.lng}\n\n"
            f"USER QUERY: {request.query}\n\n"
            "Provide your verified emergency guidance below:"
        )
        logger.info("Step 3: Prompt construction complete.")

        # Step 4: GENERATE RESPONSE
        raw_response = ""
        try:
            client = get_gemini_client()
            raw_response = client.generate(prompt)
            logger.info("Step 4: Generation complete via AI client.")
        except Exception:
            logger.exception("Step 4: AI generation failed.")
        
        # Fallback if generation failed
        if not raw_response:
            if retrieved:
                p = retrieved[0]
                steps_str = "\n".join([f"{i+1}. {s}" for i, s in enumerate(p.get("steps", []))])
                raw_response = (
                    f"Emergency guidance for {p.get('title')}:\n"
                    f"{steps_str}\n\n"
                    "Please stay calm and wait for help. Call 112 if you haven't already."
                )
                logger.info("Step 4: Generation fallback used (Retrieved protocol steps).")
            else:
                raw_response = (
                    f"Emergency detected: {crisis_type} ({severity}). "
                    "Call 112 immediately for assistance. Please stay calm and wait for help."
                )
                logger.info("Step 4: Generation fallback used (Safe default).")

        # Step 5: VERIFY
        try:
            verified_response = await verify(raw_response, crisis_type, retrieved_context=retrieved)
            logger.info("Step 5: Verification complete.")
        except Exception:
            logger.exception("Step 5: Verification failed.")
            verified_response = raw_response

        # Step 6: BUILD RESPONSE
        # Extract clean emergency numbers using the new helper
        final_numbers = collect_emergency_numbers(retrieved)
        
        # Extract clean sources using the new helper
        final_sources = collect_sources(retrieved)

        state_map = {
            "CRITICAL": "ESCALATION",
            "HIGH": "IMMEDIATE_ACTION",
            "MEDIUM": "TRIAGE",
            "LOW": "MONITORING"
        }
        next_state = state_map.get(severity, "TRIAGE")

        logger.info(f"Step 6: Building final response for session {request.session_id}.")
        return ChatResponse(
            session_id=request.session_id,
            response=verified_response,
            crisis_type=crisis_type,
            severity=severity,
            emergency_numbers=final_numbers,
            sources=final_sources,
            confidence=confidence,
            next_state=next_state,
            stream=False
        )

    except Exception:
        logger.exception("CRITICAL: Unhandled error in chat pipeline.")
        return ChatResponse(
            session_id=request.session_id,
            response="An error occurred while processing your request. Call 112 immediately for emergency assistance.",
            crisis_type="unknown",
            severity="HIGH",
            emergency_numbers=["112"],
            sources=["error-fallback"],
            confidence=0.0,
            next_state="ESCALATION",
            stream=False
        )


# ---------------------------------------------------------------------------
# SSE Streaming Helpers
# ---------------------------------------------------------------------------

SAFE_FALLBACK_TEXT = "Call 112 immediately. Stay calm and wait for help."


def format_sse_chunk(text: str) -> str:
    """Format a single chunk as an SSE data line."""
    return f"data: {json.dumps({'chunk': text}, ensure_ascii=False)}\n\n"


async def stream_text_as_sse(text: str):
    """
    Yields SSE-formatted chunks for a verified response string.
    Each word (with trailing space) is sent as a separate chunk with a tiny
    delay so the Flutter client can render streaming UI.
    """
    if not text or not text.strip():
        text = SAFE_FALLBACK_TEXT

    words = text.split(" ")
    for i, word in enumerate(words):
        # Preserve readable spacing: add trailing space except for last word
        chunk = word + (" " if i < len(words) - 1 else "")
        yield format_sse_chunk(chunk)
        await asyncio.sleep(0.02)

    # Signal completion
    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# POST /api/v1/chat/stream  —  SSE streaming of verified response
# ---------------------------------------------------------------------------

@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    SSE streaming endpoint for Flutter.

    Safety: This does NOT stream raw LLM tokens.  It runs the same full
    pipeline as /chat (classify → RAG → generate → verify), then streams
    the *verified* response word-by-word so the mobile UI feels responsive.
    """

    async def event_generator():
        try:
            # Run the full verified pipeline (same as /chat)
            full_response: ChatResponse = await chat(request)
            async for event in stream_text_as_sse(full_response.response):
                yield event
        except Exception:
            logger.exception("Streaming chat pipeline failed")
            fallback = (
                "Call 112 immediately. Stay calm. "
                "Follow verified emergency guidance."
            )
            async for event in stream_text_as_sse(fallback):
                yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

