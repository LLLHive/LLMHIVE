import os
from typing import List, Optional
try:
    import anthropic
except Exception:
    anthropic = None
try:
    import httpx
except Exception:
    httpx = None
try:
    import requests
except Exception:
    requests = None

class ClaudeClient:
    def __init__(self, api_key: Optional[str] = None, api_version: str = "2023-06-01"):
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise RuntimeError("CLAUDE_API_KEY not set")
        self.api_version = api_version

    def complete(self, model: str, messages: List[dict], max_tokens: int = 1024, temperature: float = 0.2, system: Optional[str] = None) -> str:
        if anthropic:
            client = anthropic.Anthropic(api_key=self.api_key)
            resp = client.messages.create(model=model, max_tokens=max_tokens, temperature=temperature, system=system, messages=messages)
            parts = []
            for c in getattr(resp, "content", []) or []:
                t = getattr(c, "text", None)
                if t:
                    parts.append(t)
                elif isinstance(c, dict) and "text" in c:
                    parts.append(c["text"])
            return "\n".join(parts).strip()
        payload = {"model": model, "max_tokens": max_tokens, "temperature": temperature, "messages": messages}
        if system:
            payload["system"] = system
        headers = {"x-api-key": self.api_key, "anthropic-version": self.api_version, "content-type": "application/json"}
        url = "https://api.anthropic.com/v1/messages"
        if httpx:
            with httpx.Client(timeout=60) as cx:
                r = cx.post(url, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
        elif requests:
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
        else:
            raise RuntimeError("No HTTP client available")
        out = []
        for c in data.get("content", []):
            t = c.get("text")
            if t:
                out.append(t)
        return "\n".join(out).strip()
