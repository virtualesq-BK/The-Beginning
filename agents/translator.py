from .llm_client import chat_json

_SYSTEM = """너는 해외 건설·인프라 법률 문서 전문 번역가다.
입력된 조항 원문(영문 또는 국문)을 한국어로 정확히 번역하라.
FIDIC, EPC, 지체상금(LD), 하자담보(Defects Liability), 불가항력(Force Majeure) 등
건설 법률 전문 용어는 관용적으로 통용되는 한국어 용어를 사용하라.
번역 후 스스로 원문과 대조하여 의미 누락/왜곡이 없는지 검증하고 confidence(0~1)를 매겨라.

반드시 아래 JSON 스키마로만 응답하라:
{
  "translated_text": "번역문",
  "confidence": 0.0,
  "notes": "번역 시 주의사항이나 모호한 부분 (없으면 빈 문자열)"
}
"""


def translate_clause(original_text: str) -> dict:
    return chat_json(_SYSTEM, original_text, temperature=0.2)
