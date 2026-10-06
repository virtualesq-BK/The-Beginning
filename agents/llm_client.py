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
_DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

# 역할(tier)별 모델:
#   worker = 싸게 많이 처리하는 작업자 (파싱·번역·요약)
#   agent  = 더 똑똑한 Agent 작업자 (조항 위험 분석·계약서 생성)
#   expert = 최종 판단을 맡길 전문가
TIER_WORKER = "worker"
TIER_AGENT = "agent"
TIER_EXPERT = "expert"

_TIER_MODELS = {
    TIER_WORKER: os.environ.get("LLM_MODEL_WORKER", "gpt-5-mini"),
    TIER_AGENT: os.environ.get("LLM_MODEL_AGENT", "gpt-5.6-luna"),
    TIER_EXPERT: os.environ.get("LLM_MODEL_EXPERT", "gpt-5.6-sol"),
}
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


def _client_for_tier(tier: str):
    """모든 티어에서 Universal 게이트웨이를 우선 사용한다.
    copa.codyssey.kr(OPENAI_CLIENT)는 system 메시지를 지원하지 않아 파이프라인과 호환되지 않음."""
    if _UNIVERSAL_CLIENT is not None:
        return _UNIVERSAL_CLIENT
    return _OPENAI_CLIENT


def _is_gpt5_family(model: str) -> bool:
    return model.startswith("gpt-5")


def _chat_openai(system: str, user: str, temperature: float, json_mode: bool, tier: str = TIER_WORKER):
    if tier not in _TIER_MODELS:
        raise ValueError(f"Unknown LLM tier: {tier!r} (expected one of {sorted(_TIER_MODELS)})")
    model = _TIER_MODELS[tier]
    kwargs: dict = {}
    # GPT-5 계열 추론 모델은 temperature / response_format 파라미터를 지원하지 않는다.
    if not _is_gpt5_family(model):
        kwargs["temperature"] = temperature
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
    resp = _client_for_tier(tier).chat.completions.create(
        model=model,
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


def chat(
    system: str,
    user: str,
    temperature: float = 0.2,
    json_mode: bool = False,
    tier: str = TIER_WORKER,
) -> str:
    if _client_for_tier(tier) is not None:
        try:
            return _chat_openai(system, user, temperature, json_mode, tier)
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


def _extract_json_str(raw: str) -> str:
    """마크다운 코드 블록(```json ... ```) 또는 순수 텍스트에서 JSON 문자열을 추출한다."""
    raw = raw.strip()
    # ```json ... ``` 또는 ``` ... ``` 블록 제거
    if raw.startswith("```"):
        lines = raw.splitlines()
        # 첫 줄(```json 또는 ```) 과 마지막 줄(```) 제거
        inner = lines[1:] if lines[-1].strip() == "```" else lines[1:]
        if inner and inner[-1].strip() == "```":
            inner = inner[:-1]
        raw = "\n".join(inner).strip()
    return raw


def chat_json(system: str, user: str, temperature: float = 0.2, tier: str = TIER_WORKER) -> dict:
    raw = chat(system, user, temperature=temperature, json_mode=True, tier=tier)
    return json.loads(_extract_json_str(raw))


_EMBED_MODEL = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")


def embed(texts: list[str]) -> list[list[float]]:
    """Universal 게이트웨이 우선 — copa.codyssey.kr은 /v1/embeddings 미지원 (403 반환).
    _client_for_tier()와 동일한 라우팅 전략을 따른다."""
    client = _UNIVERSAL_CLIENT if _UNIVERSAL_CLIENT is not None else _OPENAI_CLIENT
    if client is None:
        raise RuntimeError("임베딩 클라이언트가 설정되지 않았습니다 (Universal_API 또는 OPENAI_API_KEY 필요)")
    resp = client.embeddings.create(model=_EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]
