"""LLM gateway: provider-agnostic interface supporting OpenAI + Gemini."""
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal

import structlog
from openai import AsyncOpenAI

from app.core.config import settings

log = structlog.get_logger(__name__)

ProviderName = Literal["openai", "google"]


@dataclass(slots=True)
class LLMResult:
    content: str
    model: str
    tokens_prompt: int
    tokens_completion: int


class LLMGateway:
    def __init__(self) -> None:
        self.openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def chat(
        self,
        messages: list[dict],
        *,
        model: str = settings.OPENAI_MODEL_CHAT,
        max_tokens: int = settings.RAG_LLM_MAX_TOKENS,
        temperature: float = settings.RAG_LLM_TEMPERATURE,
        stream: bool = False,
    ) -> LLMResult | AsyncIterator[str]:
        if not stream:
            return await self._openai_chat(messages, model, max_tokens, temperature)
        return self._openai_stream(messages, model, max_tokens, temperature)

    async def _openai_chat(self, messages, model, max_tokens, temperature) -> LLMResult:
        resp = await self.openai.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        choice = resp.choices[0]
        return LLMResult(
            content=choice.message.content or "",
            model=resp.model,
            tokens_prompt=resp.usage.prompt_tokens if resp.usage else 0,
            tokens_completion=resp.usage.completion_tokens if resp.usage else 0,
        )

    async def _openai_stream(self, messages, model, max_tokens, temperature) -> AsyncIterator[str]:
        stream = await self.openai.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def google_chat(
        self,
        messages: list[dict],
        *,
        model: str = settings.GOOGLE_MODEL_CHAT,
        max_tokens: int = 800,
    ) -> LLMResult:
        import google.generativeai as genai

        genai.configure(api_key=settings.GOOGLE_API_KEY)
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        convo = [m for m in messages if m["role"] != "system"]
        m = genai.GenerativeModel(model, system_instruction=system)
        resp = await m.generate_content_async(
            [{"role": "user" if c["role"] == "user" else "model", "parts": [c["content"]]} for c in convo],
            generation_config={"max_output_tokens": max_tokens},
        )
        return LLMResult(
            content=resp.text or "",
            model=model,
            tokens_prompt=0,
            tokens_completion=0,
        )
