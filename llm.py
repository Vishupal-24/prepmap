"""One small function to talk to Gemma, wherever it runs.

LLM_PROVIDER=ollama  -> local Gemma through Ollama (private data stays on this machine)
LLM_PROVIDER=gemini  -> Gemma through Google AI Studio (used only for the public demo)
LLM_PROVIDER=mock    -> canned answers, for tests
"""
import json
import os
import re

import requests

PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemma-4-26b-a4b-it")
# if the newer model is not available on this key, fall back to Gemma 3
GEMINI_FALLBACK = os.environ.get("GEMINI_FALLBACK", "gemma-3-27b-it")
TIMEOUT = 150

_mock_reply = None  # tests set this


def set_mock(reply):
    global _mock_reply
    _mock_reply = reply


def generate(prompt):
    if PROVIDER == "mock":
        return _mock_reply(prompt) if callable(_mock_reply) else (_mock_reply or "{}")
    if PROVIDER == "gemini":
        return _gemini(prompt)
    return _ollama(prompt)


def generate_json(prompt):
    """Ask for JSON and pull the first JSON object out of the reply."""
    text = generate(prompt)
    return parse_json(text)


def parse_json(text):
    text = text.strip()
    # models like to wrap JSON in ```json fences
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise ValueError("model did not return JSON")
        return json.loads(match.group(0))


def _ollama(prompt):
    r = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json",
              "options": {"temperature": 0}},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["response"]


_active_model = GEMINI_MODEL
# extraction is copying, not reasoning, so keep thinking short (it was 3000 tokens / 70s)
_thinking = {"thinkingLevel": "minimal"}


def _gemini(prompt):
    global _active_model, _thinking
    r = _gemini_call(_active_model, prompt, _thinking)
    if r.status_code == 400 and _thinking:
        print(f"[gemma] thinking setting rejected: {r.text[:200]}", flush=True)
        _thinking = None
        r = _gemini_call(_active_model, prompt, _thinking)
    if r.status_code in (400, 404) and _active_model != GEMINI_FALLBACK:
        _active_model = GEMINI_FALLBACK
        r = _gemini_call(_active_model, prompt, None)
    r.raise_for_status()
    body = r.json()
    # shows up in the Render logs, handy for spotting slow calls
    print(f"[gemma] {_active_model} {r.elapsed.total_seconds():.1f}s usage={body.get('usageMetadata')}", flush=True)
    parts = body["candidates"][0]["content"]["parts"]
    # thinking models can return a thought part first; keep the visible text
    return "".join(p.get("text", "") for p in parts if not p.get("thought"))


def _gemini_call(model, prompt, thinking):
    key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    config = {"temperature": 0}
    if thinking:
        config["thinkingConfig"] = thinking
    return requests.post(
        url,
        headers={"x-goog-api-key": key},
        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": config},
        timeout=TIMEOUT,
    )


def describe():
    if PROVIDER == "gemini":
        return f"Gemma ({_active_model}) via Google AI Studio - demo mode"
    if PROVIDER == "mock":
        return "mock model (tests)"
    return f"Gemma ({OLLAMA_MODEL}) running locally via Ollama"
