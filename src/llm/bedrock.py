"""Amazon Bedrock LLM implementation."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any, TypeVar

import boto3
import structlog

from .base import LLMConfig, LLMProvider, LLMResponse, LLMUsage

if TYPE_CHECKING:
    from pydantic import BaseModel

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound="BaseModel | None")


class BedrockLLMProvider(LLMProvider):
    """Amazon Bedrock LLM provider using boto3.

    Supports Claude 3.x models via the messages API.
    """

    def __init__(
        self,
        model_id: str,
        region: str,
        *,
        endpoint_url: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        top_p: float = 0.9,
    ) -> None:
        self._model_id = model_id
        self._region = region
        self._endpoint_url = endpoint_url
        self._default_config = LLMConfig(
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
        )
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            endpoint_url=endpoint_url,
        )

    @property
    def provider_name(self) -> str:
        return "bedrock"

    def _build_messages(self, prompt: str, system_prompt: str | None) -> list[dict[str, Any]]:
        """Build Anthropic messages payload."""
        messages = []
        if system_prompt:
            messages.append({"role": "user", "content": f"\n\nSystem: {system_prompt}\n\n{prompt}"})
        else:
            messages.append({"role": "user", "content": prompt})
        return messages

    def _call_bedrock(self, body: dict[str, Any]) -> dict[str, Any]:
        """Make the raw Bedrock API call."""
        response = self._client.invoke_model(
            modelId=self._model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        return json.loads(response["body"].read().decode("utf-8"))

    async def complete(self, prompt: str, config: LLMConfig | None = None) -> LLMResponse:
        """Send a plain text prompt to Bedrock."""
        config = config or self._default_config

        body: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "messages": self._build_messages(prompt, config.system_prompt),
        }
        if config.stop_sequences:
            body["stop_sequences"] = config.stop_sequences

        logger.debug("bedrock.complete", model=self._model_id, prompt_len=len(prompt))
        result = self._call_bedrock(body)

        content = result.get("content", [])
        text = ""
        if content and isinstance(content, list):
            for block in content:
                if block.get("type") == "text":
                    text += block.get("text", "")

        return LLMResponse(
            content=text,
            model=self._model_id,
            usage=LLMUsage(
                prompt_tokens=result.get("usage", {}).get("input_tokens", 0),
                completion_tokens=result.get("usage", {}).get("output_tokens", 0),
                total_tokens=result.get("usage", {}).get("total_tokens", 0),
            ),
            finish_reason=result.get("stop_reason"),
        )

    async def structured_complete(
        self,
        prompt: str,
        output_schema: type[T],
        config: LLMConfig | None = None,
    ) -> T:
        """Call Bedrock and parse the response into a Pydantic model.

        Uses a JSON-schema-constrained prompt to improve parsing reliability.
        """
        import inspect
        from pydantic import BaseModel

        config = config or self._default_config
        model: type[BaseModel] = output_schema  # type: ignore[assignment]

        # Build JSON schema for the output type
        schema_json = model.model_json_schema() if hasattr(model, "model_json_schema") else "{}"

        structured_prompt = (
            f"{prompt}\n\n"
            "You must respond ONLY with valid JSON matching this schema:\n"
            f"{schema_json}\n\n"
            "Respond with nothing but the JSON object."
        )

        result = await self.complete(structured_prompt, config)

        # Strip markdown code fences if present
        text = result.content.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("bedrock.json_parse_error", raw=text[:500], error=str(exc))
            raise ValueError(f"Failed to parse LLM response as JSON: {exc}") from exc

        if model is None:
            return None  # type: ignore[return-value]

        return model.model_validate(parsed)  # type: ignore[return-value]
