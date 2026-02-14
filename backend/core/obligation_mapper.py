# backend/core/obligation_mapper.py
"""
Universal mapping between facts and obligations.
This allows dynamic gap detection without hardcoding specific articles.
"""

# Mapping from fact keys to obligation codes
FACT_TO_OBLIGATION_MAP = {
    "human_oversight": "ART_14_OVERSIGHT",
    "data_governance": "ART_10",
    "accuracy_robustness": "ART_15",
    "record_keeping": "ART_12",
    "transparency": "ART_50",
    "article_50_notice": "ART_50",
}

# Reverse mapping: obligation codes to fact keys
OBLIGATION_TO_FACT_MAP = {v: k for k, v in FACT_TO_OBLIGATION_MAP.items()}

def get_obligation_code_for_fact(fact_key: str) -> str:
    """Get the obligation code for a given fact key."""
    return FACT_TO_OBLIGATION_MAP.get(fact_key)

def get_fact_key_for_obligation(obligation_code: str) -> str:
    """Get the fact key for a given obligation code."""
    return OBLIGATION_TO_FACT_MAP.get(obligation_code)

def is_negative_value(value: str) -> bool:
    """Check if a fact value indicates absence/gap. For human_oversight, 'partial' is non-compliant under Article 14."""
    if not value:
        return False
    value_lower = value.lower()
    return value_lower in ["no", "absent", "partial", "none", "not", "we don't", "we do not", "missing"]

def is_positive_value(value: str) -> bool:
    """Check if a fact value indicates presence/compliance."""
    if not value:
        return False
    value_lower = value.lower()
    return value_lower in ["yes", "present", "implemented", "we have", "we do"]

def is_planned_value(value: str) -> bool:
    """Check if a fact value indicates planned remediation."""
    if not value:
        return False
    value_lower = value.lower()
    return value_lower in ["planned_remediation", "planned", "will implement", "we'll add", "future"]


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

# Facts below this threshold trigger a verification question before
# the system uses them for compliance decisions.
CONFIDENCE_THRESHOLD = 70

def compute_fact_confidence(fact_key: str, fact_value: str) -> int:
    """
    Deterministic confidence floor based on the *category* of a fact's value.

    Returns 0-100.  This acts as a ceiling that the LLM can only LOWER
    (via ``min(deterministic, llm_score)``), never inflate.

    Scoring logic:
      - Explicit positive ("yes", "present", …)        → 90
      - Explicit negative ("no", "absent", …)           → 85  (user clearly stated it)
      - Planned / future                                → 70  (intent stated, not done)
      - "partial"                                       → 50
      - "partial_or_unclear"                            → 40  (explicitly uncertain)
      - Any other non-empty string longer than 2 chars  → 85  (user likely stated it)
      - Very short / empty                              → 0-60
    """
    if not fact_value or not fact_value.strip():
        return 0

    val = fact_value.strip().lower()

    # Explicit positive statements — high confidence
    if is_positive_value(val):
        return 90

    # Explicit negative statements — high confidence (user clearly said "no")
    if is_negative_value(val):
        return 85

    # Planned = user stated intent but it's not done yet
    if is_planned_value(val):
        return 70

    # Partial / unclear — low confidence by definition
    if val == "partial_or_unclear":
        return 40
    if val == "partial":
        return 50

    # Non-compliance facts (domain, role, purpose, data_type, context, etc.)
    # If a value exists and is reasonably long, the user likely stated it explicitly.
    if len(val) > 2:
        return 85

    return 60  # Very short values are suspect

