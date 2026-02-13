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

