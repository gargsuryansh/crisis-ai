import re
import json
import logging
from typing import Dict, Any, Optional
from backend.app.services.gemini_client import GeminiClient

# Logger setup
logger = logging.getLogger("crisisai.classifier_agent")

class ClassifierAgent:
    """
    Agent responsible for classifying the crisis type, severity, 
    and language of an incoming emergency query.
    
    Uses a hybrid approach:
    1. Hard-coded India-specific keyword rules (Highest Priority)
    2. Heuristic Language Detection
    3. Gemini 2.0 Flash fallback for complex natural language
    """

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini_client = gemini_client or GeminiClient()
        
        # Enum definitions from Section 3
        self.VALID_CRISIS_TYPES = ["fire", "medical", "flood", "earthquake", "snakebite", "accident", "chemical", "violence", "unknown"]
        self.VALID_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    def _detect_language(self, query: str) -> str:
        """Simple heuristic for detecting Indian languages based on Unicode ranges."""
        # Devanagari (Hindi, Marathi, etc.)
        if re.search(r"[\u0900-\u097F]", query):
            return "hi"
        # Tamil
        if re.search(r"[\u0B80-\u0BFF]", query):
            return "ta"
        # Telugu
        if re.search(r"[\u0C00-\u0C7F]", query):
            return "te"
        
        return "en"

    def _apply_hard_coded_rules(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Applies India-specific priority rules.
        If a rule matches, returns the classification result immediately.
        """
        q_lower = query.lower()
        
        result = {
            "crisis_type": "unknown",
            "severity": "MEDIUM",
            "language_detected": self._detect_language(query),
            "confidence": 1.0
        }
        
        matched = False

        # Rule 1: Snakebite (High Priority in India)
        if "saanp" in q_lower or "snake" in q_lower:
            result["crisis_type"] = "snakebite"
            result["severity"] = "HIGH"
            matched = True

        # Rule 2: Unconscious/Critical condition
        if any(word in q_lower for word in ["unconscious", "behosh", "hosh nahi"]):
            if result["crisis_type"] == "unknown":
                result["crisis_type"] = "medical"
            result["severity"] = "CRITICAL"
            matched = True

        # Rule 3: Chest Pain / Heart Issues
        if any(word in q_lower for word in ["chest pain", "seene mein dard", "heart"]):
            result["crisis_type"] = "medical"
            result["severity"] = "HIGH"
            matched = True

        # Rule 4: Multiple Casualties
        if any(word in q_lower for word in ["multiple casualties", "kai log"]):
            result["severity"] = "CRITICAL"
            matched = True

        return result if matched else None

    async def classify(self, query: str) -> Dict[str, Any]:
        """
        Primary method to classify an emergency query.
        """
        logger.info(f"Classifying query: {query[:50]}...")

        # 1. Apply Hard-coded rules first
        hard_coded_result = self._apply_hard_coded_rules(query)
        if hard_coded_result:
            logger.info("Classification matched hard-coded rules.")
            return hard_coded_result

        # 2. Fallback to Gemini 2.0 Flash
        detected_lang = self._detect_language(query)
        prompt = f"""
        Analyze the following emergency query from a citizen and classify it.
        Query: "{query}"

        Instructions:
        - Classify the 'crisis_type' into exactly one of: {", ".join(self.VALID_CRISIS_TYPES)}.
        - Classify the 'severity' into exactly one of: {", ".join(self.VALID_SEVERITIES)}.
        - Detect the 'language_detected' (use ISO codes like 'en', 'hi', 'ta', 'te').
        - Provide a 'confidence' score between 0.0 and 1.0.

        Output MUST be ONLY valid JSON with exactly these keys:
        {{
            "crisis_type": "...",
            "severity": "...",
            "language_detected": "...",
            "confidence": 0.0
        }}
        """

        try:
            # gemini_client.generate handles circuit breaker and Groq fallback
            response_text = self.gemini_client.generate(prompt, json_mode=True)
            
            # Clean response text in case of markdown blocks
            clean_json = re.sub(r"```json|```", "", response_text).strip()
            result = json.loads(clean_json)

            # Validate enums and required keys
            if result.get("crisis_type") not in self.VALID_CRISIS_TYPES:
                result["crisis_type"] = "unknown"
            if result.get("severity") not in self.VALID_SEVERITIES:
                result["severity"] = "MEDIUM"
            
            return {
                "crisis_type": result.get("crisis_type", "unknown"),
                "severity": result.get("severity", "MEDIUM"),
                "language_detected": result.get("language_detected", detected_lang),
                "confidence": float(result.get("confidence", 0.7))
            }

        except Exception as e:
            logger.error(f"Gemini classification failed: {e}")
            # Safe default fallback
            return {
                "crisis_type": "unknown",
                "severity": "MEDIUM",
                "language_detected": detected_lang,
                "confidence": 0.5
            }

async def classify(query: str) -> Dict[str, Any]:
    """
    Convenience function for direct module import.
    Instantiates ClassifierAgent and calls its classify method.
    """
    agent = ClassifierAgent()
    return await agent.classify(query)
