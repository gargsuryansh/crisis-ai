"""
CrisisAI ChromaDB Client
Provides structured access to the 'incidents' collection for authority endpoints.

Contract: shared/contracts/chroma_schema.md
  - Collection name: 'incidents' (lowercase, exact)
  - ALL metadata values stored in ChromaDB MUST be strings
  - CHROMA_PERSIST_DIR must be './chroma_db' (never /tmp)
"""

import os
import re
import logging
import json
from typing import Dict, List, Optional, Any

import chromadb
from chromadb.config import Settings

from backend.app import config

logger = logging.getLogger("crisisai.chroma_client")


class ChromaClient:
    """
    Singleton-style ChromaDB client for the 'incidents' collection.
    Used by incident_router for authority dashboard endpoints.
    """

    def __init__(self):
        persist_dir = config.CHROMA_PERSIST_DIR
        logger.info(f"Initializing ChromaDB PersistentClient at: {persist_dir}")

        # Silence ChromaDB telemetry warnings
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.collection = self.client.get_or_create_collection(
            name="incidents",
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"ChromaDB collection 'incidents' ready. "
            f"Document count: {self.collection.count()}"
        )

    # ------------------------------------------------------------------
    # Normalization Helpers
    # ------------------------------------------------------------------

    def _build_location_from_metadata(self, metadata: dict) -> dict:
        """
        Extracts and normalizes location data from metadata.
        Supports flat keys (lat, lng, area_name) and legacy stringified formats.
        """
        lat = 0.0
        lng = 0.0
        area_name = "Unknown"

        # 1. Check for flat keys (Preferred)
        if all(k in metadata for k in ["lat", "lng", "area_name"]):
            try:
                return {
                    "lat": float(metadata["lat"]),
                    "lng": float(metadata["lng"]),
                    "area_name": str(metadata["area_name"])
                }
            except (ValueError, TypeError):
                pass

        # 2. Check for legacy stringified 'location' field
        loc_str = metadata.get("location")
        if loc_str and isinstance(loc_str, str):
            # Handle format: @{lat=28.646678; lng=77.258592; area_name=Delhi}
            if loc_str.startswith("@{"):
                lat_match = re.search(r"lat=([-+]?\d*\.\d+|\d+)", loc_str)
                lng_match = re.search(r"lng=([-+]?\d*\.\d+|\d+)", loc_str)
                area_match = re.search(r"area_name=([^;}\n]+)", loc_str)
                
                if lat_match: lat = float(lat_match.group(1))
                if lng_match: lng = float(lng_match.group(1))
                if area_match: area_name = area_match.group(1).strip()
                return {"lat": lat, "lng": lng, "area_name": area_name}

            # Handle format: {'lat': 28.646678, 'lng': 77.258592, 'area_name': 'Delhi'}
            if loc_str.startswith("{"):
                try:
                    # Try json.loads if it's valid JSON
                    clean_json = loc_str.replace("'", '"')
                    data = json.loads(clean_json)
                    return {
                        "lat": float(data.get("lat", 0.0)),
                        "lng": float(data.get("lng", 0.0)),
                        "area_name": str(data.get("area_name", "Unknown"))
                    }
                except Exception:
                    # Fallback to regex if JSON parsing fails
                    lat_match = re.search(r"['\"]lat['\"]:\s*([-+]?\d*\.\d+|\d+)", loc_str)
                    lng_match = re.search(r"['\"]lng['\"]:\s*([-+]?\d*\.\d+|\d+)", loc_str)
                    area_match = re.search(r"['\"]area_name['\"]:\s*['\"]([^'\"]+)['\"]", loc_str)
                    
                    if lat_match: lat = float(lat_match.group(1))
                    if lng_match: lng = float(lng_match.group(1))
                    if area_match: area_name = area_match.group(1).strip()
                    return {"lat": lat, "lng": lng, "area_name": area_name}

        return {"lat": lat, "lng": lng, "area_name": area_name}

    def _metadata_to_incident(self, doc_id: str, document: str, metadata: dict) -> dict:
        """
        Converts a ChromaDB result (id, document, metadata) into a 
        normalized incident dictionary matching the Section 3 contract.
        """
        location = self._build_location_from_metadata(metadata)
        
        return {
            "id": doc_id,
            "type": str(metadata.get("type", "unknown")),
            "severity": str(metadata.get("severity", "LOW")),
            "location": location,
            "source_text": document,
            "source_platform": str(metadata.get("source", metadata.get("source_platform", "mock"))),
            "classified_at": str(metadata.get("timestamp", metadata.get("classified_at", ""))),
            "status": str(metadata.get("status", "open")),
            "confidence": float(metadata.get("confidence", 0.0))
        }

    # ------------------------------------------------------------------
    # Query by metadata filters  (GET /api/v1/incidents)
    # ------------------------------------------------------------------

    def query_incidents(
        self,
        filters: Optional[Dict[str, str]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves incidents from ChromaDB using optional metadata filters.
        Returns a list of dicts matching the Incident contract.
        """
        try:
            where_clause = self._build_where(filters)

            results = self.collection.get(
                where=where_clause,
                limit=limit,
                offset=offset,
                include=["documents", "metadatas"],
            )

            if not results or not results.get("ids"):
                return []

            docs = []
            for i, doc_id in enumerate(results["ids"]):
                meta = results["metadatas"][i] if results.get("metadatas") else {}
                doc_text = results["documents"][i] if results.get("documents") else ""
                docs.append(self._metadata_to_incident(doc_id, doc_text, meta))
            return docs

        except Exception:
            logger.exception("query_incidents failed")
            return []

    # ------------------------------------------------------------------
    # Semantic search  (POST /api/v1/query)
    # ------------------------------------------------------------------

    def semantic_search(
        self,
        question: str,
        n_results: int = 10,
        filters: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Runs a semantic search and returns normalized incident dicts.
        """
        try:
            where_clause = self._build_where(filters)

            results = self.collection.query(
                query_texts=[question],
                n_results=n_results,
                where=where_clause,
                include=["documents", "metadatas", "distances"],
            )

            if not results or not results.get("ids") or not results["ids"][0]:
                return []

            docs = []
            ids = results["ids"][0]
            documents = results["documents"][0] if results.get("documents") else []
            metadatas = results["metadatas"][0] if results.get("metadatas") else []
            distances = results["distances"][0] if results.get("distances") else []

            for i, doc_id in enumerate(ids):
                meta = metadatas[i] if i < len(metadatas) else {}
                doc_text = documents[i] if i < len(documents) else ""
                dist = distances[i] if i < len(distances) else None
                
                entry = self._metadata_to_incident(doc_id, doc_text, meta)
                if dist is not None:
                    entry["distance"] = dist
                docs.append(entry)
            return docs

        except Exception:
            logger.exception("semantic_search failed")
            return []

    # ------------------------------------------------------------------
    # Single-document fetch  (PATCH helper)
    # ------------------------------------------------------------------

    def get_incident_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single normalized incident by its ID."""
        try:
            results = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"],
            )
            if not results or not results.get("ids"):
                return None
                
            return self._metadata_to_incident(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0]
            )
        except Exception:
            logger.exception(f"get_incident_by_id failed for {doc_id}")
            return None

    # ------------------------------------------------------------------
    # Update metadata  (PATCH /api/v1/incidents/{id})
    # ------------------------------------------------------------------

    def update_incident_metadata(
        self, doc_id: str, updates: Dict[str, str]
    ) -> bool:
        """
        Updates metadata fields for an existing incident document.
        ALL values are coerced to strings per the Chroma schema contract.
        """
        try:
            # Ensure string values
            safe_updates = {k: str(v) for k, v in updates.items()}
            self.collection.update(ids=[doc_id], metadatas=[safe_updates])
            logger.info(f"Updated incident {doc_id}: {safe_updates}")
            return True
        except Exception:
            logger.exception(f"update_incident_metadata failed for {doc_id}")
            return False

    def count(self) -> int:
        return self.collection.count()

    @staticmethod
    def _build_where(filters: Optional[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        if not filters:
            return None
        clauses = {k: v for k, v in filters.items() if v}
        if not clauses:
            return None
        if len(clauses) == 1:
            key, val = next(iter(clauses.items()))
            return {key: val}
        return {"$and": [{k: v} for k, v in clauses.items()]}
