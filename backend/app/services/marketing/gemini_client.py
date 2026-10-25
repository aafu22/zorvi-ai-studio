"""The only file that talks to Google's SDK. Everything else sees plain strings and AiProviderError.

Written against the `google-genai` package (`pip install google-genai`).
The import happens inside __init__ so the rest of the app, and the tests, work without it.
"""

import logging
from typing import Literal

from pydantic import BaseModel

logger = logging.getLogger(__name__)

ErrorKind = Literal["not_installed", "auth", "rate_limit", "timeout", "bad_request", "unavailable"]


class AiProviderError(Exception):
    def __init__(self, kind: ErrorKind, message: str):
        super().__init__(message)
        self.kind = kind
        self.message = message


class GeminiClient:
    def __init__(self, api_key: str, model: str, timeout_seconds: int):
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - depends on the local environment
            raise AiProviderError(
                "not_installed",
                "The google-genai package is not installed. Run: pip install -r requirements.txt",
            ) from exc
        self._types = types
        self._model = model
        # HttpOptions.timeout is in milliseconds.
        self._client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=timeout_seconds * 1000))

    @property
    def model(self) -> str:
        return self._model

    def generate_json(self, system: str, prompt: str, schema: type[BaseModel]) -> str:
        """Ask the model for JSON matching `schema` and return the raw JSON text."""
        types = self._types
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=0.9,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
        except Exception as exc:  # noqa: BLE001 - translated below; never log request content or the key
            raise _translate(exc) from None
        text = getattr(response, "text", None)
        if not text:
            raise AiProviderError("bad_request", "The model returned an empty answer.")
        return text


def _translate(exc: Exception) -> AiProviderError:
    code = getattr(exc, "code", None)
    message = str(getattr(exc, "message", "") or exc).lower()
    name = type(exc).__name__
    logger.warning("Gemini call failed: %s (code=%s)", name, code)  # class + status only
    if code == 429 or "resource_exhausted" in message or "quota" in message:
        return AiProviderError("rate_limit", "Gemini's rate limit or quota was reached.")
    if code in (401, 403) or "api key" in message or "api_key" in message:
        return AiProviderError("auth", "Gemini rejected the API key.")
    if code == 404:
        return AiProviderError("bad_request", "Gemini does not know that model name. Check GEMINI_MODEL.")
    if code in (408, 504) or "timeout" in name.lower() or "timed out" in message or isinstance(exc, TimeoutError):
        return AiProviderError("timeout", "Gemini took too long to answer.")
    if isinstance(code, int) and code >= 500:
        return AiProviderError("unavailable", "Gemini is temporarily unavailable.")
    if isinstance(code, int) and 400 <= code < 500:
        return AiProviderError("bad_request", "Gemini could not process that request.")
    return AiProviderError("unavailable", "Could not reach Gemini.")
