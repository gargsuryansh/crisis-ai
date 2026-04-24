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

def build_index_768(protocols: List[Dict[str, Any]]):
    """
    Builds a 768-dimensional FAISS index using Google text-embedding-004 API.
    Saves index and metadata to data/embeddings/.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables. Skipping 768-dim index.")
        return

    genai.configure(api_key=api_key)
    
    embeddings_list = []
    metadata_list = []
    
    logger.info(f"Generating 768-dim embeddings for {len(protocols)} protocols using Google API...")
    
    for i, protocol in enumerate(protocols):
        text = prepare_embedding_text(protocol)
        
        # Retry logic
        success = False
        for attempt in range(3):  # Original + 2 retries
            try:
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings_list.append(result['embedding'])
                metadata_list.append(extract_metadata(protocol))
                success = True
                break
            except Exception as e:
                logger.warning(f"Attempt {attempt+1} failed for protocol {protocol.get('id')}: {e}")
                time.sleep(2)  # Wait before retry
        
        if not success:
            logger.error(f"Skipping protocol {protocol.get('id')} after 3 failed attempts.")
            continue
            
        # Progress logging
        if (i + 1) % 50 == 0:
            logger.info(f"Progress: {i + 1}/{len(protocols)} protocols embedded.")
        
        # Rate limiting sleep
        time.sleep(0.5)

    if not embeddings_list:
        logger.error("No embeddings generated for 768-dim index.")
        return

    # Convert to float32
    embeddings = np.array(embeddings_list).astype('float32')
    
    # Create FAISS index
    dimension = 768
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    
    # Save paths
    data_index_path = "data/embeddings/faiss_index_768.bin"
    data_meta_path = "data/embeddings/metadata_768.json"
    
    # Save to data/
    faiss.write_index(index, data_index_path)
    with open(data_meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata_list, f, indent=2)
    
    logger.info(f"FAISS 768-dim: {index.ntotal} vectors saved to {data_index_path}")

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
    
    # Build 768-dim (API, slower)
    print("\nBuilding 768-dim index (Google text-embedding-004)...")
    print("[WARNING] This requires GEMINI_API_KEY and will take 20-40 minutes due to rate limits")
    
    # Check if we are in an interactive environment for input
    try:
        answer = input("Proceed? (y/n): ")
        if answer.lower() == 'y':
            build_index_768(protocols)
            print("DONE: 768-dim index complete")
        else:
            print("SKIP: 768-dim index")
    except EOFError:
        print("SKIP: 768-dim index (non-interactive session)")
    
    print("\n=== All indexes built ===")
