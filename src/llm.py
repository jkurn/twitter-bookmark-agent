"""
OpenRouter LLM client.

Uses the OpenAI-compatible client pointed at OpenRouter's API.
Any model on OpenRouter can be used by changing LLM_MODEL in .env.

Usage:
    from llm import chat, LLM_MODEL

    response = chat(
        messages=[{"role": "user", "content": "Hello"}],
        system="You are a helpful assistant.",
    )
    print(response)  # str
"""

from openai import OpenAI

from config import settings

# Single shared client — reuse across calls (connection pooling)
_client = OpenAI(
    api_key=settings.openrouter_api_key,
    base_url=settings.openrouter_base_url,
)

LLM_MODEL = settings.llm_model


def chat(
    messages: list[dict],
    system: str | None = None,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> str:
    """
    Send a chat request to OpenRouter and return the response text.

    Args:
        messages: List of {"role": "user"|"assistant", "content": "..."} dicts.
        system:   Optional system prompt (prepended as a system message).
        model:    Override the default model for this call only.
                  E.g. "openai/gpt-4o" or "anthropic/claude-haiku-4-5".
        temperature: Sampling temperature.
        max_tokens: Max tokens in the response.

    Returns:
        The assistant's reply as a plain string.
    """
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    response = _client.chat.completions.create(
        model=model or LLM_MODEL,
        messages=full_messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()


def chat_with_model(model: str, messages: list[dict], system: str | None = None, **kwargs) -> str:
    """Convenience wrapper to call a specific model explicitly."""
    return chat(messages=messages, system=system, model=model, **kwargs)
