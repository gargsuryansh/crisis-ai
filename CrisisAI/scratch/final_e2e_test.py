import requests
import json
import time
import websockets
import asyncio

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/api/v1/ws"

def run_test(name, func, *args, **kwargs):
    print(f"\n--- RUNNING: {name} ---")
    try:
        result = func(*args, **kwargs)
        print(f"[PASS] {name}")
        return result
    except Exception as e:
        print(f"[FAIL] {name} | Error: {e}")
        return None

# --- Test Functions ---

def test_health():
    r = requests.get(f"{BASE_URL}/health")
    r.raise_for_status()
    data = r.json()
    assert data["status"] == "ok"
    assert data["react_dashboard"] is True
    return data

def test_chat_snakebite():
    payload = {
        "session_id": "e2e_test_user_123",
        "query": "snake bite help",
        "mode": "online", "location": {}, "conversation_state": "INTAKE"
    }
    r = requests.post(f"{BASE_URL}/api/v1/chat", json=payload)
    r.raise_for_status()
    data = r.json()
    assert data["crisis_type"] == "snakebite"
    assert len(data["sources"]) > 0
    return data

def test_get_incidents():
    r = requests.get(f"{BASE_URL}/api/v1/incidents?limit=1")
    r.raise_for_status()
    data = r.json()
    assert "incidents" in data and len(data["incidents"]) > 0
    return data["incidents"][0]

def test_patch_incident(incident_id):
    payload = {"status": "responded", "authority_note": "E2E Test: Unit Dispatched"}
    r = requests.patch(f"{BASE_URL}/api/v1/incidents/{incident_id}", json=payload)
    r.raise_for_status()
    data = r.json()
    assert data["status"] == "responded"
    assert data["firestore_updated"] in (True, False)
    return data

async def test_websocket_push():
    print("Connecting to WebSocket to listen for live incident...")
    try:
        async with websockets.connect(WS_URL, open_timeout=5) as ws:
            print("WS connected. Waiting for message...")
            # Generate a new incident in a separate process/thread would be ideal
            # For this simple test, we assume the server might send a ping
            msg = await asyncio.wait_for(ws.recv(), timeout=35.0)
            print("Received a message, WS is likely working:", msg)
            assert "event" in json.loads(msg)
            return msg
    except asyncio.TimeoutError:
        raise RuntimeError("Did not receive any WebSocket message (ping or incident) within 35 seconds.")

# --- Main Runner ---

if __name__ == "__main__":
    print("====== CrisisAI Final Integration Test ======")
    
    run_test("Health Check", test_health)
    run_test("Citizen Chat (Snakebite)", test_chat_snakebite)
    incident = run_test("Get Incidents List", test_get_incidents)
    
    if incident:
        run_test(f"PATCH Incident '{incident['id']}'", test_patch_incident, incident['id'])
    
    # WebSocket test
    try:
        print("\n--- RUNNING: WebSocket Test ---")
        asyncio.run(test_websocket_push())
        print("[PASS] WebSocket Test")
    except Exception as e:
        print(f"[FAIL] WebSocket Test | Error: {e}")

    print("\n====== Integration Test Complete ======")
    print("NOTE: For full WS push test, generate a mock incident while the test is running.")
