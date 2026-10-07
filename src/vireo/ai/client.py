"""Provider-neutral interface plus opt-in OpenAI-compatible JSON HTTP client."""
from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AIClient:
    model = "unspecified"
    provider = "unspecified"

    def classify_batch(self, prompts: list[dict]) -> list[dict]:
        raise NotImplementedError


class ProviderUnavailable(RuntimeError):
    pass


class _ClientResult(dict):
    """Keep legacy dict equality/keys while exposing additive diagnostics via get()."""
    def __init__(self, values: dict, failure: dict):
        super().__init__(values)
        self._failure = failure

    def get(self, key, default=None):
        if key == "failure":
            return self._failure
        if key in ("actual_input_tokens", "actual_output_tokens", "actual_total_tokens"):
            return self._failure.get(key, default)
        return super().get(key, default)


def _failed_result(ticket_id: str, error: str, failure: dict) -> dict:
    return _ClientResult({"ticket_id": ticket_id, "error": error}, failure)


_SAFE_PROVIDER_MESSAGES = (
    "quota exceeded", "resource exhausted", "rate limit exceeded", "permission denied",
    "api key not valid", "invalid api key", "model not found", "invalid argument",
    "service unavailable", "internal error", "deadline exceeded", "billing account",
)


def _safe_provider_error(raw: bytes, api_key: str) -> dict:
    """Extract only bounded, allow-listed error metadata; never retain raw bodies."""
    try:
        payload = json.loads(raw[:8192].decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"provider_error_code": None, "provider_error_type": None,
                "provider_error_message": None, "safe_response_detail": "non_json_error_body_omitted"}
    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    if not isinstance(error, dict):
        error = {}
    code = error.get("code")
    if not isinstance(code, (str, int)) or isinstance(code, bool):
        code = None
    if isinstance(code, str) and (not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", code)
                                  or (api_key and api_key in code)):
        code = None
    error_type = error.get("status") or error.get("type")
    if not isinstance(error_type, str):
        error_type = None
    original = error.get("message")
    safe_message = None
    safe_detail = None
    if isinstance(original, str):
        normalized = re.sub(r"\s+", " ", original).strip().casefold()
        # Provider text is retained only when it matches a generic operational
        # phrase. Arbitrary messages may echo prompts or customer content.
        match = next((phrase for phrase in _SAFE_PROVIDER_MESSAGES if phrase in normalized), None)
        if match:
            safe_message = match
        elif original:
            safe_detail = "provider_message_omitted_as_untrusted"
    if api_key and safe_message and api_key in safe_message:
        safe_message = None
        safe_detail = "provider_message_omitted_as_untrusted"
    if error_type and (not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", error_type)
                       or (api_key and api_key in error_type)):
        error_type = None
    return {"provider_error_code": code, "provider_error_type": error_type,
            "provider_error_message": safe_message, "safe_response_detail": safe_detail}


def _safe_exception_message(exc: Exception, api_key: str) -> str | None:
    message = re.sub(r"\s+", " ", str(exc)).strip()
    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    message = re.sub(r"(?i)bearer\s+\S+", "Bearer [REDACTED]", message)
    # These exceptions should not contain prompt text; still omit suspiciously
    # long messages rather than risk writing request/customer content.
    if not message or len(message) > 240:
        return None
    return message


class OpenAICompatibleClient(AIClient):
    def __init__(self, endpoint: str, model: str, api_key_env: str, provider="openai_compatible", timeout=60):
        self.endpoint, self.model, self.provider, self.timeout = endpoint, model, provider, timeout
        self.api_key = os.environ.get(api_key_env)
        if not self.api_key:
            raise ProviderUnavailable(f"Provider key is not set in environment variable {api_key_env}")

    def classify_batch(self, prompts: list[dict]) -> list[dict]:
        # One ticket per request preserves ticket-level failure and evidence validation.
        results = []
        for item in prompts:
            ticket_id = item["ticket_id"]
            payload = {"model": self.model, "temperature": 0, "response_format": {"type": "json_object"},
                       "messages": [{"role": "user", "content": item["prompt"]}]}
            request = Request(self.endpoint, data=json.dumps(payload).encode(), headers={
                "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST")
            try:
                response_context = urlopen(request, timeout=self.timeout)
                with response_context as response:
                    response_body = response.read()
            except HTTPError as exc:
                try:
                    error_body = exc.read(8192)
                except Exception:
                    error_body = b""
                results.append(_failed_result(ticket_id, "HTTPError", {
                    "failure_stage": "provider_http", "exception_class": type(exc).__name__,
                    "http_status": exc.code, **_safe_provider_error(error_body, self.api_key)}))
                continue
            except (URLError, TimeoutError, OSError) as exc:
                results.append(_failed_result(ticket_id, type(exc).__name__, {
                    "failure_stage": "transport", "exception_class": type(exc).__name__,
                    "safe_message": _safe_exception_message(exc, self.api_key)}))
                continue
            except Exception as exc:
                results.append(_failed_result(ticket_id, type(exc).__name__, {
                    "failure_stage": "transport", "exception_class": type(exc).__name__,
                    "safe_message": _safe_exception_message(exc, self.api_key)}))
                continue

            try:
                raw = json.loads(response_body)
                usage = raw.get("usage") or {}
                content = raw["choices"][0]["message"]["content"]
                result = json.loads(content)
            except Exception as exc:
                usage = raw.get("usage") or {} if "raw" in locals() and isinstance(raw, dict) else {}
                results.append(_failed_result(ticket_id, type(exc).__name__, {
                    "failure_stage": "json_parse", "exception_class": type(exc).__name__,
                    "safe_message": _safe_exception_message(exc, self.api_key),
                    "actual_input_tokens": usage.get("prompt_tokens"),
                    "actual_output_tokens": usage.get("completion_tokens"),
                    "actual_total_tokens": usage.get("total_tokens")}))
                # Do not let one loop iteration's parsed body leak into the next error path.
                if "raw" in locals():
                    del raw
                continue
            if "raw" in locals():
                del raw
            results.append({"ticket_id": ticket_id, "result": result,
                            "actual_input_tokens": usage.get("prompt_tokens"),
                            "actual_output_tokens": usage.get("completion_tokens"),
                            "actual_total_tokens": usage.get("total_tokens")})
        return results
