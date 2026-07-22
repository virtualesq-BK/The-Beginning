import json
import os

from dotenv import load_dotenv

load_dotenv()

_ANTHROPIC_CLIENT = None
_OPENAI_CLIENT = None

if os.environ.get("OPENAI_API_KEY"):
    from openai import OpenAI

    _OPENAI_CLIENT = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ.get("OPENAI_BASE_URL"),
        default_headers={"User-Agent": "curl/8.4.0"},
    )

if os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("ANTHROPIC_ENABLE", "0") == "1":
    from anthropic import Anthropic

    _ANTHROPIC_CLIENT = Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        base_url=os.environ.get("ANTHROPIC_BASE_URL"),
    )

_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
_OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def _extract_text(response) -> str:
    if hasattr(response, "content"):
        parts = []
        for block in response.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        if parts:
            return "".join(parts)
    if hasattr(response, "choices") and response.choices:
        return response.choices[0].message.content or ""
    return ""


def chat(system: str, user: str, temperature: float = 0.2, json_mode: bool = False) -> str:
    if _OPENAI_CLIENT is not None:
        kwargs = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = _OPENAI_CLIENT.chat.completions.create(
            model=_OPENAI_MODEL,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            **kwargs,
        )
        return _extract_text(resp)

    if _ANTHROPIC_CLIENT is not None:
        prompt = user
        if json_mode:
            prompt = f"{user}\n\nRespond with valid JSON only."
        try:
            resp = _ANTHROPIC_CLIENT.messages.create(
                model=_MODEL,
                max_tokens=2048,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return _extract_text(resp)
        except Exception:
            pass

    if _OPENAI_CLIENT is None:
        raise RuntimeError("No LLM client configured")



def chat_json(system: str, user: str, temperature: float = 0.2) -> dict:
    raw = chat(system, user, temperature=temperature, json_mode=True)
    return json.loads(raw)


_EMBED_MODEL = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")


def embed(texts: list[str]) -> list[list[float]]:
    if _OPENAI_CLIENT is None:
        raise RuntimeError("OpenAI embeddings client is not configured")
    resp = _OPENAI_CLIENT.embeddings.create(model=_EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]
