from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List
import os

# 1. Update Output Structure to enforce exactly 4 metrics
class RiskProfile(BaseModel):
    risk_level: str = Field(description="High, Limited, or Minimal")
    category: str = Field(description="The specific Annex III category (e.g., Employment, Education)")
    metrics: List[str] = Field(description="A list of exactly 4 specific metrics to test (e.g., ['gender_bias', 'robustness', 'privacy', 'explainability'])")
    reasoning: str = Field(description="Legal reasoning based on EU AI Act")

class ComplianceAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.parser = JsonOutputParser(pydantic_object=RiskProfile)

    def analyze_use_case(self, description: str, user_metrics: List[str] = []):
        """
        Analyzes the use case. 
        If user_metrics < 4, it auto-generates the remaining ones.
        """
        
        # 2. Logic to handle user input
        metrics_instruction = ""
        if user_metrics:
            metrics_instruction = f"The user has already requested these metrics: {user_metrics}. Keep these, and generate additional relevant metrics until you have exactly 4."
        else:
            metrics_instruction = "Generate 4 relevant technical metrics to audit this system (e.g. fairness, toxicity, privacy, hallucination)."

        # 3. Updated Prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert EU AI Act Auditor. Analyze the AI system description."),
            ("system", "Determine the Risk Level based on Annex III."),
            ("system", f"{metrics_instruction} Return exactly 4 metrics in the list."),
            ("system", "{format_instructions}"),
            ("human", "{description}")
        ])

        chain = prompt | self.llm | self.parser
        
        return chain.invoke({
            "description": description,
            "format_instructions": self.parser.get_format_instructions()
        })