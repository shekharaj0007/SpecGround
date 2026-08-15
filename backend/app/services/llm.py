"""Anthropic (Claude) chat completions. Embeddings are local — Anthropic has no embed API."""

from __future__ import annotations

import json
import re

from anthropic import Anthropic

from app.config import settings

_client: Anthropic | None = None


def client() -> Anthropic:
    global _client
    if _client is None:
        key = settings.resolved_anthropic_key
        if not key.startswith("sk-ant-"):
            raise RuntimeError(
                "Set ANTHROPIC_API_KEY in .env (it starts with sk-ant-). "
                "Do not put it in OPENAI_API_KEY unless it is an Anthropic key."
            )
        _client = Anthropic(api_key=key)
    return _client


def complete_text(user: str, system: str = "", model: str | None = None, max_tokens: int = 2048) -> str:
    resp = client().messages.create(
        model=model or settings.anthropic_chat_model,
        max_tokens=max_tokens,
        temperature=0,
        system=system or "You are a careful assistant.",
        messages=[{"role": "user", "content": user}],
    )
    parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
    return "".join(parts).strip()


def complete_json(user: str, system: str = "", model: str | None = None) -> dict:
    raw = complete_text(
        user=user + "\n\nReturn a single JSON object only. No markdown fences.",
        system=system,
        model=model,
    )
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.S)
        if match:
            return json.loads(match.group(0))
    return {"answer": raw, "raw": raw}
