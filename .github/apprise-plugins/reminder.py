# -*- coding: utf-8 -*-
"""Apprise custom notification plugin for the "Reminder" push app.

Usage:  APPRISE_URL=reminder://<32-char push key>

Sends to the Reminder *complex* channel:
  POST https://reminderapi.joyslinktech.com/v1/push/complex
  {"key": "...", "data": {"title", "description", "short", "tags"}}

The push key is never logged.  The endpoint can be overridden with the
REMINDER_API_URL environment variable (used for local testing only).
"""
import json
import logging
import os
import re

import requests
from apprise.decorators import notify

API_URL = "https://reminderapi.joyslinktech.com/v1/push/complex"
TITLE_MAX = 32
DESC_MAX = 1024
SHORT_MAX = 100
TAGS = "微信读书"
SUMMARY_KEYWORDS = (
    "用户", "实际阅读", "目标时长", "成功率", "成功请求", "失败",
    "错误", "异常", "状态", "总用户数",
)

log = logging.getLogger("weread.reminder")


def _truncate(text, limit):
    text = text or ""
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _clean_body(body):
    lines = [ln.strip() for ln in (body or "").strip().splitlines()]
    return "\n".join(lines)


def _extract_key(meta):
    # Prefer the raw URL so that the key's case is preserved exactly.
    url = (meta or {}).get("url") or ""
    m = re.match(r"^\s*reminders?://([^/?#\s]+)", url, re.I)
    key = m.group(1) if m else (meta or {}).get("host") or ""
    return key.strip()


def _build_short(body):
    lines = [ln.strip() for ln in (body or "").splitlines() if ln.strip()]
    picked = [ln for ln in lines if any(k in ln for k in SUMMARY_KEYWORDS)]
    short = " | ".join(picked or lines)
    return _truncate(re.sub(r"\s+", " ", short), SHORT_MAX)


def _find_values(obj, names, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in names and not isinstance(v, (dict, list)):
                out.append("%s=%s" % (k, v))
            _find_values(v, names, out)
    elif isinstance(obj, list):
        for v in obj:
            _find_values(v, names, out)
    return out


def _has_message_id(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() == "messageid" and v:
                return True
            if _has_message_id(v):
                return True
    elif isinstance(obj, list):
        return any(_has_message_id(v) for v in obj)
    return False


@notify(on="reminder", name="Reminder 推送")
def reminder_notify(body, title, notify_type, *args, meta=None, **kwargs):
    key = _extract_key(meta)
    if not key:
        log.error("❌ Reminder 推送失败: 未提供推送密钥")
        return False

    def redact(text):
        return str(text).replace(key, "***")

    payload = {
        "key": key,
        "data": {
            "title": _truncate((title or "通知").strip(), TITLE_MAX),
            "description": _truncate(_clean_body(body), DESC_MAX),
            "short": _build_short(body),
            "tags": TAGS,
        },
    }
    url = os.environ.get("REMINDER_API_URL") or API_URL
    try:
        resp = requests.post(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=15,
        )
    except requests.RequestException as exc:
        log.error("❌ Reminder 推送请求异常: %s", type(exc).__name__)
        return False

    try:
        data = resp.json()
    except ValueError:
        data = None

    if 200 <= resp.status_code < 300 and _has_message_id(data):
        log.info("✅ Reminder 推送成功 (HTTP %s, 已返回 messageId)",
                 resp.status_code)
        return True

    codes = _find_values(
        data, {"code", "errcode", "errorcode", "error_code", "status",
               "message", "msg", "error", "errmsg"}, []
    ) if data is not None else []
    log.error(
        "❌ Reminder 推送失败: HTTP %s, %s",
        resp.status_code,
        redact("; ".join(codes)[:300]) if codes else "响应中无 messageId",
    )
    return False
