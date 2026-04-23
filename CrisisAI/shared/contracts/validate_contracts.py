import json
import sys
from enum import Enum
from typing import List, Optional, Union
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError

# --- Enums ---

class CrisisType(str, Enum):
    FIRE = "fire"
    MEDICAL = "medical"
    FLOOD = "flood"
    EARTHQUAKE = "earthquake"
    SNAKEBITE = "snakebite"
    ACCIDENT = "accident"
    CHEMICAL = "chemical"
    VIOLENCE = "violence"
    UNKNOWN = "unknown"

class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IncidentStatus(str, Enum):
    OPEN = "open"
    RESPONDED = "responded"
    RESOLVED = "resolved"

class SourcePlatform(str, Enum):
    TWITTER = "twitter"
    RSS = "rss"
    MOCK = "mock"
    CITIZEN_APP = "citizen_app"

# --- Shared Models ---

class Location(BaseModel):
    lat: float
    lng: float
    area_name: Optional[str] = None

# --- Contract Models ---

class ChatRequest(BaseModel):
    session_id: str
    query: str
    mode: str
    location: Location
    conversation_state: str
    language_hint: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    response: str
    crisis_type: CrisisType
    severity: Severity
    emergency_numbers: List[str]
    sources: List[str]
    confidence: float = Field(..., ge=0.0, le=1.0)
    next_state: str
    stream: bool

class Incident(BaseModel):
    id: str
    type: CrisisType
    severity: Severity
    location: Location
    source_text: str
    source_platform: SourcePlatform
    classified_at: str  # ISO 8601
    status: IncidentStatus
    confidence: float = Field(..., ge=0.0, le=1.0)

class IncidentSchema(BaseModel):
    incidents: List[Incident]
    total: int
    high_severity_count: int

# --- Validation Logic ---

def validate_json_file(file_path: Path, model: BaseModel):
    print(f"Validating {file_path.name}...", end=" ")
    try:
        if not file_path.exists():
            print(f"FAILED (File not found)")
            return False
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Pydantic V2 uses model_validate
        if hasattr(model, 'model_validate'):
            model.model_validate(data)
        else:
            model.parse_obj(data)
            
        print("PASSED")
        return True
    except json.JSONDecodeError as e:
        print(f"FAILED (JSON Syntax Error: {e})")
    except ValidationError as e:
        print(f"FAILED (Schema Validation Error)")
        print(e)
    except Exception as e:
        print(f"FAILED (Unexpected Error: {type(e).__name__}: {e})")
    return False

def main():
    base_path = Path(__file__).parent
    
    validations = [
        ("chat_request.json", ChatRequest),
        ("chat_response.json", ChatResponse),
        ("incident_schema.json", IncidentSchema),
    ]
    
    all_passed = True
    print("\n--- CrisisAI API Contract Validation ---\n")
    
    for filename, model in validations:
        file_path = base_path / filename
        if not validate_json_file(file_path, model):
            all_passed = False
            
    print("\n" + "="*40)
    if all_passed:
        print("SUMMARY: All critical contracts are VALID.")
        sys.exit(0)
    else:
        print("SUMMARY: Some contracts FAILED validation.")
        sys.exit(1)

if __name__ == "__main__":
    main()
