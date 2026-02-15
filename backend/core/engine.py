import os
import json
from dotenv import load_dotenv # <--- IMPORT THIS
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from core.risk_rules import evaluate_compliance_state
from core.state_machine import StateMachine, InterviewState, ConfidenceLevel
from core.high_risk_checklist import get_missing_mandatory_topics, get_topic_question, can_complete_high_risk_assessment
from core.eu_ai_act_context import get_article_context_for_topic, get_article_context_for_query
from core.vector_store import identify_relevant_articles

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
            temperature=0.3
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

        ANTI-MANIPULATION GUARDRAIL (CRITICAL - prevents users from gaming the system):
        Users may try to skip the compliance process by giving blanket affirmations like:
        - "Yes we have all of that", "We're fully compliant", "Just give me the green light"
        - "We have oversight, data governance, everything", "Yes to all"
        - "Can you just mark us as compliant?", "Skip the questions"
        
        RULES:
        1. A compliance topic (human_oversight, data_governance, accuracy_robustness, record_keeping) can ONLY be set to "yes" or "present" if the user has described a SPECIFIC MEASURE for that topic. Examples of valid evidence:
           - human_oversight: "We have a senior ML engineer who reviews every model output before it goes to the client" → "present"
           - data_governance: "We run quarterly bias audits using Fairlearn and check demographic parity" → "yes"
           - accuracy_robustness: "We have a monitoring dashboard that tracks prediction drift and error rates weekly" → "yes"
           - record_keeping: "All model inputs and outputs are logged in our Elasticsearch cluster with 12-month retention" → "yes"
        2. If the user gives a BLANKET AFFIRMATION without describing any specific measure, set ALL undiscussed compliance topics to "partial_or_unclear" and set their confidence_scores to 35.
        3. If the user tries to set MULTIPLE compliance topics to "yes" in a single message without providing specific details for EACH one, set the ones without specific details to "partial_or_unclear".
        4. The user saying "yes" to a question about a specific topic IS valid if the question was specifically about that topic and the answer addresses it. But "yes to everything" is NOT valid.
        5. Do NOT mark a topic as "yes" or "present" just because the user WANTS to be compliant. They must DEMONSTRATE compliance with specifics.

        USER INTENT DETECTION (CRITICAL for conversation flow):
        - "parked_topic": If the user EXPLICITLY says they want to move on from a topic or stop discussing it (e.g., "I'm done with Article 10", "let's move on from data governance", "skip this for now", "I don't want to talk about that right now", "we're done with that", "next topic please"), extract the compliance topic key being parked (e.g., "data_governance", "human_oversight", "accuracy_robustness", "record_keeping"). Only set this when the user EXPLICITLY asks to move on — not when they simply finish answering.
        - "user_asked_about": If the user explicitly asks about a specific article, obligation, or compliance topic (e.g., "What about Article 16?", "Why is ART_16 still pending?", "Tell me about record keeping", "What do I need for Article 15?"), extract the article number or topic key they're asking about (e.g., "ART_16", "record_keeping", "Article 15"). This helps the bot address the user's actual question instead of its own priority.
        - "user_wants_report": Set to "yes" if the user explicitly asks for the compliance report, green light, or to finish the assessment (e.g., "generate the report", "give me the green light", "download report", "let's wrap up", "I'm ready for the report", "can we generate the compliance report now?"). Set to "no" or leave unset otherwise.

        SEMANTIC CONFIDENCE (0-100) - For EVERY fact you extract, include a confidence score indicating how certain you are:
        - "confidence_scores": Object with a score for EACH key you extract. Value 0-100.
        - 90-100: User stated this explicitly and clearly (e.g., "We are in recruitment" → domain: 100).
        - 70-89: Strongly implied or inferable from context (e.g., user describes building the tool → role: 80).
        - 50-69: Partially mentioned or somewhat unclear.
        - 30-49: Vague, informal, or ambiguous (e.g., "we do it sometimes" for a compliance topic → 35).
        - 0-29: Guessed / very low confidence.
        - IMPORTANT: Include a score for EVERY key in your output, not just compliance topics. For example: domain, role, purpose, data_type, automation, context, human_oversight, data_governance, accuracy_robustness, record_keeping, transparency, etc.

        Return ONLY a raw JSON object. Do not invent facts. If unclear, ignore the key.
        Include "workflow_steps" as an array of strings whenever operational steps are mentioned or corrected.
        Include "confidence_scores" with a score for every extracted key.
        Example: {"domain": "recruitment", "role": "provider", "human_oversight": "partial_or_unclear", "confidence_scores": {"domain": 95, "role": 85, "human_oversight": 35, "data_governance": 80}, "workflow_steps": ["Resume Input", "Keyword Scan"]}
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
        conversation_history: str = "",
        workflow_steps: list = None,
        fact_confidences: dict = None,
    ):
        """
        Two-layer response generator:
        1. Deterministic logic computes a compliance DIRECTIVE (what the LLM must address)
        2. LLM generates a natural conversational response informed by the directive + conversation history

        The LLM always generates the response. Only terminal events (UNACCEPTABLE ban,
        Article 14 refusal) are hardcoded — and those are handled in interview.py, not here.
        """
        topic_ask_count = topic_ask_count or {}
        stuck_on_topic = stuck_on_topic or ""
        workflow_steps = workflow_steps or []

        try:
            from core.obligation_mapper import is_negative_value, is_planned_value

            # === CONSTANTS ===
            RESOLVED_STATUSES = ["present", "planned_remediation", "future_implementation", "mitigated", "planned", "met"]
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
            ARTICLE_INFO = {
                "human_oversight": {"article": "Article 14", "requirement": "human oversight", "short": "a human-in-the-loop review mechanism where designated personnel can override or halt AI decisions"},
                "data_governance": {"article": "Article 10", "requirement": "data governance and bias mitigation", "short": "bias testing and data quality measures for training data"},
                "accuracy_robustness": {"article": "Article 15", "requirement": "accuracy, robustness, and cybersecurity", "short": "error rate monitoring and security measures"},
                "record_keeping": {"article": "Article 12", "requirement": "record keeping and logging", "short": "automatic logging of system operations and decisions"},
            }

            # === BUILD OBLIGATION STATUS MAP ===
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

            # === HELPER FUNCTIONS ===
            all_high_priority_completed = False
            if risk_level == "HIGH":
                def _obligation_addressed(fk: str) -> bool:
                    status = obligation_status_by_fact.get(fk)
                    if status in COMPLETED_OBLIGATION_STATUSES or status in RESOLVED_STATUSES:
                        return True
                    val = (facts.get(fk) or "").strip().lower()
                    if fk == "human_oversight":
                        return val in ["present", "planned", "yes"] or (facts.get("remediation_accepted") or "").strip().lower() == "yes"
                    return val in ["yes", "present", "planned", "planned_remediation"]
                all_high_priority_completed = all(_obligation_addressed(fk) for fk in HIGH_RISK_TOPIC_ORDER)

            def _topic_resolved(fact_key: str, f: dict) -> bool:
                if obligation_status_by_fact.get(fact_key) in RESOLVED_STATUSES:
                    return True
                val = (f.get(fact_key) or "").strip().lower()
                if fact_key == "human_oversight":
                    return val in ["present", "planned"] or (f.get("remediation_accepted") or "").strip().lower() == "yes"
                return val in ["yes", "present", "planned_remediation", "planned"] or (f.get(f"{fact_key}_remediation") or "").strip().lower() == "yes"

            def _topic_has_gap(fact_key: str, f: dict) -> bool:
                if _topic_resolved(fact_key, f):
                    return False
                val = (f.get(fact_key) or "").strip().lower()
                if fact_key == "human_oversight":
                    return val in ["absent", "no", "partial"]
                return val in ["absent", "no", ""]

            # === DETERMINE COMPLIANCE DIRECTIVE ===
            # The directive tells the LLM what to do; the LLM decides HOW to say it.
            directive = ""
            directive_topic = None  # For targeted RAG context
            workflow_str = " -> ".join(workflow_steps) if workflow_steps else ""

            # Track if previous topic was just resolved (for natural transitions)
            just_resolved_topic = None
            if last_updated_fact_key and last_updated_fact_key in HIGH_RISK_TOPIC_ORDER:
                if _topic_resolved(last_updated_fact_key, facts):
                    just_resolved_topic = last_updated_fact_key

            # --- PRIORITY -1: WORKFLOW GATHERING (when in WORKFLOW state) ---
            if current_state == InterviewState.WORKFLOW:
                if not workflow_steps or len(workflow_steps) < 2:
                    domain = facts.get("domain", "their industry")
                    purpose = facts.get("purpose", "their AI system")
                    directive = (
                        f"The user has described their AI system (domain: {domain}, purpose: {purpose}) "
                        f"but we don't yet understand their operational workflow. "
                        f"Ask them to walk you through their process step-by-step: "
                        f"what data goes in, what the AI does with it, what decisions it makes, "
                        f"and what happens to the output. We need to build a clear picture of their pipeline "
                        f"so we can identify which EU AI Act articles apply at each step. "
                        f"Be specific — ask about each stage and what role the AI plays at that stage. "
                        f"For example: 'Can you walk me through the full pipeline? Starting from when data "
                        f"enters your system to when a final decision or output is delivered.'"
                    )
                else:
                    # Has some steps but may be incomplete
                    directive = (
                        f"The user has started describing their workflow: {workflow_str}. "
                        f"Ask follow-up questions to flesh out any remaining steps. Specifically ask: "
                        f"(1) Is this the complete sequence from start to finish? "
                        f"(2) At which steps does the AI make decisions vs. a human? "
                        f"(3) What happens to the output — does someone review it? "
                        f"Once the workflow is confirmed as complete, acknowledge it and tell them "
                        f"you'll now evaluate each step against the EU AI Act requirements."
                    )
                # Skip all other directive logic for WORKFLOW state

            # --- PRIORITY -0.5: USER ASKED ABOUT A SPECIFIC TOPIC ---
            # Respect user intent: if they explicitly ask about an article/obligation, address it.
            if not directive:
                user_asked = (facts.get("user_asked_about") or "").strip()
                if user_asked:
                    # Map common patterns to topic keys / labels
                    asked_topic_map = {
                        "ART_16": ("ART_16", "Article 16 (Quality Management System)"),
                        "ART_43": ("ART_43", "Article 43 (Conformity Assessment)"),
                        "ART_14": ("human_oversight", "Article 14 (Human Oversight)"),
                        "ART_10": ("data_governance", "Article 10 (Data Governance)"),
                        "ART_15": ("accuracy_robustness", "Article 15 (Accuracy & Robustness)"),
                        "ART_12": ("record_keeping", "Article 12 (Record Keeping)"),
                        "ART_50": ("transparency", "Article 50 (Transparency)"),
                        "ART_26": ("ART_26", "Article 26 (Deployer Obligations)"),
                        "Article 16": ("ART_16", "Article 16 (Quality Management System)"),
                        "Article 43": ("ART_43", "Article 43 (Conformity Assessment)"),
                        "Article 14": ("human_oversight", "Article 14 (Human Oversight)"),
                        "Article 10": ("data_governance", "Article 10 (Data Governance)"),
                        "Article 15": ("accuracy_robustness", "Article 15 (Accuracy & Robustness)"),
                        "Article 12": ("record_keeping", "Article 12 (Record Keeping)"),
                        "Article 50": ("transparency", "Article 50 (Transparency)"),
                        "record_keeping": ("record_keeping", "Article 12 (Record Keeping)"),
                        "data_governance": ("data_governance", "Article 10 (Data Governance)"),
                        "human_oversight": ("human_oversight", "Article 14 (Human Oversight)"),
                        "accuracy_robustness": ("accuracy_robustness", "Article 15 (Accuracy & Robustness)"),
                    }
                    matched = asked_topic_map.get(user_asked)
                    if matched:
                        topic_key, topic_label = matched
                        # Check if we have an obligation for this
                        ob_status = "unknown"
                        if obligations:
                            for ob in obligations:
                                if isinstance(ob, dict) and (ob.get("code") == topic_key or ob.get("code") == user_asked):
                                    ob_status = (ob.get("status") or "PENDING").strip().lower()
                                    break
                        fact_val = (facts.get(topic_key) or "not yet discussed").strip().lower()
                        directive = (
                            f"The user specifically asked about {topic_label}. Address their question directly. "
                            f"Current status: obligation='{ob_status}', fact='{fact_val}'. "
                            f"Explain what this article requires, what their current status means, and what "
                            f"specific steps they need to take to move it from '{ob_status}' to compliant. "
                            f"Be helpful and specific. After answering, you can return to the normal assessment flow."
                        )
                        if topic_key in HIGH_RISK_TOPIC_ORDER:
                            directive_topic = topic_key

            # --- PRIORITY -0.25: VERIFY LOW-CONFIDENCE FACTS ---
            # Before using facts for compliance decisions, confirm any fact the system
            # is unsure about.  Only fires in CHECKPOINT / ASSESSMENT states (during
            # INTAKE / DISCOVERY facts are still being gathered, so it's too early).
            if not directive and fact_confidences and current_state in [
                InterviewState.CHECKPOINT, InterviewState.ASSESSMENT
            ]:
                from core.obligation_mapper import CONFIDENCE_THRESHOLD
                _important_keys = [
                    "domain", "role", "purpose", "data_type", "automation",
                    "context", "human_oversight", "data_governance",
                    "accuracy_robustness", "record_keeping", "transparency",
                ]
                _fact_descriptions = {
                    "domain": "the industry / sector",
                    "role": "whether they are a provider or deployer of the AI system",
                    "purpose": "what the AI system is used for",
                    "data_type": "what type of data the system processes",
                    "automation": "the level of automation in decision-making",
                    "context": "the deployment context",
                    "human_oversight": "human oversight arrangements",
                    "data_governance": "data governance practices",
                    "accuracy_robustness": "accuracy and robustness measures",
                    "record_keeping": "record-keeping procedures",
                    "transparency": "transparency measures",
                }
                for _key in _important_keys:
                    _val = facts.get(_key, "")
                    _conf = fact_confidences.get(_key, 100)
                    if _val and _conf < CONFIDENCE_THRESHOLD:
                        _desc = _fact_descriptions.get(_key, _key)
                        directive = (
                            f"We recorded {_desc} as '{_val}' but our confidence is "
                            f"low ({_conf}/100). Before proceeding with compliance "
                            f"evaluation, naturally confirm this with the user. "
                            f"Don't sound like you're re-asking from scratch — say "
                            f"something like 'Just to make sure I have this right…' "
                            f"or 'I want to double-check…' and ask about this ONE "
                            f"fact only. Keep it brief and conversational."
                        )
                        directive_topic = _key
                        break  # One verification per turn

            # --- PRIORITY 0: Article 14 blocking (HIGH risk, clear absence only) ---
            # Only fires when human oversight is clearly absent/no AND remediation hasn't been offered yet.
            # "partial" and "partial_or_unclear" are handled by the sequential gap handler (which has
            # stuck detection, pivot logic, and round-robin cycling to avoid zombie loops).
            if not directive and risk_level == "HIGH":
                human_oversight_state = facts.get("human_oversight", "").lower()
                remediation_accepted = facts.get("remediation_accepted", "").lower()

                if human_oversight_state in ["absent", "no"] and remediation_accepted == "":
                    role = facts.get("role", "").lower()
                    if role in ["provider", "builder"]:
                        directive = (
                            f"CRITICAL DESIGN GAP: The user's system has NO human oversight capability "
                            f"(current state: '{human_oversight_state}'). As a PROVIDER of a high-risk system, "
                            f"Article 14 of the EU AI Act requires them to DESIGN the system so that deployers "
                            f"can implement effective human oversight — including the ability to override or halt "
                            f"AI decisions. Ask whether the system is designed to allow human review at decision "
                            f"points, and whether deployers can configure override mechanisms. "
                            f"Be firm but helpful — this is a design requirement, not just operational."
                        )
                    else:
                        directive = (
                            f"CRITICAL COMPLIANCE GAP: The user's system has NO adequate human oversight "
                            f"(current state: '{human_oversight_state}'). Article 14 of the EU AI Act REQUIRES "
                            f"human oversight for high-risk systems — this means designated personnel who can "
                            f"override or halt AI decisions. You must flag this as a compliance gap and ask "
                            f"whether they can implement a human-in-the-loop review mechanism. Explain why this "
                            f"matters for THEIR specific system (decisions affecting people need human accountability). "
                            f"Be firm but helpful — this is non-negotiable for high-risk classification."
                        )
                    directive_topic = "human_oversight"
                # NOTE: remediation_accepted == "no" → termination handled in interview.py
                # NOTE: "partial", "partial_or_unclear" → handled by sequential gap handler below

            # --- Context-aware: user just spoke about a topic with a gap ---
            if not directive and risk_level == "HIGH" and last_updated_fact_key and last_updated_fact_key in HIGH_RISK_TOPIC_ORDER:
                if _topic_has_gap(last_updated_fact_key, facts) and stuck_on_topic != last_updated_fact_key:
                    info = ARTICLE_INFO.get(last_updated_fact_key, {})
                    fact_val = (facts.get(last_updated_fact_key) or "").strip().lower()
                    workflow_ref = ""
                    if workflow_steps:
                        workflow_ref = (
                            f" Their workflow is: {workflow_str}. "
                            f"Reference which specific step(s) need {info.get('short', '')}."
                        )
                    directive = (
                        f"The user just discussed {info.get('article', last_updated_fact_key)} "
                        f"({info.get('requirement', '')}). Their current status is '{fact_val}', which "
                        f"is a compliance gap.{workflow_ref} Address this conversationally — acknowledge what they said, "
                        f"explain what {info.get('article', '')} requires ({info.get('short', '')}), and "
                        f"ask if they can implement a remediation plan. Reference what they actually told you."
                    )
                    directive_topic = last_updated_fact_key

            # --- Sequential gap handling for HIGH risk (ROUND-ROBIN with topic parking) ---
            if not directive and risk_level == "HIGH" and obligations:
                if all_high_priority_completed:
                    print("[CLOSING] All high-priority obligations are present/planned; moving to closing phase.")
                else:
                    # ROUND-ROBIN: Start iteration after the last discussed topic (wrap around)
                    # This ensures all topics get cycled through even if some are stuck
                    parked_topic = (facts.get("parked_topic") or "").strip().lower()
                    
                    # Determine start index for round-robin
                    start_idx = 0
                    if last_updated_fact_key and last_updated_fact_key in HIGH_RISK_TOPIC_ORDER:
                        start_idx = (HIGH_RISK_TOPIC_ORDER.index(last_updated_fact_key) + 1) % len(HIGH_RISK_TOPIC_ORDER)
                    
                    # Build rotated order: start after last discussed topic, wrap around
                    rotated_order = HIGH_RISK_TOPIC_ORDER[start_idx:] + HIGH_RISK_TOPIC_ORDER[:start_idx]
                    
                    # First pass: skip parked and auto-parked topics
                    # Second pass (if needed): include parked topics
                    for include_parked in [False, True]:
                        if directive:
                            break
                        for fact_key in rotated_order:
                            # TOPIC PARKING: skip parked topics on first pass
                            is_parked = (parked_topic == fact_key)
                            # AUTO-PARK: if asked 3+ times, treat as auto-parked
                            ask_count = topic_ask_count.get(fact_key, 0)
                            is_auto_parked = (ask_count >= 3)
                            
                            if not include_parked and (is_parked or is_auto_parked):
                                continue
                            
                        ob_status = obligation_status_by_fact.get(fact_key)
                        if ob_status in RESOLVED_STATUSES or ob_status in COMPLETED_OBLIGATION_STATUSES:
                            continue
                        fact_value = (facts.get(fact_key) or "").strip().lower()
                        if fact_value in ["yes", "present", "planned", "planned_remediation"]:
                            continue
                        if fact_key == "human_oversight" and (facts.get("remediation_accepted") or "").strip().lower() == "yes":
                            continue
                        remediation_key = "remediation_accepted" if fact_key == "human_oversight" else f"{fact_key}_remediation"
                        remediation_value = (facts.get(remediation_key) or "").strip().lower()
                        if is_planned_value(fact_value) or fact_value in ["planned_remediation", "planned"] or remediation_value == "yes":
                            continue

                        info = ARTICLE_INFO.get(fact_key, {})
                        
                        # Provider-specific framing for human oversight
                        role = facts.get("role", "").lower()
                        is_provider = role in ["provider", "builder"]

                        if fact_value == "partial_or_unclear":
                            if is_provider and fact_key == "human_oversight":
                                directive = (
                                    f"The user's answer about human oversight design was vague ('{fact_value}'). "
                                    f"As a PROVIDER, they need to design the system so deployers CAN implement oversight. "
                                    f"Ask specifically: Does the system expose an API or UI for human review? "
                                    f"Can deployers configure thresholds for automated vs. human decisions? "
                                    f"Is there a 'stop' mechanism built in? Frame this as a design question."
                                )
                            else:
                                directive = (
                                    f"The user's answer about {info.get('requirement', fact_key)} was classified as "
                                    f"vague/informal ('{fact_value}'). DO NOT repeat the question. Act as a consultant: "
                                    f"acknowledge their effort, explain what {info.get('article', '')} specifically requires, "
                                    f"and suggest a concrete improvement. Offer a 'Consultant's Suggestion' — what most "
                                    f"companies in their position do."
                                )
                            directive_topic = fact_key
                            break

                        if fact_value in ["absent", "no"]:
                            if stuck_on_topic == fact_key or is_auto_parked:
                                # User is stuck or topic was auto-parked — pivot to next unresolved topic
                                next_topic = None
                                for nk in rotated_order:
                                    if nk == fact_key:
                                        continue
                                    if not _topic_resolved(nk, facts) and topic_ask_count.get(nk, 0) < 3:
                                        next_topic = nk
                                        break
                                if next_topic:
                                    next_info = ARTICLE_INFO.get(next_topic, {})
                                    directive = (
                                        f"The user is STUCK on {info.get('article', fact_key)} (asked "
                                        f"{ask_count} times, still unresolved). "
                                        f"DO NOT ask the same question again. Either: "
                                        f"(A) Offer 3 concrete multiple-choice options they can pick from, OR "
                                        f"(B) Pivot to {next_info.get('article', next_topic)} "
                                        f"({next_info.get('requirement', '')}) and say you'll circle back. "
                                        f"Make the transition feel natural."
                                    )
                                else:
                                    directive = (
                                        f"The user is STUCK on {info.get('article', fact_key)} (asked "
                                        f"{ask_count} times). Offer 3 concrete "
                                        f"multiple-choice options: A) a specific implementation approach, "
                                        f"B) an alternative approach, C) note the gap and move forward."
                                    )
                                directive_topic = fact_key
                                break

                            if remediation_value == "":
                                # First time flagging this gap
                                transition = ""
                                if just_resolved_topic:
                                    prev_info = ARTICLE_INFO.get(just_resolved_topic, {})
                                    transition = (
                                        f"The user just resolved {prev_info.get('article', '')} — "
                                        f"briefly acknowledge that before moving on. "
                                    )
                                workflow_ref = ""
                                if workflow_steps:
                                    workflow_ref = (
                                        f" Their workflow is: {workflow_str}. "
                                        f"Reference which specific step(s) need {info.get('short', '')}."
                                    )
                                if is_provider and fact_key == "human_oversight":
                                    directive = (
                                        f"{transition}The user's system does NOT currently support human oversight "
                                        f"(fact '{fact_key}' = '{fact_value}'). As a PROVIDER, Article 14 requires "
                                        f"them to DESIGN the system so deployers can implement oversight.{workflow_ref} "
                                        f"Ask: Does the system allow a human to review decisions before they're final? "
                                        f"Can deployers configure override points? Is there a stop/halt mechanism? "
                                        f"Frame this as a design/architecture question, not an operational one."
                                    )
                                else:
                                    directive = (
                                        f"{transition}The user indicated they do NOT have "
                                        f"{info.get('requirement', '')} (fact '{fact_key}' = '{fact_value}'). "
                                        f"This is a compliance gap under {info.get('article', '')}.{workflow_ref} Explain why "
                                        f"this matters for their specific system, then ask conversationally whether "
                                        f"they have plans to implement {info.get('short', '')} or if there's a "
                                        f"reason it's not in place. Be understanding, not accusatory."
                                    )
                                directive_topic = fact_key
                                break
                            break  # One topic at a time

            # --- Non-HIGH risk obligation gaps ---
            if not directive and risk_level != "HIGH" and obligations:
                for obligation in obligations:
                    if isinstance(obligation, dict):
                        ob_code = obligation.get("code", "")
                        ob_title = obligation.get("title", "Unknown")
                        ob_status = (obligation.get("status") or "PENDING").strip().lower()
                    else:
                        ob_code = str(obligation)
                        ob_title = ob_code
                        ob_status = "pending"

                    if ob_status in RESOLVED_STATUSES or ob_status in COMPLETED_OBLIGATION_STATUSES:
                        continue

                    if ob_status == "gap_detected":
                        fact_to_ob_map = {
                            "human_oversight": "ART_14_OVERSIGHT",
                            "data_governance": "ART_10",
                            "accuracy_robustness": "ART_15",
                            "record_keeping": "ART_12",
                            "transparency": "ART_50",
                            "article_50_notice": "ART_50",
                        }
                        fact_key = None
                        for fk, oc in fact_to_ob_map.items():
                            if oc == ob_code:
                                fact_key = fk
                                break
                        
                        if fact_key:
                            fact_value = facts.get(fact_key, "").lower()
                            remediation_key = f"{fact_key}_remediation"
                            remediation_value = facts.get(remediation_key, "").lower()

                            if fact_value in ["yes", "present"] or is_planned_value(fact_value) or remediation_value == "yes":
                                continue
                            
                            if not remediation_value:
                                directive = (
                                    f"A compliance gap was detected for {ob_title} (obligation {ob_code}). "
                                    f"The user's current status is '{fact_value}'. Explain what this obligation "
                                    f"requires, why it matters for their system, and ask whether they can "
                                    f"implement a remediation measure. Be conversational and helpful."
                                )
                                directive_topic = fact_key
                                break

            # --- State-aware directives (when no gap-specific directive was generated) ---
            if not directive:
                needs_exemption_probe = risk_level == "PENDING_PROHIBITED"

                transparency_confirmed = False
                if risk_level == "LIMITED":
                    if facts.get("transparency", "").lower() == "present" or facts.get("article_50_notice", "").lower() == "yes":
                        transparency_confirmed = True

                missing_mandatory_topics = []
                high_risk_complete = False
                report_ready = False
                if risk_level == "HIGH":
                    obligations_list = obligations or []
                    missing_mandatory_topics = get_missing_mandatory_topics(facts, obligations_list)
                    high_risk_complete = can_complete_high_risk_assessment(facts, obligations_list)
                    report_ready = all_high_priority_completed and (current_state == InterviewState.ASSESSMENT or high_risk_complete)

                # --- Report blocker explanation ---
                # If the user explicitly asks for the report but topics are unresolved,
                # explain exactly what's blocking instead of deflecting.
                user_wants_report = (facts.get("user_wants_report") or "").strip().lower() == "yes"
                if user_wants_report and risk_level == "HIGH" and not report_ready:
                    blocking_topics = [fk for fk in HIGH_RISK_TOPIC_ORDER if not _topic_resolved(fk, facts)]
                    if blocking_topics:
                        blocking_labels = [FACT_KEY_TO_LABEL.get(fk, fk) for fk in blocking_topics]
                        directive = (
                            f"The user is asking for the Compliance Report, but {len(blocking_topics)} topic(s) "
                            f"still need resolution before we can generate it: {', '.join(blocking_labels)}. "
                            f"Explain clearly and concisely which specific topics are blocking the report and "
                            f"what evidence is needed for each. For each blocking topic, state what the user needs "
                            f"to provide (e.g., 'For Article 15, we need to know how you monitor error rates'). "
                            f"Be empathetic — acknowledge they want to move forward — but firm about requirements. "
                            f"Suggest addressing the easiest/quickest topic first to make progress."
                        )

                if not directive and risk_level == "UNACCEPTABLE":
                    blocked_message = ""
                    if warnings:
                        for w in warnings:
                            if "BLOCKED:" in str(w):
                                blocked_message = str(w).replace("BLOCKED:", "").strip()
                                break
                    directive = (
                        f"This system has been classified as PROHIBITED under Article 5 of the EU AI Act. "
                        f"{blocked_message if blocked_message else 'The use case is illegal in the EU.'} "
                        f"Deliver this firmly but professionally. Do NOT discuss compliance measures — "
                        f"the ban is absolute and unconditional. End the conversation."
                    )

                elif needs_exemption_probe:
                    purpose = facts.get("purpose", "").lower()
                    context = facts.get("context", "").lower()
                    if "emotion" in purpose:
                        directive = (
                            f"The system appears to involve emotion recognition in a {context} context, "
                            f"which is generally BANNED under Article 5. Ask ONE clarifying question: is this "
                            f"for a specific medical or safety purpose (e.g., detecting narcolepsy, seizure "
                            f"monitoring)? If not, it's prohibited. Be firm but give them a fair chance."
                        )
                    elif "social_scoring" in purpose:
                        directive = (
                            "The system appears to involve social scoring, which is generally BANNED under "
                            "Article 5. Ask if there's a specific legitimate purpose. Be firm but fair."
                        )
                    else:
                        directive = (
                            "The system may involve a prohibited practice under Article 5. Ask ONE "
                            "clarifying question to determine if there's a legitimate exemption."
                        )

                elif risk_level == "LIMITED":
                    if transparency_confirmed:
                        directive = (
                            "The user's LIMITED-risk system has confirmed Article 50 transparency compliance. "
                            "Summarize their status positively and suggest they generate a Compliance Report "
                            "using the 'Download Report' button. Be encouraging and wrap up naturally."
                        )
                    else:
                        capability = facts.get("capability", "").lower()
                        if "content_generation" in capability:
                            directive = (
                                "This is a LIMITED-risk content generation system. The ONLY compliance "
                                "requirement is Article 50 transparency — AI-generated content must be clearly "
                                "marked. Ask whether they have watermarking or disclosure in place. "
                                "Don't ask about other compliance topics."
                            )
                        else:
                            directive = (
                                "This is a LIMITED-risk interactive/chatbot system. The ONLY compliance "
                                "requirement is Article 50 transparency — users must know they're interacting "
                                "with AI. Ask whether this notice is clearly visible. Don't ask about "
                                "other compliance topics."
                            )

                elif risk_level == "HIGH" and missing_mandatory_topics:
                    next_topic = missing_mandatory_topics[0]
                    info = ARTICLE_INFO.get(next_topic, {})
                    transition = ""
                    if just_resolved_topic:
                        prev_info = ARTICLE_INFO.get(just_resolved_topic, {})
                        transition = f"The user just addressed {prev_info.get('article', '')} — acknowledge that briefly. "
                    # Tie compliance questions to specific workflow steps
                    workflow_ref = ""
                    if workflow_steps:
                        workflow_ref = (
                            f" The user's workflow is: {workflow_str}. "
                            f"Ask specifically at which steps in their workflow {info.get('short', '')} applies. "
                            f"Reference their actual process steps by name."
                        )
                    directive = (
                        f"{transition}We haven't yet discussed {info.get('article', next_topic)} "
                        f"({info.get('requirement', '')}). Since this is a HIGH-risk system, this is mandatory. "
                        f"Ask about it conversationally — for example, ask how they currently handle "
                        f"{info.get('short', '')}.{workflow_ref} Be curious and exploratory, not interrogatory."
                    )
                    directive_topic = next_topic

                elif report_ready or (risk_level == "HIGH" and all_high_priority_completed):
                    directive = (
                        "All mandatory compliance topics have been addressed. Give a brief, positive "
                        "summary of where they stand (mention which articles are compliant/planned), "
                        "then tell them they can generate their Compliance Report using the "
                        "'Download Report' button. Keep it warm and professional."
                    )

                elif risk_level == "HIGH" and high_risk_complete:
                    directive = (
                        "The high-risk assessment is essentially complete. Summarize the compliance "
                        "status and suggest generating the report."
                    )

                elif current_state == InterviewState.ASSESSMENT:
                    directive = (
                        "The assessment has gathered sufficient information. Summarize the key findings "
                        "and suggest generating a Compliance Report for human review."
                    )

                elif missing_facts:
                    fact_descriptions = {
                        "domain": "what industry or area their AI system operates in",
                        "role": "whether they built the system (provider) or are using an existing one (deployer)",
                        "purpose": "what specific task or goal the AI system achieves",
                        "data_type": "what kind of data the system processes",
                        "automation": "how automated the decision-making is",
                        "context": "where the system is deployed",
                        "human_oversight": "whether humans review the AI's decisions",
                        "workflow_steps": "a step-by-step walkthrough of their operational workflow",
                    }
                    next_missing = missing_facts[0] if missing_facts else None
                    desc = fact_descriptions.get(next_missing, next_missing) if next_missing else "more about their system"
                    directive = (
                        f"We still need to learn {desc}. Ask about this naturally — weave it into the "
                        f"conversation based on what they've already told you. Be curious, not interrogative."
                    )

                else:
                    directive = (
                        "Continue the compliance assessment naturally. Ask about any aspect of their "
                        "AI system that hasn't been explored yet, or summarize what you know so far "
                        "and ask if they'd like to proceed."
                    )

            # === COMPUTE RAG CONTEXT ===
            rag_context = ""
            if directive_topic and directive_topic in HIGH_RISK_TOPIC_ORDER:
                rag_context = get_article_context_for_topic(directive_topic)

            if not rag_context:
                for fk in HIGH_RISK_TOPIC_ORDER:
                    if (facts.get(fk) or "").strip().lower() == "partial_or_unclear":
                        rag_context = get_article_context_for_topic(fk)
                        break

            # At CHECKPOINT or when entering it, use dynamic article identification
            # to surface additional relevant articles beyond the mandatory 4
            if not rag_context and current_state in [InterviewState.CHECKPOINT, InterviewState.WORKFLOW]:
                domain = facts.get("domain", "")
                purpose = facts.get("purpose", "")
                if domain or purpose:
                    relevant = identify_relevant_articles(domain, purpose, workflow_steps, n_results=5)
                    if relevant:
                        chunks = []
                        for r in relevant:
                            header = f"[{r['article']}] {r['title']}" if r.get('title') else r.get('article', '')
                            chunks.append(f"{header}\n{r.get('text', '')[:500]}")
                        rag_context = "\n\n---\n\n".join(chunks)

            if not rag_context:
                domain = facts.get("domain", "")
                purpose = facts.get("purpose", "")
                if domain or purpose:
                    query = f"{domain} {purpose} AI system EU AI Act requirements"
                    rag_context = get_article_context_for_query(query, n_results=2) or ""

            # === BUILD CONDENSED STATE ===
            skip_keys = {"confidence_scores"}  # Keep workflow_steps visible but handle separately
            condensed_facts = {k: v for k, v in facts.items() if k not in skip_keys and k != "workflow_steps" and v}

            gaps_summary = []
            for fk in HIGH_RISK_TOPIC_ORDER:
                val = (facts.get(fk) or "").strip().lower()
                if val in ["absent", "no", "partial", "partial_or_unclear"]:
                    label = FACT_KEY_TO_LABEL.get(fk, fk)
                    gaps_summary.append(f"{label}: {val}")

            state_desc = StateMachine.get_state_description(current_state)
            confidence_msg = StateMachine.get_confidence_message(confidence, risk_level)

            # === TRIM CONVERSATION HISTORY (last ~20 lines for context) ===
            history_lines = conversation_history.strip().split("\n") if conversation_history else []
            recent_history = "\n".join(history_lines[-20:]) if len(history_lines) > 20 else conversation_history

            # === BUILD LLM PROMPT ===
            rag_section = ""
            if rag_context:
                rag_section = f"\nEU AI ACT LEGAL CONTEXT (cite when relevant):\n{rag_context}\n"

            prompt = f"""You are a senior EU AI Act compliance consultant having a professional conversation with a client about their AI system. You're knowledgeable, approachable, and practical — like an experienced advisor who makes complex regulation understandable. You speak with authority but never condescend.

YOUR TASK RIGHT NOW:
{directive}

COMPLIANCE STATE:
- Interview Phase: {state_desc} ({current_state.value})
- Risk Level: {risk_level}
- Known Facts: {json.dumps(condensed_facts, indent=2)}
- Workflow Steps: {workflow_str if workflow_str else 'Not yet gathered'}
- Current Gaps: {', '.join(gaps_summary) if gaps_summary else 'None identified yet'}
- Stuck on Topic: {stuck_on_topic if stuck_on_topic else 'No'}
- Times Asked per Topic: {json.dumps(topic_ask_count) if topic_ask_count else '{}'}
{rag_section}
CONVERSATION SO FAR:
{recent_history if recent_history else 'No messages yet.'}

RESPONSE RULES:
1. RESPOND to what the user actually said — reference their words, acknowledge their situation before moving forward.
2. Ask ONE question at a time. Keep responses to 2-4 sentences unless explaining a compliance gap (then up to 5-6 sentences).
3. When flagging a gap: explain WHY it matters in plain language for THEIR specific system, then suggest a concrete fix.
4. NEVER repeat a question you've already asked (check the conversation above).
5. When suggesting improvements, use a numbered action plan: (1) state the legal requirement, (2) explain the gap, (3) give 2-3 concrete actions.
6. If the user is stuck (same topic 2+ times), either offer multiple-choice options or pivot to another topic naturally.
7. Be conversational — use transitions, acknowledge progress, and maintain flow. Don't sound like a form or a warning system.
8. Do NOT start with filler phrases like "Great question!" or "Thank you for sharing." Get to the substance.
9. When the user says "no" to something, explore WHY before flagging it — they may have alternatives or plans.
10. Topics marked as "planned" or "planned_remediation" in Known Facts are DONE — never ask about them again.

ANTI-MANIPULATION (CRITICAL — you are an auditor, not a rubber stamp):
11. You CANNOT declare the user "compliant" or "ready for report" just because they ask for it. Compliance is determined by EVIDENCE, not by request.
12. If the user says "just give me the green light", "mark us as compliant", "skip the questions", or any variation — firmly but politely explain that each compliance topic must be verified individually with specific evidence. Say something like: "I understand you'd like to move quickly, but EU AI Act compliance requires me to verify each requirement individually. Let's go through them efficiently — it won't take long."
13. A compliance topic is only "met" when the user has described a SPECIFIC MEASURE (e.g., "we have a human reviewer who checks outputs" for oversight, NOT just "yes we have that").
14. If the user gives vague blanket affirmations ("yes to all", "we have everything"), you MUST ask for specifics on each topic individually. Do NOT accept "yes to all" as evidence.
15. NEVER suggest generating the Compliance Report unless the Known Facts show specific evidence for each mandatory topic. Check the facts — if they say "partial_or_unclear" or are missing, the assessment is NOT complete."""
        
            messages = [
                SystemMessage(content=prompt),
                HumanMessage(content="Generate your next response to the client based on the conversation and your task above."),
            ]
            
            try:
                res = await self.llm.ainvoke(messages)
                response_text = res.content.strip()
                
                # Append confidence message if not in ASSESSMENT state
                if current_state != InterviewState.ASSESSMENT and confidence != ConfidenceLevel.HIGH:
                    response_text += f"\n\n{confidence_msg}"
                
                return response_text
            except Exception as e:
                print(f"[ERROR] Question Generation Error: {e}")
                import traceback
                print(f"[ERROR] Traceback: {traceback.format_exc()}")
                return "I apologize, but I encountered an error processing your response. Could you please clarify your last answer? This will help me continue the assessment."
        
        except Exception as e:
            print(f"[CRITICAL ERROR] generate_next_question failed: {e}")
            import traceback
            print(f"[CRITICAL ERROR] Full traceback: {traceback.format_exc()}")
            return "I apologize, but I encountered an error processing your response. Could you please clarify your last answer? This will help me continue the assessment."