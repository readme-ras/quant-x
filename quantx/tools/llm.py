"""
QuantX - LLM Client (Groq)
Uses Groq API with Llama 3.3 70B - free, fast, no timeouts.
"""

import os
import json
import time
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.3-70b-versatile"


def call_llm(
    prompt: str,
    system: str = "",
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
    force_json: bool = True,
    max_retries: int = 3,
) -> str:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set in .env")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 2048,
    }

    if force_json:
        payload["response_format"] = {"type": "json_object"}

    for attempt in range(max_retries):
        try:
            response = requests.post(
                GROQ_BASE_URL,
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"Rate limited. Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"LLM call failed (attempt {attempt+1}): {e}. Retrying...")
                time.sleep(2 ** attempt)
            else:
                raise

    return ""


def parse_json_response(response: str, fallback: dict = None) -> dict:
    if fallback is None:
        fallback = {}
    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        return json.loads(cleaned.strip())
    except (json.JSONDecodeError, IndexError):
        logger.warning(f"Failed to parse JSON: {response[:200]}")
        return fallback


def call_llm_json(
    prompt: str,
    system: str = "",
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
    fallback: dict = None,
) -> dict:
    raw = call_llm(prompt, system=system, model=model,
                   temperature=temperature, force_json=True)
    return parse_json_response(raw, fallback=fallback or {})


def is_ollama_running() -> bool:
    """Always returns True since we're using Groq now."""
    return bool(GROQ_API_KEY)


def is_model_available(model: str = DEFAULT_MODEL) -> bool:
    """Always returns True since we're using Groq now."""
    return bool(GROQ_API_KEY)