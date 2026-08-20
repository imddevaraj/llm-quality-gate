import asyncio
import time
from dataclasses import dataclass
from typing import Any

import httpx

from .domain import Generation


@dataclass
class ProviderConfig:
    model: str
    prompt: str = ""
    temperature: float = 0.0
    max_tokens: int = 512
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "OPENAI_API_KEY"


class LLMProvider:
    async def generate(self, prompt: str) -> Generation:
        raise NotImplementedError


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, config: ProviderConfig, api_key: str, retries: int = 3):
        self.config = config
        self.api_key = api_key
        self.retries = retries

    async def generate(self, prompt: str) -> Generation:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        last_error: Exception | None = None
        for attempt in range(self.retries):
            started = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=120) as client:
                    response = await client.post(
                        f"{self.config.base_url.rstrip('/')}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                usage = data.get("usage", {})
                return Generation(
                    text=data["choices"][0]["message"]["content"],
                    latency_ms=(time.perf_counter() - started) * 1000,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    model=data.get("model", self.config.model),
                )
            except httpx.HTTPStatusError as exc:
                response_body = exc.response.text[:500]
                last_error = RuntimeError(f"HTTP {exc.response.status_code}: {response_body}")
                if exc.response.status_code not in {408, 409, 429} and exc.response.status_code < 500:
                    break
                if attempt < self.retries - 1:
                    retry_after = exc.response.headers.get("retry-after")
                    try:
                        delay = min(float(retry_after), 30) if retry_after else min(2**attempt, 8)
                    except ValueError:
                        delay = min(2**attempt, 8)
                    await asyncio.sleep(delay)
            except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
                last_error = exc
                if attempt < self.retries - 1:
                    await asyncio.sleep(min(2**attempt, 8))
        raise RuntimeError(f"provider failed after {self.retries} attempts: {last_error}")


class StaticProvider(LLMProvider):
    """Useful for local demos and tests; returns a configured output."""

    def __init__(self, output: str):
        self.output = output

    async def generate(self, prompt: str) -> Generation:
        return Generation(text=self.output, latency_ms=1, model="static")
