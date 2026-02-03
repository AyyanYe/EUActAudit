import os
import json
from dotenv import load_dotenv # <--- IMPORT THIS
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from core.risk_rules import evaluate_compliance_state

REQUIRED_FACTS = [
    {
        "key": "domain",
        "question": "Which domain does the system operate in (e.g., employment, credit, education, healthcare, public services, law enforcement)?",
    },
    {
        "key": "role",
        "question": "Are you the provider (built the model) or the deployer (using a model from someone else)?",
    },
    {
        "key": "purpose",
        "question": "What is the system's primary purpose (e.g., candidate screening, credit scoring, fraud detection)?",
    },
    {
        "key": "decision_stage",
        "question": "Where does the system sit in the decision process (advisory, pre-screening, or final decision)?",
    },
    {
        "key": "automation",
        "question": "Is the system fully automated, or does a human review and override its outputs?",
    },
    {
        "key": "data_type",
        "question": "What type of data does it use (personal data, biometric data, sensitive data, or non-personal)?",
    },
    {
        "key": "affected_stakeholders",
        "question": "Who is affected by the system's outcomes (e.g., candidates, employees, customers, students)?",
    },
    {
        "key": "deployment_region",
        "question": "Where will the system be deployed (EU only, mixed regions, or outside the EU)?",
    },
    {
        "key": "human_oversight",
        "question": "What human oversight is in place (who can pause or override decisions)?",
    },
]


def _is_missing(value: str | None) -> bool:
    if value is None:
        return True
    normalized = str(value).strip().lower()
    return normalized in {"", "unknown", "unsure", "n/a", "na"}


def _missing_facts(facts: dict) -> list[dict]:
    missing = []
    for item in REQUIRED_FACTS:
        if _is_missing(facts.get(item["key"])):
            missing.append(item)
    return missing

# <--- LOAD THE ENV FILE IMMEDIATELY ---
load_dotenv() 

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

        EXTRACT THESE SPECIFIC KEYS if mentioned:
        - "domain": Area of use (e.g., recruitment, credit_scoring, chatbot, healthcare).
        - "role": "provider" (built it) or "deployer" (bought/using it).
        - "purpose": Specific goal (e.g., ranking_candidates, detecting_fraud).
        - "decision_stage": "advisory", "pre_screening", "final_decision".
        - "data_type": "personal", "biometric", "sensitive", "non_personal".
        - "automation": "fully_automated", "human_in_the_loop", "human_on_the_loop".
        - "context": Where used? (e.g., workplace, public_space, school).
        - "affected_stakeholders": Who is affected (e.g., candidates, employees, customers).
        - "deployment_region": "eu_only", "mixed", "non_eu".
        - "human_oversight": Short description of who can override or pause decisions.

        Return ONLY a raw JSON object. Do not invent facts. If unclear, ignore the key.
        Example: {"domain": "recruitment", "role": "deployer", "data_type": "personal"}
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Conversation History:\n{history_text}")
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            content = response.content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except Exception as e:
            print(f"Extraction Error: {e}")
            return {}

    async def generate_next_question(self, facts: dict, risk_level: str, missing_obligations: list):
        """
        The 'Interviewer': Decides what to ask next based on missing info.
        """
        missing_info = _missing_facts(facts)
        next_question = missing_info[0]["question"] if missing_info else None

        prompt = f"""
        You are a Senior EU AI Act Compliance Consultant.

        CURRENT STATE:
        - Known Facts: {json.dumps(facts)}
        - Assessed Risk Level: {risk_level}
        - Next Question: {next_question}

        GOAL:
        1. Acknowledge what the user just said in one short sentence.
        2. If risk is HIGH or UNACCEPTABLE, add a brief warning.
        3. Ask the next targeted question (use the provided Next Question exactly).
        4. If there is no Next Question, suggest generating the compliance report.

        Keep it concise (2-3 sentences). Do not lecture. Be helpful.
        """

        res = await self.llm.ainvoke(prompt)
        return res.content
