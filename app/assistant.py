from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def ask_agent(prompt: str) -> str:
    response = client.responses.create(
        model="gpt-5.5",
        input=prompt,
    )
    return response.output_text