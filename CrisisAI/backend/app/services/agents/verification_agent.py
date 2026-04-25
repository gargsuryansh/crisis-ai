import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

# Setup logger
logger = logging.getLogger(__name__)

# Constants
FORBIDDEN_ADVICE = [
    "re-enter the building",
    "remove the snake",
    "apply tourniquet",
    "give water to unconscious",
    "move a spinal injury patient",
    "ignore the bite",
    "cut the bite",
    "suck the venom",
    "apply ice to snake bite",
    "run if clothes catch fire"
]

SAFE_DEFAULT = (
    "Call 112 immediately. Do not move the person unless there is immediate danger. "
    "Keep them calm and follow verified emergency instructions."
)

SAFE_WHITELIST = [
    "call 112",
    "call 108",
    "call emergency",
    "emergency services",
    "keep calm",
    "keep the person calm",
    "immobilize",
    "lying down",
    "do not move",
]

NEGATION_MARKERS = [
    "do not",
    "don't",
    "dont",
    "never",
    "avoid",
    "should not",
    "must not",
    "no "
]

SAFETY_RULES_PATH = Path("data/protocols/safety_rules.json")

def normalize_text(text: str) -> str:
    """Normalizes text for consistent comparison."""
    if not text:
        return ""
    # Lowercase
    text = text.lower()
    # Normalize curly quotes and dashes
    text = text.replace("“", "\"").replace("”", "\"").replace("‘", "'").replace("’", "'")
    text = text.replace("—", "-").replace("–", "-")
    # Normalize whitespace (multiple spaces to one)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def _is_safe_whitelisted(text: str) -> bool:
    """Checks if a phrase is explicitly whitelisted as safe."""
    normalized = normalize_text(text)
    return any(item in normalized for item in SAFE_WHITELIST)

def _is_negated_occurrence(response_norm: str, start_index: int) -> bool:
    """Look at up to 40 characters before the match to see if it is negated."""
    window_start = max(0, start_index - 40)
    pre_match_window = response_norm[window_start:start_index]
    
    for marker in NEGATION_MARKERS:
        if marker in pre_match_window:
            return True
    return False

def _avoid_sentence_to_pattern(text: str) -> str:
    """Converts 'Do not X' sentences into 'X' dangerous action patterns."""
    norm = normalize_text(text)
    # Sort markers by length descending to match longest first
    markers = sorted(NEGATION_MARKERS, key=len, reverse=True)
    for marker in markers:
        if norm.startswith(marker):
            norm = norm[len(marker):].strip()
            break
    # Remove trailing punctuation
    norm = re.sub(r'[.!?]+$', '', norm)
    return norm.strip()

def load_safety_rules() -> List[str]:
    """
    Loads safety rules from data/protocols/safety_rules.json.
    Focuses on 'rule' and 'block_patterns' fields.
    """
    if not SAFETY_RULES_PATH.exists():
        logger.warning(f"Safety rules file missing at: {SAFETY_RULES_PATH}")
        return []

    try:
        with open(SAFETY_RULES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        extracted_rules: Set[str] = set()
        rules_list = data.get("safety_rules", [])
        
        if not isinstance(rules_list, list):
            logger.warning("safety_rules field is not a list.")
            return []

        for rule_obj in rules_list:
            if not isinstance(rule_obj, dict):
                continue
                
            # Extract from 'rule' string
            main_rule = rule_obj.get("rule")
            if isinstance(main_rule, str) and len(main_rule) >= 5:
                if not _is_safe_whitelisted(main_rule):
                    extracted_rules.add(main_rule)
            
            # Extract from 'block_patterns' list
            patterns = rule_obj.get("block_patterns", [])
            if isinstance(patterns, list):
                for p in patterns:
                    if isinstance(p, str) and len(p) >= 5:
                        if not _is_safe_whitelisted(p):
                            extracted_rules.add(p)
        
        final_list = sorted(list(extracted_rules))
        logger.info(f"Loaded {len(final_list)} specific safety rules from JSON.")
        return final_list

    except Exception as e:
        logger.error(f"Failed to load or parse safety rules: {e}")
        return []

def contains_forbidden_advice(response: str, forbidden_items: List[str]) -> List[str]:
    """
    Checks for forbidden phrases using case-insensitive substring matching,
    accounting for negation to avoid false positives.
    """
    normalized_response = normalize_text(response)
    matches = set()
    
    for item in forbidden_items:
        if not item or _is_safe_whitelisted(item):
            continue
        
        normalized_item = normalize_text(item)
        if not normalized_item or len(normalized_item) < 5:
            continue
            
        start = 0
        while True:
            idx = normalized_response.find(normalized_item, start)
            if idx == -1:
                break
            
            # If the occurrence is NOT negated, it's dangerous
            if not _is_negated_occurrence(normalized_response, idx):
                matches.add(item)
                break # One dangerous occurrence is enough
            
            start = idx + 1
            
    return sorted(list(matches))

def _normalize_crisis_type(value: Optional[str]) -> str:
    """Normalizes crisis type strings for robust comparison."""
    if not value:
        return ""
    return value.lower().replace("_", "").replace("-", "").strip()

def _extract_avoid_from_context(retrieved_context: Optional[List[Dict[str, Any]]]) -> List[str]:
    """Extracts 'what_to_avoid' items from RAG context and converts them to patterns."""
    avoid_list = set()
    if not retrieved_context:
        return []
    
    for item in retrieved_context:
        what_to_avoid = item.get("what_to_avoid", [])
        if not isinstance(what_to_avoid, list):
            continue
            
        for avoid in what_to_avoid:
            text = ""
            if isinstance(avoid, str):
                text = avoid
            elif isinstance(avoid, dict):
                text = avoid.get("action", "")
            
            if text:
                pattern = _avoid_sentence_to_pattern(text)
                if pattern and len(pattern) >= 5:
                    avoid_list.add(pattern)
                    
    return sorted(list(avoid_list))

async def verify(
    response: str,
    crisis_type: str,
    retrieved_context: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Verifies AI-generated guidance. Prevents dangerous advice while allowing
    negated safety instructions and whitelisted safe phrases.
    """
    try:
        # 1. Build combined forbidden list
        combined_forbidden: Set[str] = set(FORBIDDEN_ADVICE)
        
        # 2. Add rules from safety_rules.json
        combined_forbidden.update(load_safety_rules())
        
        # 3. Add rules from RAG context (converted to patterns)
        combined_forbidden.update(_extract_avoid_from_context(retrieved_context))
        
        # 4. Add crisis-specific rules
        norm_type = _normalize_crisis_type(crisis_type)
        
        if norm_type == "snakebite":
            combined_forbidden.update([
                "apply a tourniquet",
                "apply tourniquet",
                "use a tourniquet",
                "use tourniquet",
                "cut the bite",
                "cut the wound",
                "suck the venom",
                "suck out venom",
                "apply ice",
                "catch the snake",
                "kill the snake",
                "remove the snake"
            ])
        elif norm_type == "fire":
            combined_forbidden.update([
                "re-enter",
                "use elevator",
                "run if clothes catch fire"
            ])
        elif norm_type == "medical":
            combined_forbidden.update([
                "give water to unconscious",
                "move spinal injury"
            ])

        # 5. Check response against combined forbidden list
        matches = contains_forbidden_advice(response, list(combined_forbidden))
        
        if not matches:
            return response
        
        # 6. Unsafe match found - construct correction
        logger.warning(f"Unsafe guidance detected for crisis_type '{crisis_type}': {matches}")
        
        matched_str = ", ".join(matches)
        correction = (
            f"SAFETY CORRECTION: The generated guidance contained potentially unsafe advice.\n"
            f"Avoid: {matched_str}\n\n"
            f"{SAFE_DEFAULT}\n\n"
            f"Verified guidance:\n"
            f"{response}"
        )
        return correction

    except Exception as e:
        logger.error(f"Verification process failed: {e}")
        return response
