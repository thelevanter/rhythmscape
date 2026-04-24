"""Anthropic API caller for theoretical agents.

Uses ``anthropic.Anthropic().messages.create`` with:
- ``system`` = theorist prompt (prompt caching enabled via ``cache_control``
  so repeated calls with the same theorist reuse tokens)
- ``user`` = the critique-flag row serialized as YAML (the input schema
  declared in ``prompts/ko/lefebvre.md §운용 주석``)

Prompt caching is strongly recommended since theorist prompts are several
kilobytes and we invoke many times per flag batch. With caching, the
system prompt counts against cache budget on the first call and re-uses
on subsequent calls within the 5-minute TTL window.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import yaml


DEFAULT_MODEL = "claude-opus-4-7"  # hackathon-aligned. User may override to 4-6.
DEFAULT_MAX_TOKENS = 4096  # Day-3 rehearsal showed Foucault axis-6 self-critique
# truncated at 2048; 4096 gives the 6-axis structure room to close.


@dataclass
class AgentResponse:
    theorist: str
    model: str
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


def _format_user_message(context: dict) -> str:
    """Serialize the critique-flag context to the YAML schema the prompts expect."""
    header = (
        "아래 격자는 Rhythmscape 파이프라인이 `critique_flag`로 플래그한 "
        "경험적 관측이다. 당신이 훈련된 이론가의 계열로서 이 격자를 해석하되, "
        "system 프롬프트가 제시한 형식(인식론적 면책 → 핵심 관측 읽기 → "
        "의문문 목록 → 자기-진단)을 그대로 따라라.\n\n"
    )
    body = yaml.safe_dump(context, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return header + "```yaml\n" + body + "```\n"


def call_agent(
    theorist: str,
    system_prompt: str,
    context: dict,
    *,
    client=None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = 1.0,
    enable_prompt_cache: bool = True,
) -> AgentResponse:
    """Invoke a single theorist agent with a critique-flag context."""
    # Lazy import keeps the module importable in environments without the SDK
    if client is None:
        import anthropic

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    if enable_prompt_cache:
        system_blocks = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    else:
        system_blocks = system_prompt

    user_message = _format_user_message(context)
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_blocks,
        messages=[{"role": "user", "content": user_message}],
    )

    text_parts = []
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
    text = "\n".join(text_parts)

    usage = getattr(resp, "usage", None)
    return AgentResponse(
        theorist=theorist,
        model=model,
        text=text,
        input_tokens=getattr(usage, "input_tokens", 0) if usage else 0,
        output_tokens=getattr(usage, "output_tokens", 0) if usage else 0,
        cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) if usage else 0,
        cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) if usage else 0,
        raw=resp.model_dump() if hasattr(resp, "model_dump") else {},
    )


def call_agents_for_flag(
    theorists: tuple[str, ...],
    prompts: dict[str, str],
    context: dict,
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = 1.0,
) -> list[AgentResponse]:
    """Call a sequence of theorist agents with the same context, returning all responses.

    ``prompts`` is a dict of {theorist: system_prompt} produced by
    ``prompt_loader.load_all()``.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    out: list[AgentResponse] = []
    for theorist in theorists:
        if theorist not in prompts:
            raise KeyError(f"no prompt loaded for {theorist!r}")
        resp = call_agent(
            theorist=theorist,
            system_prompt=prompts[theorist],
            context=context,
            client=client,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        out.append(resp)
    return out
