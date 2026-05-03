"""
Dialogue memory: count how many times we asked about each mandatory topic (from bot messages).
Used for stuck detection and to avoid repeating the same question (force multiple-choice or pivot).
"""

from typing import Optional

HIGH_RISK_TOPIC_ORDER = [
    "human_oversight",
    "data_governance",
    "accuracy_robustness",
    "record_keeping",
]

ARTICLE_PHRASES = {
    "human_oversight": "Article 14",
    "data_governance": "Article 10",
    "accuracy_robustness": "Article 15",
    "record_keeping": "Article 12",
}

RESOLVED_VALUES = ["present", "planned", "planned_remediation", "yes"]


def compute_topic_ask_count(logs: list) -> dict:
    """
    Count how many bot messages mention each article (Article 14, 10, 15, 12).
    logs: list of objects with .sender and .message (e.g. InterviewLog instances).
    Returns: { "human_oversight": int, "data_governance": int, ... }
    """
    topic_ask_count = {t: 0 for t in HIGH_RISK_TOPIC_ORDER}
    for log in logs:
        if getattr(log, "sender", None) != "bot" or not getattr(log, "message", None):
            continue
        msg = (log.message or "").lower()
        for fact_key, phrase in ARTICLE_PHRASES.items():
            if phrase.lower() in msg:
                topic_ask_count[fact_key] = topic_ask_count.get(fact_key, 0) + 1
                break
    return topic_ask_count


def compute_stuck_on_topic(
    topic_ask_count: dict,
    fact_dict: dict,
    risk_level: str,
) -> Optional[str]:
    """
    First topic (in HIGH_RISK_TOPIC_ORDER) that we've asked 2+ times and is still not resolved.
    Returns topic key (e.g. "human_oversight") or None.
    """
    if risk_level != "HIGH":
        return None
    for fact_key in HIGH_RISK_TOPIC_ORDER:
        if topic_ask_count.get(fact_key, 0) < 2:
            continue
        val = (fact_dict.get(fact_key) or "").strip().lower()
        if fact_key == "human_oversight":
            resolved = (
                val in RESOLVED_VALUES
                or (fact_dict.get("remediation_accepted") or "").strip().lower()
                == "yes"
            )
        else:
            resolved = (
                val in RESOLVED_VALUES
                or (fact_dict.get(f"{fact_key}_remediation") or "").strip().lower()
                == "yes"
            )
        if not resolved:
            return fact_key
    return None
