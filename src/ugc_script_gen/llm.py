"""Optional OpenAI-compatible backend with an offline mock fallback.

Set ``OPENAI_API_KEY`` (and optionally ``OPENAI_BASE_URL`` / ``UGC_MODEL``) to use any
OpenAI-compatible chat-completions endpoint: OpenAI, Groq, Together, OpenRouter, a
local Ollama or LM Studio server, etc. With no key the mock backend is used and the
tool stays fully offline and deterministic.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request


class LLMError(RuntimeError):
    pass


class MockLLM:
    """Offline stand-in: proposes no extra hooks and leaves lines untouched."""

    name = "mock"

    def propose_hooks(self, brief, n: int = 5) -> list[str]:
        return []

    def polish_lines(self, lines: list[str], brief) -> list[str]:
        return list(lines)


class OpenAICompatibleLLM:
    name = "openai-compatible"

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o-mini",
                 timeout: float = 30.0):
        self.api_key, self.base_url, self.model, self.timeout = api_key, base_url.rstrip("/"), model, timeout

    def _chat(self, system: str, user: str) -> str:
        body = json.dumps({"model": self.model, "temperature": 0.8,
                           "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=body.encode(),
                                     headers={"Authorization": f"Bearer {self.api_key}",
                                              "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
        except Exception as exc:  # network, auth, schema
            raise LLMError(str(exc)) from exc

    @staticmethod
    def _json_list(text: str) -> list[str]:
        m = re.search(r"\[.*\]", text, re.S)
        if not m:
            raise LLMError("model did not return a JSON array")
        out = json.loads(m.group(0))
        if not all(isinstance(x, str) for x in out):
            raise LLMError("expected a JSON array of strings")
        return out

    def propose_hooks(self, brief, n: int = 5) -> list[str]:
        system = ("You write scroll-stopping hooks for short-form UGC video ads. Hooks are spoken in the first 3 "
                  "seconds, under 12 words, first person, no medical or guaranteed claims. Reply with a JSON array only.")
        user = (f"Brand: {brief.brand}\nProduct: {brief.product}\nAudience: {brief.audience}\n"
                f"Pain points: {'; '.join(brief.pain_points)}\nBenefits: {'; '.join(brief.benefits)}\n"
                f"Tone: {brief.tone}\nNever say: {', '.join(brief.banned_claims) or 'n/a'}\nWrite {n} hooks.")
        return self._json_list(self._chat(system, user))[:n]

    def polish_lines(self, lines: list[str], brief) -> list[str]:
        system = ("You polish voice-over lines for a UGC ad so they sound natural when spoken by a real creator. "
                  "Keep meaning, keep every product name, keep roughly the same length. Reply with a JSON array "
                  "of strings, same length and order as the input.")
        user = f"Tone: {brief.tone}\nNever say: {', '.join(brief.banned_claims) or 'n/a'}\nLines:\n{json.dumps(lines)}"
        out = self._json_list(self._chat(system, user))
        if len(out) != len(lines):
            raise LLMError("model returned a different number of lines")
        return out


def get_llm(offline: bool = False):
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if offline or not key:
        return MockLLM()
    return OpenAICompatibleLLM(key, os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                               os.environ.get("UGC_MODEL", "gpt-4o-mini"))
