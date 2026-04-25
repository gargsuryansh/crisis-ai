import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

import numpy as np
import faiss
import google.generativeai as genai

# Setup logger
logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        """
        Initialize the RAG Service by loading the FAISS index, metadata, and protocols.
        """
        # Load environment variables or use defaults
        self.index_path = Path(os.getenv("FAISS_INDEX_PATH", "data/embeddings/faiss_index_3072.bin"))
        self.metadata_path = Path(os.getenv("FAISS_METADATA_PATH", "data/embeddings/metadata_3072.json"))
        self.protocols_path = Path(os.getenv("PROTOCOLS_JSON_PATH", "data/protocols/emergency_protocols_enhanced.json"))

        # Load FAISS index
        if not self.index_path.exists():
            raise RuntimeError(f"FAISS index file missing at: {self.index_path}")
        
        try:
            self.index = faiss.read_index(str(self.index_path))
            self.dimension = self.index.d
            logger.info(f"Loaded FAISS index with dimension {self.dimension} and {self.index.ntotal} vectors.")
        except Exception as e:
            raise RuntimeError(f"Failed to load FAISS index: {str(e)}")

        # Load metadata
        if not self.metadata_path.exists():
            raise RuntimeError(f"Metadata file missing at: {self.metadata_path}")
        
        try:
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            
            if len(self.metadata) != self.index.ntotal:
                raise RuntimeError(f"Metadata count ({len(self.metadata)}) does not match index total ({self.index.ntotal})")
        except Exception as e:
            raise RuntimeError(f"Failed to load metadata: {str(e)}")

        # Load protocols
        if not self.protocols_path.exists():
            raise RuntimeError(f"Protocols JSON file missing at: {self.protocols_path}")
        
        try:
            with open(self.protocols_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                protocols_list = data.get("protocols", [])
                self.protocols_by_id = {str(p["id"]): p for p in protocols_list}
            logger.info(f"Loaded {len(self.protocols_by_id)} protocols from {self.protocols_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to load protocols: {str(e)}")

        # Configure Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is missing")
        genai.configure(api_key=api_key)
        self.embedding_model = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001")

        logger.info("RAGService initialization successful.")

    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for the query using Gemini.
        """
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=query,
                task_type="retrieval_query"
            )
            
            embedding = result.get("embedding")
            if embedding is None:
                raise ValueError("Gemini API returned no embedding content.")
            
            # Convert to numpy array and reshape
            vector = np.array(embedding, dtype=np.float32).reshape(1, -1)
            
            # Verify dimension
            if vector.shape[1] != self.dimension:
                raise ValueError(f"Query embedding dimension mismatch: expected {self.dimension}, got {vector.shape[1]}")
            
            return vector
        except Exception as e:
            logger.error(f"Error generating query embedding: {str(e)}")
            raise

    def _normalize_crisis_type(self, value: str) -> str:
        """Normalizes crisis type strings for robust comparison."""
        return value.lower().replace("_", "").replace("-", "").strip() if value else ""

    def _flatten_avoid(self, items) -> List[str]:
        """Converts mixed string/dict avoid items into a list of plain strings."""
        out = []
        if not items:
            return out
        for it in items:
            if isinstance(it, str):
                out.append(it)
            elif isinstance(it, dict):
                action = it.get("action")
                if action:
                    out.append(action)
        return out

    async def retrieve(self, query: str, crisis_type: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant protocols for the given query.
        """
        # Embed the query
        query_vector = self.embed_query(query)
        
        # Search FAISS with overfetch
        search_k = min(max(top_k * 5, top_k), self.index.ntotal)
        distances, indices = self.index.search(query_vector, search_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1: continue # FAISS returns -1 if not enough results
            
            meta = self.metadata[idx]
            protocol_id = str(meta.get("id"))
            
            protocol = self.protocols_by_id.get(protocol_id)
            if not protocol:
                logger.warning(f"Protocol ID {protocol_id} found in index but missing in protocols map.")
                continue

            # Process steps
            steps_data = protocol.get("steps", [])
            extracted_steps = []
            if isinstance(steps_data, list):
                for step in steps_data:
                    if isinstance(step, dict):
                        extracted_steps.append(step.get("action", ""))
                    elif isinstance(step, str):
                        extracted_steps.append(step)
            
            # Handle emergency numbers (support both singular and plural)
            emergency_numbers = protocol.get("emergency_numbers", [])
            if not emergency_numbers:
                single_number = protocol.get("emergency_number")
                if single_number:
                    emergency_numbers = [single_number] if isinstance(single_number, str) else single_number
            
            if not isinstance(emergency_numbers, list):
                emergency_numbers = [str(emergency_numbers)]

            # Normalize what_to_avoid
            flattened_avoid = self._flatten_avoid(protocol.get("what_to_avoid", []))

            # Construct result dict
            result_dict = {
                "chunk_id": protocol_id,
                "id": protocol_id,
                "crisis_type": protocol.get("crisis_type", "general"),
                "severity": protocol.get("severity", "medium"),
                "title": protocol.get("title", ""),
                "situation": protocol.get("situation", ""),
                "content": protocol.get("content", ""),
                "steps": extracted_steps,
                "what_to_avoid": flattened_avoid,
                "emergency_numbers": emergency_numbers,
                "source": protocol.get("source", []),
                "tags": protocol.get("tags", []),
                "distance": float(dist),
            }

            # Build readable context string
            text_context = [
                f"Title: {result_dict['title']}",
                f"Situation: {result_dict['situation']}",
                f"Content: {result_dict['content']}",
                "Steps:"
            ]
            for i, step in enumerate(extracted_steps, 1):
                text_context.append(f"{i}. {step}")
            
            text_context.append("What to avoid:")
            for avoid in flattened_avoid:
                text_context.append(f"- {avoid}")
            
            text_context.append(f"Emergency numbers: {', '.join(map(str, emergency_numbers))}")
            text_context.append(f"Source: {result_dict['source']}")
            
            result_dict["text"] = "\n".join(text_context)
            results.append(result_dict)

        # Filtering logic with normalized crisis_type
        final_results = []
        if crisis_type:
            target_type = self._normalize_crisis_type(crisis_type)
            final_results = [r for r in results if self._normalize_crisis_type(r["crisis_type"]) == target_type]
            logger.info(f"Filtered {len(final_results)} results for crisis_type: {crisis_type} (normalized: {target_type})")

        # Fallback to unfiltered if filtered count is 0
        if not final_results:
            final_results = results[:top_k]
        else:
            final_results = final_results[:top_k]

        logger.info(f"Returning {len(final_results)} retrieval results for query: '{query[:50]}...'")
        return final_results
