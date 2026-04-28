import asyncio
import sys
from pathlib import Path

# Add project root (CrisisAI) to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.app.services.agents.classifier_agent import ClassifierAgent

async def test_classifier():
    classifier = ClassifierAgent()
    
    test_cases = [
        ("Muje saanp ne kaat liya hai", "snakebite", "HIGH", "hi"),
        ("Someone is unconscious and behosh here!", "medical", "CRITICAL", "en"),
        ("I have severe chest pain and seene mein dard", "medical", "HIGH", "en"),
        ("There is a fire but many people (kai log) are trapped", "unknown", "CRITICAL", "hi"),
        ("Help, building collapse!", "Gemini Fallback", "N/A", "en"),
        ("கணவன் மயக்கம்", "Gemini Fallback", "N/A", "ta")
    ]
    
    print("\n--- Testing ClassifierAgent (Hard-coded Rules & Language) ---\n")
    
    for query, expected_type, expected_sev, expected_lang in test_cases:
        # Note: We won't actually call Gemini in this test to avoid API usage/keys
        # We'll just check if the hard-coded rules hit.
        
        # Manually calling internal methods for testing purposes
        hard_coded = classifier._apply_hard_coded_rules(query)
        lang = classifier._detect_language(query)
        
        if hard_coded:
            print(f"QUERY: {query.encode('ascii', 'ignore').decode('ascii')} (Contains non-ascii)")
            print(f"  MATCH: Type={hard_coded['crisis_type']}, Severity={hard_coded['severity']}, Lang={lang}")
            print(f"  EXPECTED: Type={expected_type}, Severity={expected_sev}, Lang={expected_lang}")
        else:
            print(f"QUERY: {query.encode('ascii', 'ignore').decode('ascii')} (Contains non-ascii)")
            print(f"  MATCH: [Gemini Fallback Needed], Lang={lang}")
            print(f"  EXPECTED: Lang={expected_lang}")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_classifier())
