"""
CrisisAI Authority Incident Router
Endpoints for the React dashboard (authority side).

Contracts touched:
  - incident_schema.json   → GET  /api/v1/incidents
  - query_request.json     → POST /api/v1/query
  - query_response.json    → POST /api/v1/query  (response)
  - PATCH /api/v1/incidents/{id}
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional, Any
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import APIRouter, HTTPException, Query, Request

from backend.app.models.incident_models import (
    Incident,
    IncidentListResponse,
    IncidentLocation,
    IncidentPatchRequest,
    IncidentPatchResponse,
    QueryRequest,
    QueryResponse,
)
from backend.app.services.chroma_client import ChromaClient
from backend.app.services.gemini_client import GeminiClient

logger = logging.getLogger("crisisai.incident_router")

router = APIRouter(
    prefix="/api/v1",
    tags=["incidents"],
)

# ---------------------------------------------------------------------------
# Firebase / Firestore Initialization
# ---------------------------------------------------------------------------

_firestore_db = None

def get_firestore_db():
    """
    Initializes Firebase and returns a Firestore client.
    Handles re-initialization safely.
    """
    global _firestore_db
    if _firestore_db is None:
        try:
            if not firebase_admin._apps:
                # Resolve path to service account
                ROOT_DIR = Path(__file__).resolve().parents[3]
                sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "./firebase_service_account.json")
                if not os.path.isabs(sa_path):
                    sa_full_path = str(ROOT_DIR / sa_path)
                else:
                    sa_full_path = sa_path
                
                if not os.path.exists(sa_full_path):
                    logger.error(f"Firestore service account not found at {sa_full_path}")
                    return None

                cred = credentials.Certificate(sa_full_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin initialized successfully.")
            
            _firestore_db = firestore.client()
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {e}")
            return None
    return _firestore_db

# ---------------------------------------------------------------------------
# Lazy singletons
# ---------------------------------------------------------------------------

_chroma: Optional[ChromaClient] = None
_gemini: Optional[GeminiClient] = None


def get_chroma() -> ChromaClient:
    global _chroma
    if _chroma is None:
        logger.info("Lazily initializing ChromaClient...")
        _chroma = ChromaClient()
    return _chroma


def get_gemini() -> GeminiClient:
    global _gemini
    if _gemini is None:
        logger.info("Lazily initializing GeminiClient for query endpoint...")
        _gemini = GeminiClient()
    return _gemini


# ---------------------------------------------------------------------------
# GET /api/v1/incidents
# ---------------------------------------------------------------------------

@router.get("/incidents", response_model=IncidentListResponse)
async def list_incidents(
    severity: Optional[str] = Query(None, description="Filter by severity: LOW | MEDIUM | HIGH | CRITICAL"),
    type: Optional[str] = Query(None, description="Filter by crisis type"),
    area: Optional[str] = Query(None, description="Filter by area name"),
    status: Optional[str] = Query(None, description="Filter by status: open | responded | resolved"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Returns a paginated list of incidents.
    ChromaClient now returns normalized dicts, so we just wrap them in Pydantic.
    """
    logger.info(f"GET /incidents severity={severity} type={type} area={area} status={status}")

    chroma = get_chroma()
    filters = {}
    if severity: filters["severity"] = severity.upper()
    if type: filters["type"] = type.lower()
    if area: filters["area_name"] = area
    if status: filters["status"] = status.lower()

    # ChromaClient.query_incidents returns List[dict] already normalized
    rows = chroma.query_incidents(filters=filters or None, limit=limit, offset=offset)
    
    # Convert dicts to Pydantic models
    incidents = [Incident(**r) for r in rows]
    high_count = sum(1 for i in incidents if i.severity in ("HIGH", "CRITICAL"))

    return IncidentListResponse(
        incidents=incidents,
        total=len(incidents),
        high_severity_count=high_count,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/query
# ---------------------------------------------------------------------------

@router.post("/query", response_model=QueryResponse)
async def authority_query(request: QueryRequest):
    """
    Authority chatbot with semantic search.
    """
    logger.info(f"POST /query question='{request.question[:60]}...'")

    chroma = get_chroma()
    search_filters = {}
    if request.filters:
        if request.filters.area: search_filters["area_name"] = request.filters.area
        if request.filters.type: search_filters["type"] = request.filters.type.lower()
        if request.filters.severity: search_filters["severity"] = request.filters.severity.upper()

    results = chroma.semantic_search(
        question=request.question,
        n_results=10,
        filters=search_filters or None,
    )
    supporting_ids = [r["id"] for r in results]
    data_freshness = datetime.now(timezone.utc).isoformat()

    # Build context summary
    context_lines = []
    for i, r in enumerate(results[:5], 1):
        loc = r.get("location", {})
        area = loc.get("area_name", "Unknown")
        context_lines.append(
            f"{i}. [{r.get('type','?').upper()} / {r.get('severity','?')}] {area} — {r.get('source_text','')[:120]}"
        )
    context_block = "\n".join(context_lines) if context_lines else "No matching incidents found."

    if request.use_grounding:
        prompt = (
            "You are CrisisAI Authority Assistant. Answer using ONLY the data below.\n\n"
            f"### INCIDENT DATA:\n{context_block}\n\n"
            f"### QUESTION:\n{request.question}\n\n"
            "Provide a direct answer and a recommended action."
        )
        try:
            gemini = get_gemini()
            llm_answer = gemini.generate(prompt)
        except Exception:
            llm_answer = f"Based on {len(results)} matching incidents:\n{context_block}"

        recommended = ""
        if "recommended" in llm_answer.lower():
            for p in llm_answer.split("\n"):
                if "recommend" in p.lower():
                    recommended = p.strip().lstrip("0123456789.-) ")
                    break
        
        return QueryResponse(
            answer=llm_answer,
            supporting_incidents=supporting_ids,
            recommended_action=recommended or f"Review {len(results)} incidents.",
            data_freshness=data_freshness,
        )
    else:
        return QueryResponse(
            answer=f"Found {len(results)} incident(s).\n\n{context_block}",
            supporting_incidents=supporting_ids,
            recommended_action=f"Review {len(results)} incidents.",
            data_freshness=data_freshness,
        )


# ---------------------------------------------------------------------------
# PATCH /api/v1/incidents/{id}
# ---------------------------------------------------------------------------

@router.patch("/incidents/{incident_id}")
async def patch_incident(incident_id: str, request: Request):
    """
    Updates status and broadcasts via WebSocket.
    Now also writes to Firestore if a session_id is linked to the incident.
    """
    try:
        body_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    status = body_data.get("status")
    authority_note = body_data.get("authority_note") or body_data.get("notes", "")

    chroma = get_chroma()
    existing = chroma.get_incident_by_id(incident_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Incident not found")

    if not status:
        raise HTTPException(status_code=400, detail="Field 'status' is required")

    updates = {"status": status}
    
    firestore_updated = False
    citizen_notified = False

    if chroma.update_incident_metadata(incident_id, updates):
        # Requirements: Get full incident details
        # We need the raw metadata because the normalized model might strip session_id
        session_id = None
        crisis_type = "unknown"
        try:
            raw_res = chroma.collection.get(ids=[incident_id], include=["metadatas"])
            if raw_res and raw_res["metadatas"]:
                meta = raw_res["metadatas"][0]
                session_id = meta.get("session_id")
                crisis_type = meta.get("type", "unknown")
        except Exception as e:
            logger.warning(f"Could not retrieve raw metadata for {incident_id}: {e}")

        if session_id:
            try:
                db = get_firestore_db()
                if db:
                    doc_ref = db.collection("notifications").document(session_id)
                    doc_ref.set({
                        "incident_id": incident_id,
                        "status": status,
                        "message": f"Help is on the way! {authority_note}",
                        "crisis_type": crisis_type,
                        "authority_note": authority_note,
                        "created_at": firestore.SERVER_TIMESTAMP
                    })
                    firestore_updated = True
                    citizen_notified = True
                    logger.info(f"Firestore notification sent to session {session_id}")
                else:
                    logger.error("Firestore DB initialization failed during patch.")
            except Exception as e:
                logger.error(f"Firestore write failed for session {session_id}: {e}")
                # Do not fail the entire request, ChromaDB update is more critical
                firestore_updated = False
                citizen_notified = False
        else:
            logger.warning(f"No session_id for incident {incident_id}, skipping Firestore notification.")
            firestore_updated = False
            citizen_notified = False

        # Broadcast update over WebSocket
        try:
            from backend.app.routers.chat_router import broadcast_status_update
            await broadcast_status_update(incident_id, status)
        except Exception as e:
            logger.warning(f"WebSocket broadcast failed: {e}")

        return {
            "id": incident_id,
            "status": status,
            "updated": True,
            "firestore_updated": firestore_updated,
            "citizen_notified": citizen_notified
        }
    
    raise HTTPException(status_code=500, detail="Update failed")
