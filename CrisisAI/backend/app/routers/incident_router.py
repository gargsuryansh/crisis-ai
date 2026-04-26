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
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

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

@router.patch("/incidents/{incident_id}", response_model=IncidentPatchResponse)
async def patch_incident(incident_id: str, body: IncidentPatchRequest):
    """
    Updates status and broadcasts via WebSocket.
    """
    chroma = get_chroma()
    existing = chroma.get_incident_by_id(incident_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Incident not found")

    updates = {}
    if body.status: updates["status"] = body.status
    if not updates: raise HTTPException(status_code=400, detail="No fields to update")

    if chroma.update_incident_metadata(incident_id, updates):
        try:
            from backend.app.routers.chat_router import broadcast_status_update
            await broadcast_status_update(incident_id, body.status)
        except Exception:
            pass
        return IncidentPatchResponse(id=incident_id, status=body.status, updated=True)
    
    raise HTTPException(status_code=500, detail="Update failed")
