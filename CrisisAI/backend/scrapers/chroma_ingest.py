import chromadb
import os
import time
import logging
from hashlib import md5
from typing import Dict, Any, Optional

# Setup logging
logger = logging.getLogger(__name__)

# Configuration
# NEVER use /tmp — Cloud Run resets /tmp on every restart, which would wipe the database.
CHROMA_PERSIST_DIR = os.getenv('CHROMA_PERSIST_DIR', './chroma_db')

try:
    # Create ChromaDB PersistentClient
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    # Get or create collection
    # Collection name 'incidents' EXACT lowercase — must match chroma_client.py
    collection = client.get_or_create_collection(
        name='incidents',
        metadata={'hnsw:space': 'cosine'}
    )
except Exception as e:
    logger.error(f"Failed to initialize ChromaDB: {e}")
    collection = None

def ingest_incident(text: str, metadata: Dict[str, Any]) -> str:
    """
    Ingests an incident document into ChromaDB.
    Ensures all metadata values are strings and checks for duplicates.
    """
    if collection is None:
        logger.error("Cannot ingest: ChromaDB collection is not initialized.")
        return "ERROR"

    try:
        # ALL ChromaDB metadata values MUST be strings — silent empty results otherwise
        safe_meta = {k: str(v) for k, v in metadata.items()}

        # Generate unique document ID based on text hash and timestamp
        doc_id = f"incident_{md5(text.encode()).hexdigest()[:8]}_{int(time.time())}"

        # Deduplication check: check if a very similar document already exists
        existing = collection.query(query_texts=[text], n_results=1)
        if existing['distances'] and len(existing['distances'][0]) > 0:
            distance = existing['distances'][0][0]
            if distance < 0.15:
                logger.info(f"Duplicate detected (distance={distance:.4f}) for: {text[:50]}...")
                return 'DUPLICATE'

        # Add to collection
        collection.add(
            documents=[text],
            metadatas=[safe_meta],
            ids=[doc_id]
        )

        logger.info(f"Ingested incident: {doc_id} | type={safe_meta.get('type', 'unknown')}")

        # TODO (Day 3): Call broadcast_incident() for React WebSocket live push
        # asyncio.run(broadcast_new_incident({'id': doc_id, **safe_meta, 'source_text': text}))

        return doc_id

    except Exception as e:
        logger.error(f"Error ingesting incident: {e}")
        return "ERROR"

def get_collection_stats() -> dict:
    """Returns basic statistics about the incidents collection."""
    if collection is None:
        return {"error": "Collection not initialized"}
    
    return {
        "total_count": collection.count(),
        "collection_name": 'incidents',
        "persist_dir": CHROMA_PERSIST_DIR
    }

def query_incidents_by_type(crisis_type: str, limit: int = 10) -> list:
    """
    Queries ChromaDB for incidents of a specific type.
    Use 'all' to query without a type filter.
    """
    if collection is None:
        return []

    try:
        results = collection.query(
            query_texts=[crisis_type],
            n_results=limit,
            where={"type": crisis_type} if crisis_type != "all" else None
        )
        return results
    except Exception as e:
        logger.error(f"Error querying incidents: {e}")
        return []
