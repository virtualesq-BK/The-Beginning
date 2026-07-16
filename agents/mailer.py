"""전문가 연결 요청 메일 발송."""

from __future__ import annotations

import json
import os
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage
from typing import Literal

ExpertRequestType = Literal["translation_review", "legal_expert"]

REQUEST_LABELS: dict[ExpertRequestType, str] = {
    "translation_review": "전문가 번역 검수",
    "legal_expert": "해외 법률 전문가 연결",
}


def _expert_email() -> str:
    return os.getenv("EXPERT_EMAIL", "virtual.esq@gmail.com")


def _send_via_smtp(subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    to_email = _expert_email()

    if not user or not password:
        raise RuntimeError("SMTP_USER / SMTP_PASSWORD 가 설정되지 않았습니다.")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)


def _send_via_formsubmit(subject: str, body: str) -> None:
    to_email = _expert_email()
    payload = json.dumps(
        {
            "name": "The Beginning",
            "message": body,
            "_subject": subject,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        f"https://formsubmit.co/ajax/{to_email}",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Origin": os.getenv("PUBLIC_APP_ORIGIN", "http://localhost:5173"),
            "Referer": os.getenv("PUBLIC_APP_ORIGIN", "http://localhost:5173") + "/",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"FormSubmit 발송 실패 (HTTP {e.code}): {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"FormSubmit 연결 실패: {e.reason}") from e

    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        data = {"raw": raw}

    if isinstance(data, dict) and str(data.get("success")).lower() == "false":
        message = data.get("message") or "FormSubmit 발송에 실패했습니다."
        if "Activation" in message or "Activate" in message:
            raise RuntimeError(
                f"{_expert_email()} 받은편지함에서 FormSubmit 활성화 메일(Activate Form)을 "
                "확인하고 링크를 클릭한 뒤, 다시 요청해 주세요."
            )
        raise RuntimeError(message)


def send_expert_request(request_type: ExpertRequestType) -> dict:
    if request_type not in REQUEST_LABELS:
        raise ValueError(f"지원하지 않는 요청 유형입니다: {request_type}")

    label = REQUEST_LABELS[request_type]
    subject = f"[The Beginning] {label} 요청"
    body = (
        f"The Beginning 서비스에서 '{label}' 요청이 접수되었습니다.\n\n"
        f"요청 유형: {label}\n"
        f"수신 주소: {_expert_email()}\n"
    )

    # SMTP가 설정되어 있으면 우선 사용, 없으면 FormSubmit으로 발송
    if os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"):
        _send_via_smtp(subject, body)
        channel = "smtp"
    else:
        _send_via_formsubmit(subject, body)
        channel = "formsubmit"

    return {
        "ok": True,
        "request_type": request_type,
        "label": label,
        "to": _expert_email(),
        "channel": channel,
    }
