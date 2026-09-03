import json
import os

from dotenv import load_dotenv

load_dotenv()

_ANTHROPIC_CLIENT = None
_OPENAI_CLIENT = None
_UNIVERSAL_CLIENT = None
_DEEPSEEK_CLIENT = None

if os.environ.get("Universal_API"):
    from openai import OpenAI

    _UNIVERSAL_CLIENT = OpenAI(
        api_key=os.environ["Universal_API"],
        base_url=os.environ.get("Universal_URL"),
        default_headers={"User-Agent": "curl/8.4.0"},
    )

if os.environ.get("OPENAI_API_KEY"):
    from openai import OpenAI

    _OPENAI_CLIENT = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ.get("OPENAI_BASE_URL"),
        default_headers={"User-Agent": "curl/8.4.0"},
    )

_DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("deepseek_API_Key")
if _DEEPSEEK_API_KEY:
    from openai import OpenAI

    _DEEPSEEK_CLIENT = OpenAI(
        api_key=_DEEPSEEK_API_KEY,
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
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
_DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
_UNIVERSAL_MODEL = os.environ.get("Universal_MODEL", "gpt-5-nano-chat")


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


def _is_quota_exhausted(exc: Exception) -> bool:
    """사용량/쿼터 소진(429, insufficient_quota 등)으로 실패했는지 판별한다."""
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True
    body = getattr(exc, "body", None) or {}
    code = ""
    if isinstance(body, dict):
        code = str(body.get("code") or body.get("error", {}).get("code") or "")
    message = str(exc)
    return (
        "insufficient_quota" in code
        or "insufficient_quota" in message
        or "quota" in message.lower()
        or "rate limit" in message.lower()
    )


def _chat_openai(system: str, user: str, temperature: float, json_mode: bool):
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


def _chat_deepseek(system: str, user: str, temperature: float, json_mode: bool):
    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = _DEEPSEEK_CLIENT.chat.completions.create(
        model=_DEEPSEEK_MODEL,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        **kwargs,
    )
    return _extract_text(resp)


def chat(system: str, user: str, temperature: float = 0.2, json_mode: bool = False) -> str:
    if _OPENAI_CLIENT is not None:
        try:
            return _chat_openai(system, user, temperature, json_mode)
        except Exception as exc:
            if _DEEPSEEK_CLIENT is not None and _is_quota_exhausted(exc):
                return _chat_deepseek(system, user, temperature, json_mode)
            raise

    if _DEEPSEEK_CLIENT is not None:
        return _chat_deepseek(system, user, temperature, json_mode)

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

    raise RuntimeError("No LLM client configured")



def chat_universal(
    system: str,
    user: str,
    temperature: float = 0.2,
    json_mode: bool = False,
    model: str | None = None,
) -> str:
    """Universal_API/Universal_URL 게이트웨이(monorouter) 전용 클라이언트로 호출한다."""
    if _UNIVERSAL_CLIENT is None:
        raise RuntimeError("Universal LLM client is not configured (Universal_API/Universal_URL)")
    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = _UNIVERSAL_CLIENT.chat.completions.create(
        model=model or _UNIVERSAL_MODEL,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        **kwargs,
    )
    return _extract_text(resp)


def chat_json(system: str, user: str, temperature: float = 0.2) -> dict:
    raw = chat(system, user, temperature=temperature, json_mode=True)
    return json.loads(raw)


_EMBED_MODEL = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")


def embed(texts: list[str]) -> list[list[float]]:
    if _OPENAI_CLIENT is None:
        raise RuntimeError("OpenAI embeddings client is not configured")
    resp = _OPENAI_CLIENT.embeddings.create(model=_EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]
