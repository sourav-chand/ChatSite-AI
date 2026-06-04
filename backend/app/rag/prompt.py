"""Prompt assembly + injection detection."""
from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

from app.core.config import settings
from app.core.exceptions import PromptInjectionError

log = structlog.get_logger(__name__)

INJECTION_PATTERNS = [
    r"ignore (?:all )?previous (?:instructions|directives)",
    r"disregard (?:the )?(?:system|previous)",
    r"system\s*:\s*",
    r"\bact as\b",
    r"\byou are now\b",
    r"\bnew instructions\b",
    r"\boverride\b",
    r"<\s*system\s*>",
    r"reveal (?:your|the) (?:system|hidden) prompt",
    r"forget (?:everything|all|your)",
    r"jailbreak",
    r"do anything now",
]


def detect_injection(text: str) -> str | None:
    lowered = text.lower()
    for pat in INJECTION_PATTERNS:
        if re.search(pat, lowered):
            return pat
    return None


def validate_query(text: str) -> str:
    text = text.strip()
    if len(text) > settings.RAG_MAX_QUERY_LEN:
        raise PromptInjectionError(f"Query exceeds {settings.RAG_MAX_QUERY_LEN} chars")
    if not text:
        raise PromptInjectionError("Empty query")
    hit = detect_injection(text)
    if hit:
        log.warning("prompt_injection.detected", pattern=hit, query=text[:100])
        raise PromptInjectionError("Query rejected by safety filter")
    return text


@dataclass(slots=True)
class PromptBundle:
    system: str
    user: str


def build_prompt(
    *,
    company_name: str,
    chunks: list[dict],
    history: list[dict],
    question: str,
) -> PromptBundle:
    context_lines: list[str] = []
    for i, c in enumerate(chunks, 1):
        title = c.get("title") or c.get("source_url", "")
        url = c.get("source_url", "")
        context_lines.append(
            f"[{i}] {title}\nURL: {url}\n{c['content']}\n"
        )
    context = "\n".join(context_lines) or "No context available."

    sys_prompt = (
        f"You are a helpful assistant for {company_name}. Answer based ONLY on the "
        f"provided context. If the answer is not in the context, say so clearly. "
        f"Never make up information. Always cite the source URL when referencing content.\n\n"
        f"Context:\n{context}\n\n"
    )

    history_text = ""
    if history:
        history_text = "Conversation history (last turns):\n"
        for turn in history[-settings.RAG_HISTORY_TURNS :]:
            role = turn.get("role", "user").upper()
            history_text += f"{role}: {turn.get('content', '')}\n"

    user_prompt = f"{history_text}\nUser question: {question}\nAnswer:"
    return PromptBundle(system=sys_prompt, user=user_prompt)
