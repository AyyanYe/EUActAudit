"""
Tests for Expert Consultation: dialogue memory, stuck detection, extraction normalization.
Run: python backend/tests/test_expert_consultation.py   or   pytest backend/tests/test_expert_consultation.py -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_compute_topic_ask_count_empty():
    from core.dialogue_memory import compute_topic_ask_count
    assert compute_topic_ask_count([])["human_oversight"] == 0


def test_compute_topic_ask_count_counts_article_14():
    from core.dialogue_memory import compute_topic_ask_count
    class Log:
        def __init__(self, sender, message):
            self.sender = sender
            self.message = message
    logs = [
        Log("bot", "Article 14 requires human oversight. Can you implement?"),
        Log("bot", "Under Article 14, high-risk systems need..."),
    ]
    counts = compute_topic_ask_count(logs)
    assert counts["human_oversight"] == 2
    assert counts["data_governance"] == 0


def test_compute_stuck_on_topic_resolved():
    from core.dialogue_memory import compute_stuck_on_topic
    topic_ask_count = {"human_oversight": 2, "data_governance": 0, "accuracy_robustness": 0, "record_keeping": 0}
    fact_dict = {"human_oversight": "planned", "remediation_accepted": "yes"}
    assert compute_stuck_on_topic(topic_ask_count, fact_dict, "HIGH") is None


def test_compute_stuck_on_topic_first_gap():
    from core.dialogue_memory import compute_stuck_on_topic
    topic_ask_count = {"human_oversight": 2, "data_governance": 0, "accuracy_robustness": 0, "record_keeping": 0}
    fact_dict = {"human_oversight": "partial_or_unclear"}
    assert compute_stuck_on_topic(topic_ask_count, fact_dict, "HIGH") == "human_oversight"


def test_normalize_compliance_facts_partial():
    from core.engine import normalize_compliance_facts
    data = {"human_oversight": "partial", "data_governance": "yes"}
    normalize_compliance_facts(data)
    assert data["human_oversight"] == "partial_or_unclear"
    assert data["data_governance"] == "yes"


def test_normalize_compliance_facts_low_confidence():
    from core.engine import normalize_compliance_facts
    data = {"human_oversight": "we have something", "confidence_scores": {"human_oversight": 40}}
    normalize_compliance_facts(data)
    assert data["human_oversight"] == "partial_or_unclear"


def test_normalize_compliance_facts_leaves_yes_unchanged():
    from core.engine import normalize_compliance_facts
    data = {"human_oversight": "yes", "confidence_scores": {"human_oversight": 90}}
    normalize_compliance_facts(data)
    assert data["human_oversight"] == "yes"


def test_normalize_compliance_facts_leaves_absent_unchanged():
    from core.engine import normalize_compliance_facts
    data = {"data_governance": "absent", "confidence_scores": {"data_governance": 20}}
    normalize_compliance_facts(data)
    assert data["data_governance"] == "absent"


def test_compute_stuck_on_topic_data_governance():
    """First topic with count>=2 and unresolved is returned; human_oversight resolved so data_governance is stuck."""
    from core.dialogue_memory import compute_stuck_on_topic
    topic_ask_count = {"human_oversight": 2, "data_governance": 2, "accuracy_robustness": 0, "record_keeping": 0}
    fact_dict = {"human_oversight": "planned", "remediation_accepted": "yes", "data_governance": "no"}
    assert compute_stuck_on_topic(topic_ask_count, fact_dict, "HIGH") == "data_governance"


def test_compute_topic_ask_count_mixed_logs():
    from core.dialogue_memory import compute_topic_ask_count
    class Log:
        def __init__(self, sender, message):
            self.sender = sender
            self.message = message
    logs = [
        Log("user", "We have some oversight"),
        Log("bot", "Article 10 requires data governance. Can you implement bias testing?"),
        Log("bot", "Article 14 requires human oversight."),
    ]
    counts = compute_topic_ask_count(logs)
    assert counts["human_oversight"] == 1
    assert counts["data_governance"] == 1
    assert counts["accuracy_robustness"] == 0


if __name__ == "__main__":
    tests = [
        test_compute_topic_ask_count_empty,
        test_compute_topic_ask_count_counts_article_14,
        test_compute_topic_ask_count_mixed_logs,
        test_compute_stuck_on_topic_resolved,
        test_compute_stuck_on_topic_first_gap,
        test_compute_stuck_on_topic_data_governance,
        test_normalize_compliance_facts_partial,
        test_normalize_compliance_facts_low_confidence,
        test_normalize_compliance_facts_leaves_yes_unchanged,
        test_normalize_compliance_facts_leaves_absent_unchanged,
    ]
    for t in tests:
        t()
        print("OK", t.__name__)
    print("All tests passed.")
