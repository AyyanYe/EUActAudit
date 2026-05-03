from langchain_openai import ChatOpenAI
import os
import json


async def analyze_risk(description: str, user_metrics: list):
    """
    Uses OpenRouter (GPT-3.5 or GPT-4) to classify the risk level
    according to the EU AI Act.
    """

    # 1. Setup the LLM with OpenRouter
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is missing. Cannot perform risk analysis.")

    llm = ChatOpenAI(
        model="openai/gpt-3.5-turbo",  # Fast & Cheap for simple classification
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0,
    )

    # 2. The Prompt
    metrics_str = ", ".join(user_metrics) if user_metrics else "None provided"

    prompt = f"""
    You are an EU AI Act Compliance Officer. Analyze this AI system.
    
    System Description: "{description}"
    Intended Metrics: "{metrics_str}"
    
    Determine the Risk Category based on EU AI Act Annex III:
    - 'High Risk': Critical infrastructure, Education, Employment, Essential private/public services, Law enforcement, Migration/Border control, Justice/Democratic processes.
    - 'Limited Risk': Chatbots, Emotion recognition, Deepfakes (Transparency obligations).
    - 'Minimal Risk': Spam filters, Video games, Inventory management.
    
    Also suggest 4 specific metrics to test if user provided fewer than 4.

    Return JSON ONLY:
    {{
        "risk_level": "High Risk" | "Limited Risk" | "Minimal Risk",
        "reasoning": "Short explanation...",
        "metrics": ["Metric1", "Metric2", "Metric3", "Metric4"]
    }}
    """

    # 3. Execution
    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()

        # Clean markdown if present
        if "```json" in content:
            content = content.replace("```json", "").replace("```", "")

        return json.loads(content)
    except Exception as e:
        print(f"Risk Logic Error: {e}")
        # Fallback response so the app doesn't crash
        return {
            "risk_level": "Unknown Risk",
            "reasoning": "Automatic analysis failed. Defaulting to safe mode.",
            "metrics": ["Fairness", "Accuracy", "Robustness", "Transparency"],
        }
