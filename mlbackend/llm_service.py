"""
AGRISENTINEL STANDALONE LOCAL AI SERVICE
----------------------------------------
100% On-Device Standalone Machine Learning AI (Zero Groq/Gemini Cloud Keys Required).
Uses trained local NLP model (mlbackend/advisor_ai_model.py).
"""

try:
    from .advisor_ai_model import local_advisor_ai
except ImportError:
    from advisor_ai_model import local_advisor_ai


def get_llm_response(prompt: str, system_prompt: str = "") -> str:
    """Routes query directly to local standalone trained Advisor AI model."""
    return local_advisor_ai.respond(prompt)
