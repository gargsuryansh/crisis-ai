import os
import json
import time
import shutil
import logging
import asyncio
import numpy as np
import faiss
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("crisisai.faiss_builder")

# Load environment variables
load_dotenv()

def prepare_embedding_text(protocol: Dict[str, Any]) -> str:
    """Combines protocol fields into a single string for embedding."""
    title = protocol.get("title", "")
    situation = protocol.get("situation", "")
    content = protocol.get("content", "")
    steps = protocol.get("steps", [])
    actions = " ".join([s.get("action", "") for s in steps])
    tags = " ".join(protocol.get("tags", []))
    
    return f"{title} {situation} {content} {actions} {tags}".strip()

def extract_metadata(protocol: Dict[str, Any]) -> Dict[str, str]:
    """Extracts required metadata from a protocol object, ensuring all values are strings."""
    return {
        "id": str(protocol.get("id", "")),
        "crisis_type": str(protocol.get("crisis_type", "")),
        "severity": str(protocol.get("severity", "")),
        "title": str(protocol.get("title", "")),
        "source": str(protocol.get("source", "unknown")),
        "timestamp": str(protocol.get("last_updated", "unknown"))
    }

def build_index_384(protocols: List[Dict[str, Any]]):
    """
    Builds a 384-dimensional FAISS index using sentence-transformers/all-MiniLM-L6-v2.
    Saves index and metadata to data/embeddings/ and mobile/assets/faiss_index/.
    """
    logger.info("Initializing SentenceTransformer(all-MiniLM-L6-v2)...")
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    
    texts = []
    metadata_list = []
    
    for protocol in protocols:
        texts.append(prepare_embedding_text(protocol))
        metadata_list.append(extract_metadata(protocol))
    
    logger.info(f"Generating 384-dim embeddings for {len(texts)} protocols...")
    embeddings = model.encode(texts, show_progress_bar=True)
    
    # Convert to float32 (FAISS requirement)
    embeddings = np.array(embeddings).astype('float32')
    
    # Create FAISS index
    dimension = 384
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    # Save paths
    data_index_path = "data/embeddings/faiss_index_384.bin"
    data_meta_path = "data/embeddings/metadata_384.json"
    mobile_index_path = "mobile/assets/faiss_index/faiss_index_384.bin"
    mobile_meta_path = "mobile/assets/faiss_index/metadata_384.json"
    
    # Save to data/
    faiss.write_index(index, data_index_path)
    with open(data_meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata_list, f, indent=2)
    
    # Copy to mobile/
    shutil.copy2(data_index_path, mobile_index_path)
    shutil.copy2(data_meta_path, mobile_meta_path)
    
    logger.info(f"FAISS 384-dim: {index.ntotal} vectors saved to {data_index_path} and mobile assets.")

def build_index_3072(protocols: List[Dict[str, Any]]):
    """
    Builds a 3072-dimensional FAISS index using Google gemini-embedding-001 API with batching.
    Saves index and metadata to data/embeddings/.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables. Skipping 3072-dim index.")
        return

    genai.configure(api_key=api_key)
    
    # Build all texts and metadata upfront
    all_texts = [prepare_embedding_text(p) for p in protocols]
    all_metadata = [extract_metadata(p) for p in protocols]
    
    dimension = 3072
    index = faiss.IndexFlatL2(dimension)
    final_metadata = []
    
    batch_size = 90  # Free-tier safe limit (100/min)
    num_batches = (len(all_texts) + batch_size - 1) // batch_size
    
    logger.info(f"Generating 3072-dim embeddings for {len(protocols)} protocols in {num_batches} batches (Rate-limit safe mode)...")
    
    for i in range(num_batches):
        start_idx = i * batch_size
        end_idx = min((i + 1) * batch_size, len(all_texts))
        
        batch_texts = all_texts[start_idx:end_idx]
        batch_meta = all_metadata[start_idx:end_idx]
        
        logger.info(f"Processing batch {i+1}/{num_batches} (protocols {start_idx}-{end_idx-1})...")
        
        try:
            # Using models/gemini-embedding-001 for 3072-dim vectors
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=batch_texts,
                task_type="retrieval_document"
            )
            
            # Robust parsing for google-generativeai embed_content responses
            emb_list = None

            if isinstance(result, dict):
                if "embedding" in result and isinstance(result["embedding"], list):
                    if result["embedding"] and isinstance(result["embedding"][0], (int, float)):
                        emb_list = [result["embedding"]]  # single vector
                    elif result["embedding"] and isinstance(result["embedding"][0], list):
                        emb_list = result["embedding"]    # list of vectors
                elif "embeddings" in result:
                    emb_list = result["embeddings"]

            elif isinstance(result, list):
                if result and isinstance(result[0], dict) and "embedding" in result[0]:
                    emb_list = [r["embedding"] for r in result]

            if emb_list is None:
                raise ValueError(f"Unexpected embed_content response format: {type(result)} | {str(result)[:200]}")

            batch_embeddings = np.array(emb_list, dtype="float32")

            # Dimension mismatch safety check
            if batch_embeddings.ndim == 1:
                batch_embeddings = batch_embeddings.reshape(1, -1)

            if batch_embeddings.shape[1] != dimension:
                raise ValueError(f"Embedding dimension mismatch: expected {dimension}, got {batch_embeddings.shape[1]}")

            # Add all vectors from the batch to FAISS at once
            index.add(batch_embeddings)
            
            # Keep track of metadata for successful batches
            final_metadata.extend(batch_meta)
            
        except Exception as e:
            logger.error(f"Error processing batch {i+1}: {e}")
            # Skip this batch and continue
            continue
            
        # Rate limiting sleep between batches (Free-tier safe)
        logger.info("Sleeping 65 seconds to respect free-tier rate limits...")
        time.sleep(65)

    if index.ntotal == 0:
        logger.error("No embeddings were successfully generated for 3072-dim index.")
        return

    # Save paths
    data_index_path = "data/embeddings/faiss_index_3072.bin"
    data_meta_path = "data/embeddings/metadata_3072.json"
    
    # Save index and metadata
    try:
        faiss.write_index(index, data_index_path)
        with open(data_meta_path, 'w', encoding='utf-8') as f:
            json.dump(final_metadata, f, indent=2)
        
        logger.info(f"FAISS 3072-dim: {index.ntotal} vectors saved to {data_index_path}")
    except Exception as e:
        logger.error(f"Failed to save 3072-dim index or metadata: {e}")

if __name__ == "__main__":
    print("=== CrisisAI FAISS Index Builder ===")
    
    json_path = 'data/protocols/emergency_protocols_enhanced.json'
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Input JSON not found at {json_path}")

    # Load JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    protocols = data.get('protocols', [])
    print(f"Loaded {len(protocols)} protocols")
    
    # Build 384-dim (local, fast)
    print("\nBuilding 384-dim index (sentence-transformers)...")
    try:
        build_index_384(protocols)
    except Exception as e:
        logger.error(f"Failed to build 384-dim index: {e}", exc_info=True)
    
    # Build 3072-dim (API, slower)
    print("\nBuilding 3072-dim index (Google gemini-embedding-001)...")
    print("[WARNING] This requires GEMINI_API_KEY and will take 20-40 minutes due to rate limits")
    
    # Check if we are in an interactive environment for input
    try:
        answer = input("Proceed? (y/n): ")
        if answer.lower() == 'y':
            build_index_3072(protocols)
            print("DONE: 3072-dim index complete")
        else:
            print("SKIP: 3072-dim index")
    except EOFError:
        print("SKIP: 3072-dim index (non-interactive session)")
    
    print("\n=== All indexes built ===")
