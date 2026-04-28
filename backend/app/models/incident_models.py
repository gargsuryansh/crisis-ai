"""
CrisisAI Incident & Query Pydantic Models
Matches shared/contracts/incident_schema.json, query_request.json, query_response.json
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Incident models  (GET /api/v1/incidents, PATCH /api/v1/incidents/{id})
# ---------------------------------------------------------------------------

class IncidentLocation(BaseModel):
    lat: float
    lng: float
    area_name: str


class Incident(BaseModel):
    """Single incident object matching incident_schema.json."""
    id: str
    type: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    location: IncidentLocation
    source_text: str
    source_platform: Literal["twitter", "rss", "mock", "citizen_app"]
    classified_at: str
    status: Literal["open", "responded", "resolved"]
    confidence: float


class IncidentListResponse(BaseModel):
    """Response for GET /api/v1/incidents."""
    incidents: List[Incident]
    total: int
    high_severity_count: int = 0


class IncidentPatchRequest(BaseModel):
    """Body for PATCH /api/v1/incidents/{id}."""
    status: Optional[Literal["open", "responded", "resolved"]] = None
    notes: Optional[str] = None


class IncidentPatchResponse(BaseModel):
    """Response for PATCH /api/v1/incidents/{id}."""
    id: str
    status: str
    updated: bool


# ---------------------------------------------------------------------------
# Authority query models  (POST /api/v1/query)
# ---------------------------------------------------------------------------

class QueryFilters(BaseModel):
    area: Optional[str] = None
    type: Optional[str] = None
    severity: Optional[str] = None


class QueryRequest(BaseModel):
    """Matches shared/contracts/query_request.json."""
    question: str
    filters: Optional[QueryFilters] = None
    use_grounding: bool = False
    stream: bool = False


class QueryResponse(BaseModel):
    """Matches shared/contracts/query_response.json."""
    answer: str
    supporting_incidents: List[str] = Field(default_factory=list)
    recommended_action: str = ""
    data_freshness: str = ""
