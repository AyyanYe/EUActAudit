import os
import json
from dotenv import load_dotenv # <--- IMPORT THIS
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from core.risk_rules import evaluate_compliance_state

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
        - "domain": The area of use (e.g., recruitment, credit_scoring, chatbot, healthcare).
        - "role": "provider" (built it) or "deployer" (bought/using it).
        - "purpose": Specific goal (e.g., ranking_candidates, detecting_fraud).
        - "data_type": "personal", "biometric", "anonymous".
        - "automation": "fully_automated", "human_in_the_loop".
        - "context": Where is it used? (e.g., workplace, public_space, school).

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
        # Define what we usually need to know
        critical_keys = ["domain", "role", "data_type", "automation"]
        missing_info = [key for key in critical_keys if key not in facts]

        prompt = f"""
        You are a Senior EU AI Act Compliance Consultant.
        
        CURRENT STATE:
        - Known Facts: {json.dumps(facts)}
        - Assessed Risk Level: {risk_level}
        - Missing Critical Info: {missing_info}
        
        GOAL:
        1. Acknowledge what the user just said.
        2. If 'Risk Level' is HIGH or UNACCEPTABLE, warn them clearly but professionally.
        3. Ask the NEXT most important question to fill the 'Missing Critical Info'.
        4. If all info is present, suggest generating the Compliance Report.

        Keep it concise (2-3 sentences). Do not lecture. Be helpful.
        """
        
        res = await self.llm.ainvoke(prompt)
        return res.content