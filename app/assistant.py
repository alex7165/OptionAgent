from dotenv import load_dotenv
from openai import OpenAI
import os
from config.settings import DEFAULT_MODEL, TRADING_RULES

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def ask_agent(prompt: str) -> str:
    full_prompt = f"""
{TRADING_RULES}

Aufgabe:
{prompt}
"""

    response = client.responses.create(
        model=DEFAULT_MODEL,
        input=full_prompt,
    )
    return response.output_text