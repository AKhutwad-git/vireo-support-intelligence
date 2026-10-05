"""Provider-neutral interface plus opt-in OpenAI-compatible JSON HTTP client."""
from __future__ import annotations
import json
import os
from urllib.request import Request, urlopen


class AIClient:
    model = "unspecified"
    provider = "unspecified"
    def classify_batch(self, prompts: list[dict]) -> list[dict]:
        raise NotImplementedError


class ProviderUnavailable(RuntimeError):
    pass


class OpenAICompatibleClient(AIClient):
    def __init__(self, endpoint: str, model: str, api_key_env: str, provider="openai_compatible", timeout=60):
        self.endpoint, self.model, self.provider, self.timeout = endpoint, model, provider, timeout
        self.api_key = os.environ.get(api_key_env)
        if not self.api_key: raise ProviderUnavailable(f"Provider key is not set in environment variable {api_key_env}")

    def classify_batch(self, prompts: list[dict]) -> list[dict]:
        # One ticket per request preserves ticket-level failure and evidence validation.
        results = []
        for item in prompts:
            try:
                payload = {"model": self.model, "temperature": 0, "response_format": {"type": "json_object"},
                    "messages": [{"role": "user", "content": item["prompt"]}]}
                request = Request(self.endpoint, data=json.dumps(payload).encode(), headers={
                    "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST")
                with urlopen(request, timeout=self.timeout) as response:
                    raw = json.loads(response.read())
                usage = raw.get("usage") or {}
                results.append({"ticket_id": item["ticket_id"], "result": json.loads(raw["choices"][0]["message"]["content"]),
                    "actual_input_tokens": usage.get("prompt_tokens"), "actual_output_tokens": usage.get("completion_tokens")})
            except Exception as exc:
                # Keep later ticket requests in the batch independent of this failure.
                results.append({"ticket_id": item["ticket_id"], "error": type(exc).__name__})
        return results
