"""DeepSeek-klient. Endast infrastruktur; ingen domän-, API- eller UI-logik."""
from __future__ import annotations

import time
from typing import Any, Mapping, Sequence

from openai import OpenAI

from .settings import DeepSeekSettings


class DeepSeekError(RuntimeError):
    """Omsluter leverantörsfel utan att läcka hemligheter eller payloads."""


class DeepSeekClient:
    """Tunn, testbar omslutning runt DeepSeeks OpenAI-kompatibla API."""

    def __init__(self, settings: DeepSeekSettings, *, client: OpenAI | None = None,
                 timeout_seconds: float = 120.0, max_retries: int = 2,
                 backoff_seconds: float = 0.5):
        self._settings = settings
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._backoff = backoff_seconds
        self._client = client or OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

    def __repr__(self) -> str:
        return f"DeepSeekClient(model={self._settings.model!r}, base_url={self._settings.base_url!r})"

    def chat(self, messages: Sequence[Mapping[str, str]], *,
             temperature: float = 0.2, max_tokens: int | None = None,
             response_format: dict | None = None) -> str:
        """Returnerar assistentens svaretxt. Kastar DeepSeekError vid fel."""
        if not messages:
            raise DeepSeekError("messages får inte vara tomt")
        kwargs: dict[str, Any] = {
            "model": self._settings.model,
            "messages": list(messages),
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if response_format is not None:
            kwargs["response_format"] = response_format

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.chat.completions.create(**kwargs)
                choice = response.choices[0] if response.choices else None
                content = getattr(getattr(choice, "message", None), "content", None)
                if not content:
                    raise DeepSeekError("Tomt svar från DeepSeek")
                return content
            except DeepSeekError:
                last_error = DeepSeekError("Tomt svar från DeepSeek")
                if attempt < self._max_retries:
                    time.sleep(self._backoff * (2 ** attempt))
                    continue
                raise
            except Exception as exc:
                last_error = exc
                if attempt < self._max_retries:
                    time.sleep(self._backoff * (2 ** attempt))
        raise DeepSeekError(
            f"DeepSeek-anrop misslyckades: {type(last_error).__name__}"
        ) from None

    def chat_with_tools(self, messages: list, *, tools: list | None = None,
                        temperature: float = 0.2, max_tokens: int | None = None,
                        thinking: bool = False) -> Any:
        """Returnerar hela message-objektet (inkl. tool_calls och reasoning_content)."""
        kwargs: dict[str, Any] = {
            "model": self._settings.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if tools is not None:
            kwargs["tools"] = tools
            kwargs["extra_body"] = {
                "thinking": {"type": "enabled" if thinking else "disabled"}
            }

        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message
