# backend/core/high_risk_checklist.py
"""
Mandatory Checklist for HIGH Risk Systems under EU AI Act.
Ensures all required topics are covered before assessment completion.
"""

from typing import Dict, List, Tuple

# Mandatory topics that must be discussed for HIGH risk systems
HIGH_RISK_MANDATORY_TOPICS = [
    "human_oversight",      # Article 14 - Human oversight mechanisms
    "data_governance",      # Article 10 - Training data quality and bias mitigation
    "accuracy_robustness",  # Article 15 - Accuracy, robustness, and security
    "record_keeping"        # Article 12 - Logging and record keeping
]

def get_missing_mandatory_topics(facts: Dict[str, str], obligations: List[dict]) -> List[str]:
    """
    Returns list of mandatory HIGH risk topics that are missing or not confirmed.
    
    Args:
        facts: Dictionary of extracted facts
        obligations: List of obligations (to check if human_oversight obligation exists)
    
    Returns:
        List of missing topic keys
    """
    missing = []
    
    # Check each mandatory topic
    for topic in HIGH_RISK_MANDATORY_TOPICS:
        if topic == "human_oversight":
            # Human oversight is confirmed if "present", "planned", or user accepted remediation.
            oversight_value = facts.get("human_oversight", "").lower()
            remediation_accepted = facts.get("remediation_accepted", "").lower()
            has_oversight_obligation = any(
                ob.get("code", "") in ["ART_26", "ART_14_OVERSIGHT"]
                for ob in obligations if isinstance(ob, dict)
            )
            if oversight_value in ["present", "planned", "yes"]:
                continue  # Topic covered
            if remediation_accepted == "yes":
                continue  # User accepted remediation (planned) - topic addressed
            if oversight_value in ["absent", "no", "partial", "partial_or_unclear"]:
                continue  # Addressed but non-compliant or under review; guardrail / expert handles it
            if has_oversight_obligation and oversight_value in ["present", "planned", "yes"]:
                continue
            missing.append(topic)
        
        elif topic == "data_governance":
            data_gov_value = facts.get("data_governance", "").lower()
            if data_gov_value not in ["yes", "no", "planned_remediation", "planned", "partial_or_unclear"]:
                missing.append(topic)
        
        elif topic == "accuracy_robustness":
            accuracy_value = facts.get("accuracy_robustness", "").lower()
            if accuracy_value not in ["yes", "no", "planned_remediation", "planned", "partial_or_unclear"]:
                missing.append(topic)
        
        elif topic == "record_keeping":
            record_value = facts.get("record_keeping", "").lower()
            if record_value not in ["yes", "no", "planned_remediation", "planned", "partial_or_unclear"]:
                missing.append(topic)
    
    return missing

def get_topic_question(topic: str) -> str:
    """
    Returns the appropriate question for a missing mandatory topic.
    """
    questions = {
        "human_oversight": "Since this is a High Risk system, we must ensure human oversight under Article 14. Do you have human reviewers who can stop or override the AI's decisions?",
        "data_governance": "Since this is a High Risk system, we must ensure data quality under Article 10. How do you mitigate bias in your training data (e.g., ensuring fair representation of different demographics)?",
        "accuracy_robustness": "Since this is a High Risk system, we must ensure accuracy and robustness under Article 15. How do you monitor error rates and ensure the system's security and reliability?",
        "record_keeping": "Since this is a High Risk system, we must ensure proper record keeping under Article 12. Do you maintain logs of the AI system's operations and decisions?"
    }
    return questions.get(topic, f"Please provide information about {topic}.")

def can_complete_high_risk_assessment(facts: Dict[str, str], obligations: List[dict]) -> bool:
    """
    Checks if all mandatory topics are covered for HIGH risk assessment.
    Returns True only if all mandatory topics are confirmed.
    """
    missing = get_missing_mandatory_topics(facts, obligations)
    return len(missing) == 0

