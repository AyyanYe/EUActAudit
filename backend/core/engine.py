import os
import json
from dotenv import load_dotenv # <--- IMPORT THIS
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from core.risk_rules import evaluate_compliance_state
from core.state_machine import StateMachine, InterviewState, ConfidenceLevel
from core.high_risk_checklist import get_missing_mandatory_topics, get_topic_question, can_complete_high_risk_assessment
from core.eu_ai_act_context import get_article_context_for_topic

# <--- LOAD THE ENV FILE IMMEDIATELY ---
load_dotenv()

COMPLIANCE_KEYS_NORMALIZE = ["human_oversight", "data_governance", "accuracy_robustness", "record_keeping"]


def normalize_compliance_facts(data: dict) -> None:
    """
    In-place normalization for compliance fact values.
    - Map "partial" -> "partial_or_unclear" for compliance topics.
    - If confidence_scores[key] < 60 and value is not clearly yes/no/absent, set to "partial_or_unclear".
    """
    for key in COMPLIANCE_KEYS_NORMALIZE:
        if key not in data:
            continue
        val = (data.get(key) or "").strip().lower()
        if val == "partial":
            data[key] = "partial_or_unclear"
    confidence_scores = data.get("confidence_scores") or {}
    if isinstance(confidence_scores, dict):
        for key in COMPLIANCE_KEYS_NORMALIZE:
            if key not in data or data[key] in ["yes", "no", "present", "absent", "planned", "planned_remediation"]:
                continue
            score = confidence_scores.get(key)
            if isinstance(score, (int, float)) and 0 <= score <= 100 and score < 60:
                data[key] = "partial_or_unclear" 

class GovernanceEngine:
    def __init__(self):
        # Debug print to verify key is found
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("ERROR: OPENROUTER_API_KEY not found in environment!")
        
        self.llm = ChatOpenAI(
            model="openai/gpt-4o",
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0
        )

    async def extract_facts(self, history_text: str):
        """
        The 'Sensor': Extracts structured facts from the conversation history.
        """
        system_prompt = """
        You are an Expert Compliance Auditor for the EU AI Act (2025).
        Your job is to listen to the user and EXTRACT structured facts about their AI system.

        CRITICAL: Extract BOTH positive AND negative facts. If the user says "we do not have X", "no X", "none", "we don't do that", 
        that is a FACT indicating a GAP. Capture it explicitly as "absent" or "no".
        
        NEGATIVE INTENT DETECTION:
        - When user answers "No", "None", "We don't do that", "We don't have that", "Not implemented", "Missing" → 
          This indicates a COMPLIANCE GAP. Extract the fact with value "absent" or "no".
        - Examples:
          * "Do you have human oversight?" → "No" → Extract: "human_oversight": "absent"
          * "Do you mitigate bias?" → "We don't do that" → Extract: "data_governance": "absent"
          * "Is there transparency?" → "None" → Extract: "transparency": "absent"

        EXTRACT THESE SPECIFIC KEYS if mentioned (or explicitly denied):
        - "domain": The area of use (e.g., recruitment, credit_scoring, healthcare, education).
        - "role": "provider" (built it) or "deployer" (bought/using it).
        - "purpose": Specific goal (e.g., ranking_candidates, detecting_fraud, filtering_candidates, emotion_recognition, social_scoring).
        - "capability": "chatbot" (conversational AI), "interaction" (user interacts with AI), "content_generation" (AI generates images/video/audio).
        - "data_type": "personal", "biometric", "anonymous", "sensitive_personal".
        - "automation": "fully_automated" (no human review), "human_in_the_loop" (human reviews decisions), "partial_automation".
        - "context": Where is it used? (e.g., workplace, public_space, school, education).
        - "human_oversight": "present" (human reviews decisions currently), "absent" (no human review), "planned" (will implement), "partial" (some decisions reviewed), "partial_or_unclear" (vague/informal: "we do it sometimes", "it's complicated", "kind of", "informally").
        - "remediation_accepted": "yes" or "no" (only set if user answers the Article 14 remediation question).
        - "special_category_data": "yes" (processes racial/ethnic origin, health, political opinions, etc.), "no", or specific types mentioned.
        - "exemption_probe_answered": "yes" or "no" (only set if user answers the medical/safety exemption question).
        - "media_type": "image", "video", "audio" (for content generation systems).
        - "transparency": "present" (user confirms AI disclosure/notice is visible), "absent" (user says no disclosure), or "unknown" (not yet asked).
        - "article_50_notice": "yes" (transparency notice is present), "no" (not present), or leave unset if not mentioned).
        - "data_governance": "yes" (user confirms bias mitigation/training data quality measures), "no" (no measures), or leave unset if not mentioned.
        - "accuracy_robustness": "yes" (user confirms error rate monitoring/security measures), "no" (no measures), or leave unset if not mentioned.
        - "record_keeping": "yes" (user confirms logging/record keeping in place), "no" (no logging), or leave unset if not mentioned.

        WORKFLOW STEPS (Live Workflow Map):
        - "workflow_steps": Extract the high-level operational steps of the AI system from the conversation as a sequential array of strings.
        - Each step should be a short label (e.g., "Resume Input", "Keyword Scan", "Human Review", "Email Candidate").
        - If the user describes a process (e.g., "takes a resume, scans for keywords, then emails the candidate"), set workflow_steps to that order.
        - If the user corrects or updates steps (e.g., "Actually, a human reviews it before the email", "Swap step 2 and 3", "Step 3 is actually manual review"), update the array accordingly. Apply corrections to the existing list.
        - Always return workflow_steps as an array of strings, e.g. ["Resume Input", "Keyword Scan", "Human Review", "Email Candidate"]. If no steps can be inferred, return an empty array [].

        CRITICAL MAPPING RULES FOR PROHIBITED PRACTICES:
        1. Emotion Recognition Detection:
           - If user mentions: "detecting facial expressions", "monitoring boredom", "attention score", "emotion detection", 
             "detecting student engagement", "reading emotions", "facial expression analysis" → set "purpose": "emotion_recognition"
           - If context is "education", "school", "workplace" → set "context": "education" or "workplace" accordingly
        
        2. Social Scoring Detection:
           - If user mentions: "social scoring", "reliability score", "trustworthiness rating" → set "purpose": "social_scoring"
        
        3. Chatbot/Interaction Detection (for LIMITED Risk):
           - If user mentions: "chatbot", "conversational AI", "AI assistant", "virtual assistant", "chat interface", 
             "customer service bot", "AI that talks to users" → set "capability": "chatbot" or "interaction"
           - Do NOT set this as "domain" or "purpose" - it's a "capability"
        
        4. Content Generation Detection (for LIMITED Risk):
           - If user mentions: "generating images", "creating videos", "AI art", "deepfake", "synthetic media" → set "capability": "content_generation"
           - Also set "media_type": "image", "video", or "audio" based on what they mention

        IMPORTANT RULES:
        1. HUMAN OVERSIGHT STATE MAPPING (CRITICAL - Article 14 Compliance Guardrail):
           - If user says "we have human oversight", "yes we have reviewers", "human reviews decisions" → set "human_oversight": "present"
           - If user says "we do not have human oversight", "no human review", "fully automated", "no reviewers" → set "human_oversight": "absent"
           - SEMANTIC EVALUATION (Intent/Completeness): Do not rely only on keywords. Evaluate the QUALITY of the user's answer. If the user is vague or informal → set "partial_or_unclear". Examples of vague/informal: "we do it sometimes", "it's complicated", "kind of", "we have something informal", "we're working on it", "not really formalized", "depends", "in some cases". Use "partial_or_unclear" when the answer does not clearly meet the legal threshold (not a clear yes, no, or committed plan).
           - If user clearly says "partial oversight", "only some decisions reviewed", "not all" → set "human_oversight": "partial".
           - If user says "we're planning to add it", "we'll implement it", "yes we can add that" (in response to remediation question) → set "human_oversight": "planned"
           - If user says "we removed the reviewer", "we eliminated oversight", "we stopped using human review" → set "human_oversight": "absent" (OVERWRITE previous state)
           - CRITICAL: If user changes from "present" or "planned" to "absent" or "partial", OVERWRITE the previous value. The latest statement takes precedence.
        2. If user says "fully automated" or "automatic rejection" → set "automation": "fully_automated" AND "human_oversight": "absent"
        3. REMEDIATION RESPONSE EXTRACTION:
           - If user answers remediation question with "yes", "we can implement", "we'll add it", "sure" → set "remediation_accepted": "yes" AND "human_oversight": "planned"
           - If user answers remediation question with "no", "we won't add it", "not possible", "refuse" → set "remediation_accepted": "no"
        3. If user mentions sensitive data (ethnic origin, disabilities, health) → set "special_category_data": "yes"
        4. Capture negative statements as explicit facts, not as missing information.
        5. If user says "no" to medical/safety exemption question → set "exemption_probe_answered": "no"
        6. If user says "yes" to medical/safety exemption → set "exemption_probe_answered": "yes" and note the exemption reason
        7. TRANSPARENCY EXTRACTION (Article 50):
           - If user confirms AI disclosure (e.g., "yes", "we have a banner", "it says so in the UI", "users are informed", "transparency notice is visible") → set "transparency": "present" AND "article_50_notice": "yes"
           - If user says "no", "not yet", "we don't have that" → set "transparency": "absent" AND "article_50_notice": "no"
           - If user mentions watermarking or marking for content generation → set "transparency": "present" AND "article_50_notice": "yes"
        
        8. HIGH RISK MANDATORY TOPICS EXTRACTION (with semantic evaluation):
           - For data_governance, accuracy_robustness, record_keeping: Evaluate INTENT and COMPLETENESS. Allowed values: "yes", "no", "absent", "planned_remediation", "partial_or_unclear".
           - "partial_or_unclear": Use when the user's answer is vague, informal, or does not clearly meet the legal threshold (e.g. "we have some processes", "we're looking into it", "it's ad hoc", "not really").
           - data_governance: Clear bias mitigation / data quality → "yes". Explicit no → "no" or "absent". Vague → "partial_or_unclear". Committed plan → "planned_remediation" and set "[topic]_remediation": "yes".
           - accuracy_robustness: Clear monitoring/security → "yes". Explicit no → "no"/"absent". Vague → "partial_or_unclear".
           - record_keeping: Clear logging/records → "yes". Explicit no → "no"/"absent". Vague → "partial_or_unclear".
           - If user explicitly says "no" or "we don't have that" → set the key to "no" or "absent"
           - REMEDIATION RESPONSE EXTRACTION (for Article 10, 12, 15):
             - If user answers remediation question with "yes", "we can implement", "we'll add it", "sure", "yes we can" → set "[topic]_remediation": "yes" AND set the main fact to "planned_remediation"
             - If user answers remediation question with "no", "we won't add it", "not possible", "refuse" → set "[topic]_remediation": "no"
             - CRITICAL: When "[topic]_remediation": "yes", ALSO set the main fact (e.g., "data_governance") to "planned_remediation" to mark it as addressed
             - Examples: 
               * User says "yes" to data governance remediation → set "data_governance_remediation": "yes" AND "data_governance": "planned_remediation"
               * User says "no" to accuracy remediation → set "accuracy_robustness_remediation": "no" (keep "accuracy_robustness" as "no")

        SEMANTIC CONFIDENCE (0-100) - Do not rely on Yes/No keywords. For each compliance article below, output a confidence score 0-100 indicating how well the user's answers meet the legal threshold:
        - "confidence_scores": Object with keys: "human_oversight", "data_governance", "accuracy_robustness", "record_keeping". Value 0-100 per key.
        - 0-30: Absent or clearly no / not implemented.
        - 31-59: Partial, vague, or unclear ("we do it sometimes", "it's complicated", "we're working on it").
        - 60-79: Some evidence of compliance but not fully clear or formalized.
        - 80-100: Clear, formal compliance (present, documented, implemented).
        - Only include keys that are discussed or inferable from the conversation; omit others or set to 50 if truly unknown.

        Return ONLY a raw JSON object. Do not invent facts. If unclear, ignore the key.
        Include "workflow_steps" as an array of strings whenever operational steps are mentioned or corrected.
        Include "confidence_scores" as above for compliance articles when relevant.
        Example: {"domain": "recruitment", "human_oversight": "partial_or_unclear", "confidence_scores": {"human_oversight": 35, "data_governance": 80}, "workflow_steps": ["Resume Input", "Keyword Scan"]}
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Conversation History:\n{history_text}")
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            content = response.content.replace("```json", "").replace("```", "").strip()
            data = json.loads(content)
            # Ensure workflow_steps is a list of strings
            if "workflow_steps" in data:
                raw = data["workflow_steps"]
                if isinstance(raw, list):
                    data["workflow_steps"] = [str(s).strip() for s in raw if s]
                else:
                    data["workflow_steps"] = []
            normalize_compliance_facts(data)
            return data
        except Exception as e:
            print(f"Extraction Error: {e}")
            return {}

    async def generate_next_question(
        self,
        facts: dict,
        risk_level: str,
        current_state: InterviewState,
        confidence: ConfidenceLevel,
        missing_facts: list,
        warnings: list = None,
        obligations: list = None,
        last_updated_fact_key: str = None,
        topic_ask_count: dict = None,
        stuck_on_topic: str = None,
    ):
        """
        The 'Interviewer': Decides what to ask next based on state machine and missing info.
        Context-aware: prioritizes the topic the user just spoke about; only then looks for next gap in order.
        Uses dialogue memory (topic_ask_count) and stuck detection to force multiple-choice or expert pivot.
        """
        topic_ask_count = topic_ask_count or {}
        stuck_on_topic = stuck_on_topic or ""
        try:
            # Import obligation mapper for universal gap detection
            from core.obligation_mapper import is_negative_value, is_planned_value

            # Topic closed = do not ask again (sidebar shows planned_remediation / resolved)
            RESOLVED_STATUSES = ["present", "planned_remediation", "future_implementation", "mitigated", "planned", "met"]
            # Filter out completed items: do not generate a question for these
            COMPLETED_OBLIGATION_STATUSES = ["present", "planned", "mitigated", "planned_remediation", "met"]

            HIGH_RISK_TOPIC_ORDER = ["human_oversight", "data_governance", "accuracy_robustness", "record_keeping"]
            FACT_KEY_TO_LABEL = {
                "human_oversight": "Article 14 (Human Oversight)",
                "data_governance": "Article 10 (Data Governance)",
                "accuracy_robustness": "Article 15 (Accuracy & Robustness)",
                "record_keeping": "Article 12 (Record Keeping)",
            }
            CODE_TO_FACT = {
                "ART_14_OVERSIGHT": "human_oversight",
                "ART_10": "data_governance",
                "ART_15": "accuracy_robustness",
                "ART_12": "record_keeping",
            }
            obligation_status_by_fact = {}
            if obligations:
                for ob in obligations:
                    if isinstance(ob, dict):
                        code = ob.get("code", "")
                        status = (ob.get("status") or "").strip().lower()
                    else:
                        code = str(ob)
                        status = "pending"
                    fk = CODE_TO_FACT.get(code)
                    if fk:
                        obligation_status_by_fact[fk] = status

            # Addressed = do not ask again (status in ['present', 'planned'] or fact/resolution present)
            ADDRESSED_STATUSES = ["present", "planned", "planned_remediation", "met", "mitigated"]

            # Next-best: are all high-priority obligations completed? (then move to closing phase)
            all_high_priority_completed = False
            if risk_level == "HIGH":
                def _obligation_addressed(fk: str) -> bool:
                    status = obligation_status_by_fact.get(fk)
                    if status in COMPLETED_OBLIGATION_STATUSES or status in ADDRESSED_STATUSES:
                        return True
                    val = (facts.get(fk) or "").strip().lower()
                    if fk == "human_oversight":
                        return val in ["present", "planned", "yes"] or (facts.get("remediation_accepted") or "").strip().lower() == "yes"
                    return val in ["yes", "present", "planned", "planned_remediation"]
                all_high_priority_completed = all(_obligation_addressed(fk) for fk in HIGH_RISK_TOPIC_ORDER)

            def _topic_resolved(fact_key: str, f: dict) -> bool:
                """Topic is DONE for interview flow: present, planned, or obligation status in RESOLVED_STATUSES."""
                if obligation_status_by_fact.get(fact_key) in RESOLVED_STATUSES:
                    return True
                val = (f.get(fact_key) or "").strip().lower()
                if fact_key == "human_oversight":
                    return val in ["present", "planned"] or (f.get("remediation_accepted") or "").strip().lower() == "yes"
                return val in ["yes", "present", "planned_remediation", "planned"] or (f.get(f"{fact_key}_remediation") or "").strip().lower() == "yes"

            def _success_prefix_for_next_topic(next_fact_key: str) -> str:
                """If user just accepted remediation (previous turn), confirm and introduce next topic."""
                if not last_updated_fact_key or last_updated_fact_key == next_fact_key:
                    return ""
                if last_updated_fact_key not in HIGH_RISK_TOPIC_ORDER or next_fact_key not in HIGH_RISK_TOPIC_ORDER:
                    return ""
                if not _topic_resolved(last_updated_fact_key, facts):
                    return ""
                label = FACT_KEY_TO_LABEL.get(next_fact_key, next_fact_key.replace("_", " ").title())
                return f"Understood. That mitigation plan is noted. Moving on to {label}...\n\n"

            def _topic_has_gap(fact_key: str, f: dict) -> bool:
                """Topic still has a compliance gap (not resolved)."""
                if _topic_resolved(fact_key, f):
                    return False
                val = (f.get(fact_key) or "").strip().lower()
                if fact_key == "human_oversight":
                    return val in ["absent", "no", "partial"]
                return val in ["absent", "no", ""]

            # 1. CONTEXT-AWARE: If user just spoke about a topic and it still has a gap, address THAT topic only (no jump to Article 14).
            # Skip canned question if we're stuck on this topic (let LLM do multiple-choice or pivot)
            if risk_level == "HIGH" and last_updated_fact_key and last_updated_fact_key in HIGH_RISK_TOPIC_ORDER:
                if _topic_has_gap(last_updated_fact_key, facts) and stuck_on_topic != last_updated_fact_key:
                    CRITICAL_OBLIGATIONS_ACTIVE = {
                        "human_oversight": "⚠️ Critical Gap: Article 14 requires human oversight for high-risk systems. Your system is currently non-compliant. Can you implement a 'Human-in-the-loop' review step?",
                        "data_governance": "⚠️ Critical Gap: Article 10 requires data governance and bias mitigation. Your training data must be representative. Can you implement bias testing?",
                        "accuracy_robustness": "⚠️ Critical Gap: Article 15 requires accuracy monitoring. Can you implement performance logging?",
                        "record_keeping": "⚠️ Critical Gap: Article 12 requires automatic logging. Can you enable system logs?",
                    }
                    msg = CRITICAL_OBLIGATIONS_ACTIVE.get(last_updated_fact_key)
                    if msg:
                        print(f"[CONTEXT-AWARE] Returning remediation for active topic: {last_updated_fact_key}")
                        return msg

            # 2. SEQUENTIAL GAP HANDLING: Filter out completed items (status present/planned/mitigated or fact yes/present).
            if risk_level == "HIGH" and obligations:
                if all_high_priority_completed:
                    print("[CLOSING] All high-priority obligations are present/planned; moving to closing phase.")
                else:
                    for fact_key in HIGH_RISK_TOPIC_ORDER:
                        ob_status = obligation_status_by_fact.get(fact_key)
                        if ob_status in RESOLVED_STATUSES or ob_status in COMPLETED_OBLIGATION_STATUSES:
                            print(f"Skipping {FACT_KEY_TO_LABEL.get(fact_key, fact_key)} because status is {ob_status}")
                            continue
                        fact_value = (facts.get(fact_key) or "").strip().lower()
                        if fact_value in ["yes", "present", "planned", "planned_remediation"]:
                            print(f"Skipping {FACT_KEY_TO_LABEL.get(fact_key, fact_key)} because fact is '{fact_value}' (addressed).")
                            continue
                        if fact_value == "partial_or_unclear":
                            print(f"[EXPERT] {FACT_KEY_TO_LABEL.get(fact_key, fact_key)} is partial_or_unclear; not repeating question—LLM will acknowledge, explain law, suggest improvement.")
                            continue
                        if fact_key == "human_oversight" and (facts.get("remediation_accepted") or "").strip().lower() == "yes":
                            print(f"Skipping {FACT_KEY_TO_LABEL.get(fact_key, fact_key)} because remediation accepted (addressed).")
                            continue
                        remediation_key = "remediation_accepted" if fact_key == "human_oversight" else f"{fact_key}_remediation"
                        remediation_value = (facts.get(remediation_key) or "").strip().lower()
                        if is_planned_value(fact_value) or fact_value in ["planned_remediation", "planned"] or remediation_value == "yes":
                            continue  # DONE - do not ask again
                        if fact_key == "human_oversight" and fact_value in ["absent", "no", "partial"]:
                            if remediation_value == "" and stuck_on_topic != "human_oversight":
                                prefix = _success_prefix_for_next_topic("human_oversight")
                                return prefix + "⚠️ Critical Gap: Article 14 requires human oversight for high-risk systems. Your system is currently non-compliant. Can you implement a 'Human-in-the-loop' review step?"
                            break  # already asked or refused; Article 14 termination handled in router
                        if fact_value in ["absent", "no"]:
                            if stuck_on_topic == fact_key:
                                break  # let LLM handle multiple-choice or pivot
                            ob_info = {
                                "data_governance": "⚠️ Critical Gap: Article 10 requires data governance and bias mitigation. Your training data must be representative. Can you implement bias testing?",
                                "accuracy_robustness": "⚠️ Critical Gap: Article 15 requires accuracy monitoring. Can you implement performance logging?",
                                "record_keeping": "⚠️ Critical Gap: Article 12 requires automatic logging. Can you enable system logs?",
                            }
                            if remediation_value == "" and fact_key in ob_info:
                                prefix = _success_prefix_for_next_topic(fact_key)
                                return prefix + ob_info[fact_key]
                            break  # one topic at a time
                # If we didn't return above, fall through to legacy obligation loop (for non-HIGH or other codes)
            elif obligations:
                for obligation in obligations:
                    # Handle both dict and string format obligations
                    if isinstance(obligation, dict):
                        ob_code = obligation.get('code', '')
                        ob_title = obligation.get('title', 'Unknown')
                        ob_status = (obligation.get('status') or 'PENDING').strip().lower()
                    else:
                        ob_code = str(obligation)
                        ob_title = ob_code
                        ob_status = 'pending'
                    # Filter out completed items: do not generate a question for present/planned/mitigated
                    if ob_status in RESOLVED_STATUSES or ob_status in COMPLETED_OBLIGATION_STATUSES:
                        print(f"Skipping {ob_title} because status is {ob_status}")
                        continue
                    # Check if this obligation has a gap_detected status
                    if ob_status == "gap_detected":
                        # Find corresponding fact key
                        fact_key = None
                        fact_to_ob_map = {
                            "human_oversight": "ART_14_OVERSIGHT",
                            "data_governance": "ART_10",
                            "accuracy_robustness": "ART_15",
                            "record_keeping": "ART_12",
                            "transparency": "ART_50",
                            "article_50_notice": "ART_50"
                        }
                        for fk, oc in fact_to_ob_map.items():
                            if oc == ob_code:
                                fact_key = fk
                                break
                        
                        if fact_key:
                            remediation_key = f"{fact_key}_remediation"
                            remediation_value = facts.get(remediation_key, "").lower()
                            fact_value = facts.get(fact_key, "").lower()
                            if fact_value in ["yes", "present"]:
                                print(f"Skipping {ob_title} because fact is '{fact_value}' (completed).")
                                continue
                            if is_planned_value(fact_value) or remediation_value == "yes":
                                continue
                            
                            # If remediation not yet asked, ask it
                            if not remediation_value:
                                # Dynamic warning generation - works for ANY obligation
                                article_num = ob_code.replace("ART_", "").replace("_", " ")
                                return f"⚠️ Critical Gap Detected: {ob_title} is mandatory for {risk_level} risk systems. You answered that this is absent. You cannot proceed without it. Can you implement a remediation measure?"
                            elif remediation_value == "no":
                                # User refused remediation - log gap but continue (except Article 14 which terminates)
                                if ob_code == "ART_14_OVERSIGHT":
                                    # Article 14 termination handled separately in interview.py
                                    continue
                                # For other obligations, continue assessment with gap noted
                                continue
            
            # LEGACY: CRITICAL OBLIGATIONS MAP - Keep for backward compatibility
            # Maps fact keys to their required state and remediation questions
            CRITICAL_OBLIGATIONS = {
                "human_oversight": {
                    "article": "Article 14",
                    "requirement": "human oversight",
                    "remediation_question": "⚠️ Critical Gap: Article 14 requires human oversight for high-risk systems. Your system is currently non-compliant. Can you implement a 'Human-in-the-loop' review step?",
                    "remediation_key": "remediation_accepted"  # Special key for Article 14
                },
                "data_governance": {
                    "article": "Article 10",
                    "requirement": "data governance and bias mitigation",
                    "remediation_question": "⚠️ Critical Gap: Article 10 requires data governance and bias mitigation. Your training data must be representative. Can you implement bias testing?",
                    "remediation_key": "data_governance_remediation"
                },
                "accuracy_robustness": {
                    "article": "Article 15",
                    "requirement": "accuracy monitoring",
                    "remediation_question": "⚠️ Critical Gap: Article 15 requires accuracy monitoring. Can you implement performance logging?",
                    "remediation_key": "accuracy_robustness_remediation"
                },
                "record_keeping": {
                    "article": "Article 12",
                    "requirement": "automatic logging",
                    "remediation_question": "⚠️ Critical Gap: Article 12 requires automatic logging. Can you enable system logs?",
                    "remediation_key": "record_keeping_remediation"
                }
            }
            
            # UNIVERSAL BLOCKING MECHANISM - Skip if obligation status is present/planned/mitigated or fact is yes/present.
            if risk_level == "HIGH" and not all_high_priority_completed:
                for fact_key in HIGH_RISK_TOPIC_ORDER:
                    ob_status = obligation_status_by_fact.get(fact_key)
                    if ob_status in RESOLVED_STATUSES or ob_status in COMPLETED_OBLIGATION_STATUSES:
                        print(f"Skipping {FACT_KEY_TO_LABEL.get(fact_key, fact_key)} because status is {ob_status}")
                        continue
                    obligation_info = CRITICAL_OBLIGATIONS.get(fact_key)
                    if not obligation_info:
                        continue
                    fact_value = (facts.get(fact_key) or "").strip().lower()
                    if fact_value in ["yes", "present", "planned", "planned_remediation"]:
                        print(f"Skipping {FACT_KEY_TO_LABEL.get(fact_key, fact_key)} because fact is '{fact_value}' (addressed).")
                        continue
                    if fact_value == "partial_or_unclear":
                        continue
                    if fact_key == "human_oversight" and (facts.get("remediation_accepted") or "").strip().lower() == "yes":
                        print(f"Skipping {FACT_KEY_TO_LABEL.get(fact_key, fact_key)} because remediation accepted (addressed).")
                        continue
                    remediation_key = obligation_info["remediation_key"]
                    remediation_value = (facts.get(remediation_key) or "").strip().lower()
                    if remediation_value == "yes":
                        continue
                    is_negative = fact_value in ["absent", "no"] or (fact_key == "human_oversight" and fact_value == "partial")
                    if not is_negative:
                        continue
                    if fact_key == "human_oversight":
                        continue  # Article 14 handled in sequential block and in prompt
                    if remediation_value == "" and stuck_on_topic != fact_key:
                        print(f"[BLOCKING] {obligation_info['article']} blocking activated for {fact_key}")
                        prefix = _success_prefix_for_next_topic(fact_key)
                        return prefix + obligation_info["remediation_question"]
                    break  # One topic at a time; rest handled in prompt
            
            state_desc = StateMachine.get_state_description(current_state)
            confidence_msg = StateMachine.get_confidence_message(confidence, risk_level)
            
            # Build context about what we're looking for
            missing_context = ""
            if missing_facts:
                fact_descriptions = {
                    "domain": "the area or industry where this AI system is used",
                    "role": "whether you are building this system (provider) or using an existing one (deployer)",
                    "purpose": "the specific goal or task this AI system performs",
                    "data_type": "what kind of data the system processes (personal, biometric, anonymous)",
                    "automation": "whether decisions are fully automated or have human oversight",
                    "context": "where the system is deployed (workplace, public space, school, etc.)",
                    "human_oversight": "whether human reviewers check the AI's decisions before they take effect"
                }
                missing_context = ", ".join([fact_descriptions.get(key, key) for key in missing_facts[:2]])

            # Check for prohibited practices that need exemption probe
            needs_exemption_probe = risk_level == "PENDING_PROHIBITED"
            
            # Check if transparency is already confirmed for LIMITED risk (prevent loops)
            transparency_confirmed = False
            if risk_level == "LIMITED":
                transparency_status = facts.get("transparency", "").lower()
                article_50_status = facts.get("article_50_notice", "").lower()
                if transparency_status == "present" or article_50_status == "yes":
                    transparency_confirmed = True
            
            # Check for missing mandatory topics for HIGH risk systems
            missing_mandatory_topics = []
            high_risk_complete = False
            report_ready = False  # All obligations addressed (Art 14, 10, 15, 12) → suggest compliance report
            if risk_level == "HIGH":
                obligations_list = obligations if obligations else []
                missing_mandatory_topics = get_missing_mandatory_topics(facts, obligations_list)
                high_risk_complete = can_complete_high_risk_assessment(facts, obligations_list)
                report_ready = all_high_priority_completed and (current_state == InterviewState.ASSESSMENT or high_risk_complete)
            
            # Check for critical compliance gaps (only if not UNACCEPTABLE)
            compliance_gaps = []
            if risk_level == "HIGH":
                # Only add compliance gap if not already blocking (Article 14 guardrail handles it)
                article_14_blocking_check = facts.get("human_oversight", "").lower() in ["absent", "no", "partial"]
                if article_14_blocking_check and facts.get("automation") == "fully_automated":
                    compliance_gaps.append("CRITICAL: High-risk systems require human oversight under Article 14. Fully automated decisions without human review violate compliance requirements.")
                if facts.get("special_category_data") == "yes" and facts.get("data_type") != "sensitive_personal":
                    compliance_gaps.append("WARNING: System processes special category personal data (ethnic origin, health, etc.) which requires enhanced protections.")
                # Flag "no" answers for mandatory topics as compliance gaps (but don't keep asking)
                if facts.get("data_governance") in ["no", "absent"]:
                    compliance_gaps.append("COMPLIANCE GAP: Data governance measures (bias mitigation, training data quality) are required under Article 10 for high-risk systems.")
                if facts.get("accuracy_robustness") in ["no", "absent"]:
                    compliance_gaps.append("COMPLIANCE GAP: Accuracy, robustness, and security monitoring are required under Article 15 for high-risk systems.")
                if facts.get("record_keeping") in ["no", "absent"]:
                    compliance_gaps.append("COMPLIANCE GAP: Record keeping and logging are required under Article 12 for high-risk systems.")
            
            # COMPLIANCE GUARDRAIL - Article 14 Human Oversight Blocking Logic (RUNS FIRST)
            # This check must run BEFORE any other question logic to catch critical non-compliance
            article_14_blocking = False
            remediation_question_asked = False
            remediation_response = None
            
            if risk_level == "HIGH":
                human_oversight_state = facts.get("human_oversight", "").lower()
                remediation_accepted = facts.get("remediation_accepted", "").lower()
                
                # Check if human oversight is absent, partial, or vague (partial_or_unclear). Article 14: partial = non-compliant; partial_or_unclear = expert guidance, no repeat.
                if human_oversight_state in ["absent", "no", "partial", "partial_or_unclear"]:
                    article_14_blocking = True
                    # Check if we've already asked the remediation question
                    if remediation_accepted == "":
                        remediation_question_asked = True  # Need to ask remediation question
                    elif remediation_accepted == "no":
                        # User refused remediation - TERMINATE
                        article_14_blocking = True  # Keep blocking
                        remediation_response = "refused"
                    elif remediation_accepted == "yes":
                        article_14_blocking = False
                        remediation_response = "accepted"
                    elif human_oversight_state == "partial_or_unclear":
                        article_14_blocking = True
                        remediation_response = "partial_or_unclear"
            
            # Extract blocked message from warnings if UNACCEPTABLE
            blocked_message = ""
            if risk_level == "UNACCEPTABLE" and warnings:
                for warning in warnings:
                    if "BLOCKED:" in warning:
                        blocked_message = warning.replace("BLOCKED:", "").strip()
                        break

            # RAG context: inject EU AI Act excerpt for the topic the user just spoke about (for expert guidance)
            rag_context = ""
            if last_updated_fact_key and last_updated_fact_key in HIGH_RISK_TOPIC_ORDER:
                rag_context = get_article_context_for_topic(last_updated_fact_key)
            partial_or_unclear_topic = None
            for fk in HIGH_RISK_TOPIC_ORDER:
                if (facts.get(fk) or "").strip().lower() == "partial_or_unclear":
                    partial_or_unclear_topic = fk
                    if not rag_context:
                        rag_context = get_article_context_for_topic(fk)
                    break

            # Format variables for prompt (ensure they're strings)
            article_14_blocking_str = str(article_14_blocking)
            remediation_question_asked_str = str(remediation_question_asked)
            remediation_response_str = str(remediation_response) if remediation_response else "None"
            topic_ask_count_str = json.dumps(topic_ask_count) if topic_ask_count else "{}"
            stuck_on_topic_str = stuck_on_topic or "None"

            prompt = f"""
        You are an EU AI Act Expert Consultant. Your goal is to determine if the user has met the legal threshold for each obligation. Use the facts and the law excerpt below. If their answer is insufficient, do NOT simply repeat the question—explain why it is insufficient and offer a concrete suggestion.
        
        EU AI ACT CONTEXT (relevant to current topic):
        {rag_context if rag_context else "None — use your knowledge of the EU AI Act."}
        
        You are conducting a structured interview.
        
        CURRENT STATE: {state_desc} ({current_state.value})
        - Known Facts: {json.dumps(facts, indent=2)}
        - Assessed Risk Level: {risk_level}
        - Missing Information: {missing_facts}
        - Compliance Gaps Detected: {compliance_gaps if compliance_gaps else "None"}
        - Needs Exemption Probe: {needs_exemption_probe}
        - Transparency Confirmed (for LIMITED risk): {transparency_confirmed}
        - Missing Mandatory Topics (for HIGH risk): {missing_mandatory_topics if missing_mandatory_topics else "None - All topics covered"}
        - High Risk Assessment Complete: {high_risk_complete}
        - Report Ready (all obligations addressed; suggest generating compliance report): {report_ready}
        - Blocked Message (if UNACCEPTABLE): {blocked_message if blocked_message else "None"}
        - Article 14 Blocking (CRITICAL): {article_14_blocking_str}
        - Remediation Question Asked: {remediation_question_asked_str}
        - Remediation Response: {remediation_response_str}
        - Active Topic (topic the user just spoke about): {last_updated_fact_key or "None"}
        - Topic in partial_or_unclear state (vague/informal answer): {partial_or_unclear_topic or "None"}
        - DIALOGUE MEMORY (times we have asked about each topic): {topic_ask_count_str}
        - STUCK ON TOPIC (user still has gap here and we have asked 2+ times): {stuck_on_topic_str}
        
        DIALOGUE MEMORY RULE: If "Stuck on topic" is set (we have asked that topic 2+ times and it is still unresolved), do NOT ask the same question again. You MUST do one of:
        (A) MULTIPLE-CHOICE: Offer 3 concrete options so the user can pick one. Use this format: "To move forward, which best describes your situation? A) [concrete option, e.g. formal human review each release]. B) [another option, e.g. sampling-based review]. C) [e.g. Let's cover data governance first and circle back to this]." Then wait for their choice.
        (B) PIVOT: Move to the next mandatory topic and say you will circle back (see Expert Pivot below).
        
        EXPERT PIVOT (you are ALLOWED and ENCOURAGED): If the user is stuck on Article 14 (human oversight), move to Article 10 (Data Governance) to keep the conversation flowing. Say: "It seems we're stuck on the technicalities of Article 14. To keep things moving, let's jump to Article 10 (Data Governance)—we can circle back to formalizing oversight later." Then ask one question about data governance (bias mitigation, training data quality). For any stuck topic, pivot to the next article in order (14 → 10 → 15 → 12) and return to the stuck topic later.
        
        EXPERT CONSULTATION MODE (when a topic is "partial_or_unclear" or user gave a vague answer):
        - Do NOT repeat the same question. The user has already responded; their answer was classified as vague or informal.
        - DO: (1) Acknowledge their effort ("I see you're thinking about [topic] / have something in place informally"). (2) Explain the legal requirement in 1-2 sentences, referencing the EU AI Act excerpt above. (3) Suggest a specific improvement ("For example, you could formalize a three-tier review process..." or "Many companies document bias testing quarterly..."). (4) Optionally offer a "Consultant's Suggestion": "Most companies in your position implement [X]. Would you like to see how that could work for you?"
        - PIVOT OPTION: If the user seems stuck on one topic (e.g. multiple vague answers on the same point), you MAY pivot: "It seems we're circling the technicalities of [Article X]. To keep things moving, let's jump to [next topic, e.g. Article 10 Data Governance], and we can circle back to formalizing [topic] later." Then ask about the next mandatory topic once.
        - Status for sidebar: Treat "partial_or_unclear" as Under Review; treat a clear commitment ("we will do X") as Planned.
        
        CONTEXT-AWARE RULES (CRITICAL - prevents zombie loop):
        - If "Active Topic" is set (e.g. data_governance), address THAT topic only. Do NOT jump back to Article 14 (human oversight) when the user is discussing another topic.
        - Only after the active topic is resolved (present/planned/planned_remediation) should you move to the next topic in order.
        - Any topic marked "planned_remediation" or "planned" in Known Facts is DONE - do NOT ask about it again.
        
        INSTRUCTIONS - PRIORITY ORDER (STRICT - DO NOT SKIP):
        
        PRIORITY 0 (HIGHEST - COMPLIANCE GUARDRAIL): Article 14 Human Oversight Blocking Logic
        - This MUST run BEFORE any other priority. Check "Article 14 Blocking" flag above.
        - Under Article 14, ONLY "present" (full human oversight) or "planned" (after remediation) is compliant. "partial" oversight is NON-COMPLIANT and must trigger the same blocking as "absent".
        - IF risk_level == "HIGH" AND human_oversight in ["absent", "no", "partial", "partial_or_unclear"]:
          - IF "Remediation Response" is "partial_or_unclear" (user gave a vague answer): Do NOT repeat the question. Follow EXPERT CONSULTATION MODE: acknowledge, explain the legal requirement using the EU AI Act context above, suggest a specific improvement, and optionally offer a Consultant's Suggestion or pivot to another topic.
          - IF "Remediation Question Asked" is False (we haven't asked yet):
            - IMMEDIATELY ask: "⚠️ Critical Gap: Article 14 requires human oversight for high-risk systems. Your system is currently non-compliant. Can you implement a 'Human-in-the-loop' review step?"
            - DO NOT ask any other questions until this is resolved.
            - DO NOT proceed to other topics.
          - IF "Remediation Response" is "accepted" (user said YES):
            - human_oversight should be set to "planned" (check Known Facts)
            - Respond: "Good. I have noted that oversight measures will be implemented. This addresses the Article 14 requirement. Let's move to Article 10 (Data Governance)."
            - Proceed to next mandatory topic (data_governance).
          - IF "Remediation Response" is "refused" (user said NO):
            - TERMINATE THE ASSESSMENT IMMEDIATELY.
            - Respond EXACTLY: "⛔ Assessment Terminated. You have confirmed that this High-Risk system will NOT have human oversight. This is a direct violation of Article 14 of the EU AI Act. This system cannot be legally deployed. I am generating your Non-Compliance Report now."
            - DO NOT ask any more questions.
            - The system will automatically generate a Non-Compliance Report.
        - FLIP-FLOP DETECTION: If user was previously compliant (human_oversight was "present" or "planned") but now says "we removed it" or "we eliminated oversight", the blocking logic MUST re-engage immediately.
        - This blocking check runs on EVERY turn - if human_oversight is "absent", "no", or "partial" at any point, the guardrail activates.
        
        PRIORITY 1: If Risk Level is "UNACCEPTABLE":
        - STOP asking compliance questions (oversight, data, etc.)
        - Issue a firm but educational "Prohibited Practice Warning"
        - Use the exact "Blocked Message" provided above. If a blocked message exists, use it verbatim. Do NOT modify it or add any mention of "human oversight" or "compliance measures".
        - If no blocked message is provided, construct a message stating: "❌ Assessment Halted. This use case is illegal in the EU under Article 5 due to [specific prohibited practice]. I cannot proceed with generating a compliance profile for a banned use case."
        - CRITICAL: Article 5 bans are PER SE (inherently illegal) - they have NOTHING to do with human oversight, data protection, or any other compliance measure. The system is illegal regardless of these factors.
        - Do NOT mention "human oversight", "compliance measures", or any conditional factors in the rejection message. The ban is absolute and unconditional.
        - Do NOT ask any follow-up questions about compliance.
        - End the conversation professionally.
        
        PRIORITY 2: If Risk Level is "PENDING_PROHIBITED" (needs exemption probe):
        - Ask ONE clarifying exemption question
        - For emotion recognition in education/workplace: "Wait. Emotion recognition in schools/workplaces is generally banned under Article 5. Is this system intended for a specific medical or safety purpose (e.g., detecting narcolepsy, monitoring for seizures, safety alerts)? If not, this is a Prohibited Practice."
        - For social scoring: "Wait. Social scoring systems are generally banned under Article 5. Is this system intended for a specific legitimate purpose? If not, this is a Prohibited Practice."
        - Do NOT ask about compliance requirements (oversight, data, etc.) until exemption is resolved.
        - Be firm but educational - explain why it's banned, but give them a chance to clarify if there's a legitimate exemption.
        
        PRIORITY 2.5: If Risk Level is "LIMITED" (e.g., Chatbots/Deepfakes):
        - CRITICAL LOOP PREVENTION: Check the "Transparency Confirmed" flag above. If it is True, transparency is already confirmed - do NOT ask about transparency again.
        - Also check Known Facts: If "transparency": "present" or "article_50_notice": "yes" is already in Known Facts, do NOT ask about transparency again.
        - If transparency is already confirmed (flag is True OR "present"/"yes" in Known Facts), respond: "Based on the information provided, your system appears to align with Article 50 transparency requirements for LIMITED risk AI systems. Our analysis indicates your system is likely consistent with the disclosure obligations. Would you like to generate a preliminary Compliance Report for human review?"
        - If transparency is NOT yet confirmed (flag is False AND not "present"/"yes" in Known Facts):
          - Do NOT ask for clarification on purpose, domain, or other details.
          - Immediately trigger the Article 50 transparency check - this is the ONLY compliance requirement for LIMITED risk systems.
          - For chatbots/interaction systems: Ask: "Under Article 50, you must disclose that users are interacting with an AI. Is this transparency notice clearly visible to users?"
          - For content generation/deepfakes: Ask: "Under Article 50, AI-generated content must be clearly marked. Is this watermarking or disclosure mechanism in place?"
        - Do NOT ask about human oversight, data types, automation, or other compliance questions - LIMITED risk ONLY requires Article 50 transparency.
        - Once transparency is confirmed, suggest generating a preliminary Compliance Report for human review.
        
        PRIORITY 3: If Risk Level is "HIGH":
        - MANDATORY CHECKLIST ENFORCEMENT: Check "Missing Mandatory Topics" above. This is CRITICAL.
        - If "Missing Mandatory Topics" is NOT empty, you MUST ask about the FIRST missing topic before doing anything else.
        - DO NOT suggest generating a preliminary Compliance Report if there are missing mandatory topics.
        - Priority order for missing topics (ask about the FIRST one in the list):
          1. human_oversight (if missing) - Ask: "Since this is a High Risk system, we must ensure human oversight under Article 14. Do you have human reviewers who can stop or override the AI's decisions?"
          2. data_governance (if missing) - Ask: "Since this is a High Risk system, we must ensure data quality under Article 10. How do you mitigate bias in your training data (e.g., ensuring fair representation of different demographics)?"
          3. accuracy_robustness (if missing) - Ask: "Since this is a High Risk system, we must ensure accuracy and robustness under Article 15. How do you monitor error rates and ensure the system's security and reliability?"
          4. record_keeping (if missing) - Ask: "Since this is a High Risk system, we must ensure proper record keeping under Article 12. Do you maintain logs of the AI system's operations and decisions?"
        - Ask ONE missing topic at a time. Do NOT skip mandatory topics or ask about other things.
        
        - HANDLING "NO" ANSWERS - BE CONVERSATIONAL AND EXPLORATORY:
          When a user answers "no" to a mandatory topic question, DO NOT just flag it as a gap and move on. Instead:
          1. Ask follow-up questions to understand the context and explore alternatives:
             - For "human_oversight": "no" → Ask: "I understand you don't currently have human oversight. Is this something you're planning to implement? Are there any review mechanisms in place, even if not formal?"
             - For "data_governance": "no" → Ask: "I see you don't have formal bias mitigation measures yet. Have you done any data quality checks or demographic analysis? Are there plans to address this?"
             - For "accuracy_robustness": "no" → Ask: "I understand monitoring isn't in place yet. Do you have any testing or validation processes? Are there plans to implement error rate tracking?"
             - For "record_keeping": "no" → Ask: "I see logging isn't currently implemented. Do you have any documentation or audit trails? Is this something you're planning to add?"
          2. Be understanding and conversational - acknowledge their situation, explore what they DO have, and understand their plans.
          3. After 1-2 follow-up questions, if they still confirm "no" or don't have alternatives, acknowledge the compliance gap professionally and move to the next topic.
          4. DO NOT loop - if you've already asked 1-2 follow-up questions about a topic and they've confirmed "no", move on to the next mandatory topic.
        
        - CRITICAL LOOP PREVENTION: 
          - If you've already asked about a mandatory topic AND asked 1-2 follow-up questions after a "no" answer, do NOT ask about it again.
          - A topic is "addressed" if: (a) it's "yes", OR (b) it's "no" AND you've asked follow-up questions.
          - Only move to the next topic after you've explored the current one with follow-up questions (if they said "no").
        
        - ONLY suggest generating a preliminary Compliance Report for human review if "High Risk Assessment Complete" is True (all mandatory topics covered, even if some are "no") AND you're in ASSESSMENT state.
        
        PRIORITY 4: If Risk Level is HIGH and all mandatory topics are covered:
        - Provide a clear but professional summary (1 sentence).
        - Check the Known Facts: If a fact is already present (even if it's "no"), do NOT ask about it again.
        - If all mandatory topics are confirmed, suggest generating a preliminary Compliance Report for human review.
        
        PRIORITY 5: If "Report Ready" is True (all obligations for Articles 14, 10, 15, 12 addressed):
        - Do NOT ask any more compliance questions.
        - Give a brief positive summary (1-2 sentences) and say: "Your assessment is complete. You can now generate a Compliance Report for human review using the 'Download Report' button. The report will summarize your system's risk level and obligations."
        - Keep the tone smooth and professional so the user can complete the full assessment and obtain the report.
        
        PRIORITY 6: If all critical information is collected and we're in ASSESSMENT state (and for HIGH risk, all mandatory topics are covered):
        - Suggest generating a preliminary Compliance Report for human review.
        
        CRITICAL RULE - Natural Conversation Flow:
        - When a user says "no" to a question, ask 1-2 follow-up questions to understand their situation better before moving on.
        - Be conversational and explore alternatives - don't just flag it as unacceptable.
        - After exploring a topic (even if the answer is "no"), move to the next topic naturally.
        - Avoid loops: If you've already asked about a topic AND asked follow-up questions, do NOT ask about it again.
        - Only ask about facts that are completely absent from Known Facts, or facts that are "no" but haven't been explored with follow-up questions yet.
        - A "no" answer should trigger exploration, not immediate rejection - understand the context first.
        
        IMPORTANT:
        - Be concise (2-3 sentences total, unless addressing a critical gap or prohibited practice).
        - Do not lecture or provide legal advice.
        - Be conversational and helpful, but firm when blocking prohibited practices.
        - If confidence is LOW or MEDIUM, acknowledge that the assessment may change.
        """
        
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content="Generate the next question for the user.")
            ]
            
            # Call LLM to generate response
            try:
                res = await self.llm.ainvoke(messages)
                response_text = res.content.strip()
                
                # Append confidence message if not in ASSESSMENT state
                if current_state != InterviewState.ASSESSMENT and confidence != ConfidenceLevel.HIGH:
                    response_text += f"\n\n{confidence_msg}"
                
                return response_text
            except Exception as e:
                # Log the actual error for debugging
                print(f"[ERROR] Question Generation Error: {e}")
                print(f"[ERROR] Error type: {type(e).__name__}")
                import traceback
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
                # Return fallback message instead of crashing
                return "I apologize, but I encountered an error processing your response. Could you please clarify your last answer? This will help me continue the assessment."
        
        except Exception as e:
            # Outer try-catch for any errors in the entire function
            print(f"[CRITICAL ERROR] generate_next_question failed: {e}")
            print(f"[CRITICAL ERROR] Error type: {type(e).__name__}")
            import traceback
            print(f"[CRITICAL ERROR] Full traceback: {traceback.format_exc()}")
            # Return safe fallback message
            return "I apologize, but I encountered an error processing your response. Could you please clarify your last answer? This will help me continue the assessment."