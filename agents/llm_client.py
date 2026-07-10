import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_client = OpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_BASE_URL"],
    default_headers={"User-Agent": "curl/8.4.0"},
)
_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def chat(system: str, user: str, temperature: float = 0.2, json_mode: bool = False) -> str:
    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = _client.chat.completions.create(
        model=_MODEL,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        **kwargs,
    )
    return resp.choices[0].message.content


def chat_json(system: str, user: str, temperature: float = 0.2) -> dict:
    raw = chat(system, user, temperature=temperature, json_mode=True)
    return json.loads(raw)


_EMBED_MODEL = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")


def embed(texts: list[str]) -> list[list[float]]:
    resp = _client.embeddings.create(model=_EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]
