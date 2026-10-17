"""Tiny LLM client built on the standard library only (no dependencies)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

DEFAULT_MODELS = {"anthropic": "claude-sonnet-5-5", "ollama": "llama3.1"}


class LLMError(RuntimeError):
    pass


def resolve(provider: str | None, model: str | None) -> tuple[str, str]:
    provider = provider or os.environ.get("REPOLENS_PROVIDER") or "anthropic"
    if provider not in DEFAULT_MODELS:
        raise LLMError(f"unknown provider '{provider}' (choose: {', '.join(DEFAULT_MODELS)})")
    model = model or os.environ.get("REPOLENS_MODEL") or DEFAULT_MODELS[provider]
    return provider, model


def _post(url: str, payload: dict, headers: dict, timeout: int) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")[:500]
        raise LLMError(f"API error {err.code}: {body}") from None
    except urllib.error.URLError as err:
        raise LLMError(f"cannot reach {url}: {err.reason}") from None


def complete(system: str, user: str, provider: str, model: str,
             max_tokens: int = 2000, timeout: int = 180) -> str:
    if provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise LLMError(
                "ANTHROPIC_API_KEY is not set. Export it, or run locally and for free "
                "with: --provider ollama"
            )
        data = _post(
            "https://api.anthropic.com/v1/messages",
            {"model": model, "max_tokens": max_tokens, "system": system,
             "messages": [{"role": "user", "content": user}]},
            {"x-api-key": key, "anthropic-version": "2023-06-01"},
            timeout,
        )
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")

    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    data = _post(
        f"{host}/api/chat",
        {"model": model, "stream": False,
         "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
        {},
        timeout,
    )
    return data.get("message", {}).get("content", "")
