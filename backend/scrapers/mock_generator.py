import random
import time
import logging
from datetime import datetime, timezone, timedelta
from backend.scrapers.chroma_ingest import ingest_incident, get_collection_stats

# Setup logging
logger = logging.getLogger(__name__)

INDIAN_CITIES = [
    {"name": "Mumbai", "lat": 19.076, "lng": 72.877},
    {"name": "Delhi", "lat": 28.613, "lng": 77.209},
    {"name": "Chennai", "lat": 13.082, "lng": 80.270},
    {"name": "Kolkata", "lat": 22.572, "lng": 88.363},
    {"name": "Hyderabad", "lat": 17.385, "lng": 78.486},
    {"name": "Pune", "lat": 18.520, "lng": 73.856},
    {"name": "Jaipur", "lat": 26.912, "lng": 75.787},
    {"name": "Bhopal", "lat": 23.259, "lng": 77.412},
    {"name": "Lucknow", "lat": 26.846, "lng": 80.946},
    {"name": "Ahmedabad", "lat": 23.022, "lng": 72.571},
    {"name": "Nagpur", "lat": 21.145, "lng": 79.088},
    {"name": "Indore", "lat": 22.719, "lng": 75.857},
]

INCIDENT_TEMPLATES = [
    {
        "type": "fire",
        "severity": "HIGH",
        "templates": [
            "Major fire reported at {city} central market. Multiple shops engulfed in flames. Fire brigade en route.",
            "Residential building fire in {city} suburb. Residents being evacuated. Smoke visible from 2km away."
        ],
        "source_platform": "mock"
    },
    {
        "type": "flood",
        "severity": "HIGH",
        "templates": [
            "Heavy waterlogging reported in {city} after overnight rainfall. Several roads submerged.",
            "Flood warning issued for {city} low-lying areas. Water level rising rapidly in local river."
        ],
        "source_platform": "rss"
    },
    {
        "type": "medical",
        "severity": "MEDIUM",
        "templates": [
            "Mass food poisoning reported at {city} wedding. Over 50 people hospitalized.",
            "Heatstroke cases surging in {city}. 15 people admitted to district hospital today."
        ],
        "source_platform": "twitter"
    },
    {
        "type": "accident",
        "severity": "CRITICAL",
        "templates": [
            "Major road accident on {city} highway. Bus collided with truck. Multiple casualties reported.",
            "Building collapse in {city} old city area. Rescue operations underway."
        ],
        "source_platform": "twitter"
    },
    {
        "type": "chemical",
        "severity": "HIGH",
        "templates": [
            "Gas leak reported at {city} industrial area. Residents in 1km radius being evacuated."
        ],
        "source_platform": "rss"
    },
    {
        "type": "snakebite",
        "severity": "HIGH",
        "templates": [
            "Multiple snake bite cases reported in {city} rural outskirts after heavy rain. Anti-venom shortage at local hospital."
        ],
        "source_platform": "mock"
    },
    {
        "type": "violence",
        "severity": "MEDIUM",
        "templates": [
            "Communal tension reported in {city} old quarter. Police deployed. Section 144 imposed."
        ],
        "source_platform": "twitter"
    }
]

def generate_mock_incidents(count_per_type: int = 3) -> dict:
    """
    Generates a specified number of mock incidents for each crisis type 
     and ingests them into the ChromaDB collection.
    """
    total_generated = 0
    duplicates_skipped = 0
    
    logger.info(f"Starting mock incident generation: {count_per_type} per type")
    
    for item in INCIDENT_TEMPLATES:
        crisis_type = item["type"]
        severity = item["severity"]
        source_platform = item["source_platform"]
        
        # Pick count_per_type random cities
        selected_cities = random.sample(INDIAN_CITIES, min(count_per_type, len(INDIAN_CITIES)))
        
        for city in selected_cities:
            # Pick a random template for this type
            template = random.choice(item["templates"])
            text = template.format(city=city["name"])
            
            # Generate random timestamp within the last 24 hours
            hours_ago = random.uniform(0, 24)
            random_timestamp = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
            
            # Build metadata dict - ALL values MUST be strings
            metadata = {
                "type": crisis_type,
                "severity": severity,
                "area_name": city["name"],
                "lat": str(round(city["lat"] + random.uniform(-0.05, 0.05), 6)),
                "lng": str(round(city["lng"] + random.uniform(-0.05, 0.05), 6)),
                "source": source_platform,
                "timestamp": random_timestamp.isoformat().replace("+00:00", "Z"),
                "status": "open",
                "confidence": str(round(random.uniform(0.75, 0.98), 2)),
            }
            
            # Ingest into ChromaDB
            result = ingest_incident(text, metadata)
            
            if result == 'DUPLICATE':
                duplicates_skipped += 1
            elif result != 'ERROR':
                total_generated += 1
                
    stats = get_collection_stats()
    return {
        "total_generated": total_generated,
        "duplicates_skipped": duplicates_skipped,
        "total_in_db": stats.get("total_count", 0)
    }

if __name__ == "__main__":
    # Configure logging for standalone run
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("--- CrisisAI Mock Incident Generator ---")
    
    result = generate_mock_incidents(count_per_type=3)
    
    print(f"Generated: {result['total_generated']}")
    print(f"Duplicates skipped: {result['duplicates_skipped']}")
    print(f"Total in ChromaDB: {result['total_in_db']}")
    
    stats = get_collection_stats()
    print(f"Collection: {stats.get('collection_name')} | Dir: {stats.get('persist_dir')}")
    print("--- Done ---")
