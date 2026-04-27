import sys
import os
import requests
import json
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

# Load .env manually for the script if needed
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from backend.scrapers.chroma_ingest import ingest_incident

def test():
    print("--- STEP 1: Ingesting incident with session_id ---")
    metadata = {
        "type": "fire",
        "severity": "HIGH",
        "status": "open",
        "lat": "28.6139",
        "lng": "77.2090",
        "area_name": "New Delhi",
        "session_id": "test_session_789", # Unique session for this test
        "source": "citizen_app"
    }
    text = f"Emergency: Fire at New Delhi station. (Test ID: {int(Path(__file__).stat().st_mtime)})"
    incident_id = ingest_incident(text, metadata)
    
    if incident_id in ("ERROR", "DUPLICATE"):
        print(f"Failed to ingest or duplicate: {incident_id}")
        # If duplicate, we can still try to patch it if we know the ID, 
        # but let's try to make it unique.
        if incident_id == "DUPLICATE":
            # Just search for it? No, let's just use a timestamp.
            pass
        else:
            return

    print(f"Ingested incident ID: {incident_id}")

    print("\n--- STEP 2: Patching the incident via API ---")
    url = f"http://localhost:8000/api/v1/incidents/{incident_id}"
    payload = {
        "status": "responded",
        "authority_note": "Fire brigade dispatched, ETA 5 minutes. (Automated Test)"
    }
    
    try:
        response = requests.patch(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test()
