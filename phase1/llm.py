"""Minimal OpenAI Responses API transport, with bounded calls and no SDK dependency."""
import json
import os
import shlex
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMError(RuntimeError):
    pass


def load_env(path=Path(".env")):
    """Read simple KEY=value lines; never execute shell code or overwrite the environment."""
    path = Path(path)
    if not path.exists():
        return
    allowed = {"OPENAI_API_KEY", "OPENAI_MODEL"}
    for number, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key = key.strip().removeprefix("export ")
        if not separator or key not in allowed:
            raise LLMError(f"Unsupported .env entry on line {number}; use OPENAI_API_KEY or OPENAI_MODEL.")
        try:
            parts = shlex.split(value, comments=True)
        except ValueError:
            raise LLMError(f"Invalid quoting in .env on line {number}.") from None
        if len(parts) > 1:
            raise LLMError(f"Invalid .env value on line {number}.")
        os.environ.setdefault(key, parts[0] if parts else "")


class OpenAIResponses:
    provider = "openai"

    def __init__(self, model, max_calls=60, max_output_tokens=1400):
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not self.api_key or self.api_key == "replace-with-your-key":
            raise LLMError("Set OPENAI_API_KEY in your environment or the local .env file; never commit it.")
        self.max_calls = max_calls
        self.max_output_tokens = max_output_tokens
        self.calls = 0

    def create(self, instructions, history, tools):
        if self.calls >= self.max_calls:
            raise LLMError(f"Run stopped at the {self.max_calls}-request API budget.")
        self.calls += 1
        payload = {
            "model": self.model, "instructions": instructions, "input": history,
            "tools": tools, "parallel_tool_calls": False,
            "max_output_tokens": self.max_output_tokens, "store": False,
            # Preserve encrypted reasoning items in memory if a reasoning model is selected.
            "include": ["reasoning.encrypted_content"],
        }
        request = Request("https://api.openai.com/v1/responses",
                          data=json.dumps(payload).encode(), method="POST",
                          headers={"Authorization": f"Bearer {self.api_key}",
                                   "Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=60) as response:
                result = json.load(response)
        except HTTPError as error:
            # Do not print response bodies or headers that could expose credentials.
            raise LLMError(f"OpenAI HTTP {error.code}; check API access, model, and billing. No automatic retry.") from None
        except (URLError, TimeoutError, OSError, HTTPException):
            raise LLMError("OpenAI request failed or timed out; no automatic retry.") from None
        except (ValueError, TypeError):
            raise LLMError("OpenAI returned an invalid JSON response.") from None
        if not isinstance(result, dict):
            raise LLMError("OpenAI returned an unexpected response shape.")
        return result


def public_items(items):
    """Trace visible outputs, not encrypted reasoning or internal chain-of-thought."""
    visible = []
    for item in items:
        if item.get("type") == "reasoning":
            visible.append({"type": "reasoning", "summary": item.get("summary", [])})
        else:
            visible.append(item)
    return visible


def validate_response(response):
    """Check the protocol envelope before any model-requested effects execute."""
    if not isinstance(response, dict) or not isinstance(response.get("output"), list):
        raise LLMError("Model returned an invalid response envelope.")
    if not isinstance(response.get("id"), str) or not isinstance(response.get("model"), str):
        raise LLMError("Model response is missing its response ID or model.")
    seen = set()
    for item in response["output"]:
        if not isinstance(item, dict) or not isinstance(item.get("type"), str):
            raise LLMError("Model returned an invalid output item.")
        if item["type"] == "function_call":
            if any(not isinstance(item.get(key), str) or not item[key]
                   for key in ("call_id", "name", "arguments")):
                raise LLMError("Model returned a malformed function call.")
            if item["call_id"] in seen:
                raise LLMError("Model returned duplicate function call IDs.")
            seen.add(item["call_id"])
        if item["type"] == "message":
            if not isinstance(item.get("content"), list) or any(
                    not isinstance(part, dict) or
                    (part.get("type") == "output_text" and not isinstance(part.get("text"), str))
                    for part in item["content"]):
                raise LLMError("Model returned malformed message content.")
