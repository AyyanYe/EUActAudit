# backend/core/eu_ai_act_context.py
# Short excerpts from EU AI Act for RAG-style injection into expert consultation prompts.
# Use to explain legal requirements when the user's answer is insufficient or vague.

EU_AI_ACT_ARTICLE_14 = """
Article 14 – Human oversight (EU AI Act 2025)
High-risk AI systems shall be designed and developed in such a way that they can be effectively overseen by natural persons. Human oversight shall aim to prevent or minimize risks to health, safety or fundamental rights. Oversight may be exercised through human-in-the-loop, human-on-the-loop, or human-in-command. For automated decisions with legal or similarly significant effects, the human must be able to understand, intervene, and reverse or interrupt the system. "Sometimes" or informal review does not meet the threshold for effective human oversight under the Act.
"""

EU_AI_ACT_ARTICLE_10 = """
Article 10 – Data governance (EU AI Act 2025)
High-risk AI systems that use training, validation and testing data shall be developed with data governance and management practices that ensure relevant, representative, sufficiently free-of-errors and complete datasets. Appropriate measures shall be taken to detect and mitigate risks of bias. Training data shall be relevant, representative and of sufficient quality in view of the intended purpose.
"""

EU_AI_ACT_ARTICLE_15 = """
Article 15 – Accuracy, robustness and cybersecurity (EU AI Act 2025)
High-risk AI systems shall be designed to achieve an appropriate level of accuracy, robustness and cybersecurity. Accuracy shall be evaluated in light of the intended purpose. Risks of errors shall be minimized. The system and its outputs shall be resilient to errors and shall allow for human intervention. Appropriate resilience and security measures shall be in place.
"""

EU_AI_ACT_ARTICLE_12 = """
Article 12 – Record-keeping (EU AI Act 2025)
Providers of high-risk AI systems shall keep logs of the operation of their systems. The logging shall be such as to ensure traceability and enable post-market monitoring and other enforcement. Records shall be kept for a period appropriate to the intended purpose and the nature of the system, and in any case for at least six months unless otherwise required by Union or national law.
"""

ARTICLE_CONTEXT_BY_TOPIC = {
    "human_oversight": EU_AI_ACT_ARTICLE_14,
    "data_governance": EU_AI_ACT_ARTICLE_10,
    "accuracy_robustness": EU_AI_ACT_ARTICLE_15,
    "record_keeping": EU_AI_ACT_ARTICLE_12,
}


def get_article_context_for_topic(topic_key: str) -> str:
    """Return RAG context (law excerpt) for the given mandatory topic."""
    return ARTICLE_CONTEXT_BY_TOPIC.get(topic_key, "").strip()
