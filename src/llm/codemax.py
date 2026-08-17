"""Anthropic LLM provider via Codemax proxy — OpenAI-compatible /v1/chat/completions endpoint."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, TypeVar

import httpx
import structlog

from .base import LLMConfig, LLMProvider, LLMResponse, LLMUsage

if TYPE_CHECKING:
    from pydantic import BaseModel

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound="BaseModel | None")


class CodemaxLLMProvider(LLMProvider):
    """Anthropic LLM via Codemax proxy.

    Codemax exposes an OpenAI-compatible /v1/chat/completions endpoint
    that proxies to Anthropic models. This lets us reuse the familiar
    OpenAI API shape without vendor lock-in.

    Docs: https://www.codemax.pro/docs
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.codemax.pro",
        model: str = "claude-sonnet-5",
        *,
        timeout: float = 120.0,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        top_p: float = 0.9,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._default_config = LLMConfig(
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
        )

    @property
    def provider_name(self) -> str:
        return "codemax"

    async def complete(
        self,
        prompt: str,
        config: LLMConfig | None = None,
    ) -> LLMResponse:
        cfg = config or self._default_config

        messages: list[dict[str, str]]
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt  # type: ignore[assignment]

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": cfg.temperature,
            "max_tokens": cfg.max_tokens,
            "top_p": cfg.top_p,
        }
        if cfg.stop_sequences:
            payload["stop"] = cfg.stop_sequences

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )

        if resp.status_code != 200:
            logger.error("codemax.request_failed", status=resp.status_code, body=resp.text[:500])
            resp.raise_for_status()

        data = resp.json()
        choice = data["choices"][0]
        content = choice["message"]["content"]

        usage = data.get("usage")
        llm_usage = None
        if usage:
            llm_usage = LLMUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )

        return LLMResponse(
            content=content,
            model=data.get("model", self._model),
            usage=llm_usage,
            finish_reason=choice.get("finish_reason"),
        )

    async def structured_complete(
        self,
        prompt: str,
        output_schema: type[T],
        config: LLMConfig | None = None,
    ) -> T:
        cfg = config or self._default_config
        # Extract field names and descriptions without full meta-schema $defs to avoid LLM schema-echoing
        field_hints = {}
        for fname, ffield in output_schema.model_fields.items():
            field_hints[fname] = fld_desc = str(ffield.description or ffield.annotation or "value")

        structured_prompt = (
            f"{prompt}\n\n"
            "CRITICAL REQUIREMENT:\n"
            "Return ONLY a valid JSON object containing your actual analysis values for these fields:\n"
            f"{json.dumps(field_hints, indent=2)}\n\n"
            "Do NOT return a schema definition. Return a populated JSON object."
        )

        result = await self.complete(structured_prompt, config)

        text = result.content.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("codemax.json_parse_error", raw=text[:500], error=str(exc))
            raise ValueError(f"Failed to parse LLM response as JSON: {exc}") from exc

        if isinstance(parsed, dict):
            # If wrapped in top-level key like {"decision": {...}} or {"result": {...}}
            if "properties" in parsed and "type" in parsed:
                parsed = parsed.get("properties", parsed)
            for k in ("decision", "result", "data", "output"):
                if k in parsed and isinstance(parsed[k], dict):
                    parsed = parsed[k]
                    break

        return output_schema.model_validate(parsed)  # type: ignore[return-value]
