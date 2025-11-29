# core/genai_client.py
import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# initialize client once, safe to import elsewhere
try:
    GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None
except Exception as e:
    client = None
    print(f"Warning: Gemini client init failed: {e}")

# Simple in-process rate limiter: 2 calls per 60 seconds
_rate_state = {"timestamps": []}
_RATE_MAX = 2
_RATE_WINDOW = 60

def check_and_mark_rate():
    now = time.time()
    ts = _rate_state["timestamps"]
    ts[:] = [t for t in ts if now - t < _RATE_WINDOW]
    if len(ts) >= _RATE_MAX:
        retry_after = _RATE_WINDOW - (now - ts[0])
        return False, retry_after
    ts.append(now)
    return True, 0

def safe_generate_content(*, model: str, contents: str, system_instruction: str = "", response_mime_type: str = "application/json"):
    """
    Wrapper over genai client models.generate_content. Ensures client exists and rate-limit respected.
    """
    if client is None:
        raise RuntimeError("Gemini client not initialized. Set GEMINI_API_KEY in environment.")
    ok, retry = check_and_mark_rate()
    if not ok:
        raise RuntimeError(f"Rate limit exceeded. Retry after {int(retry)}s.")
    # contents is the prompt string (we pass plain prompt — gemini SDK infers role)
    return client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system_instruction, response_mime_type=response_mime_type)
    )
