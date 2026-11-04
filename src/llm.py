import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "")
TEMPORARY_CODES = ("429", "500", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE")


def get_client():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise SystemExit(
            "GEMINI_API_KEY is missing. Add it to the .env file in the project folder.")
    return genai.Client(api_key=key)


def ask(prompt, system=None, temperature=0.0, retries=2, return_model=False):
    """Send a prompt to Gemini. Retry on temporary errors, then fall back to the second model."""
    client = get_client()
    config = types.GenerateContentConfig(
        system_instruction=system, temperature=temperature)
    models = [m for m in (MODEL, FALLBACK_MODEL) if m]
    last_error = None

    for model in models:
        delay = 5
        for attempt in range(retries + 1):
            try:
                response = client.models.generate_content(
                    model=model, contents=prompt, config=config)
                text = response.text or ""
                return (text, model) if return_model else text
            except Exception as error:
                if not any(code in str(error) for code in TEMPORARY_CODES):
                    raise
                last_error = error
                if attempt < retries:
                    print(f"{model}: temporary error, retrying in {delay}s ...")
                    time.sleep(delay)
                    delay *= 2
        print(f"{model}: still unavailable, moving on.")

    raise last_error


if __name__ == "__main__":
    print(f"Model: {MODEL} (fallback: {FALLBACK_MODEL or 'none'})")
    print(ask("Reply with the single word: ready"))
