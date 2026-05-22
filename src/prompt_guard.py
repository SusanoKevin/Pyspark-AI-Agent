from __future__ import annotations

import os
import re

_MAX_MESSAGE_LEN  = int(os.getenv("MAX_MESSAGE_LEN",   "2000"))
_MAX_PROMPT_TOKENS = int(os.getenv("MAX_PROMPT_TOKENS", "2048"))

_INJECTION_PATTERNS = re.compile(
    r"ignore\s+(all\s+)?(previous|prior|your|above|the)\s+instructions?"
    r"|disregard\s+(all\s+)?(previous|prior|your|above|the)\s+instructions?"
    r"|forget\s+(all\s+)?(previous|prior|your|above|the)\s+instructions?"
    r"|you\s+are\s+now\b"
    r"|\bact\s+as\s+(a|an|if)\b"
    r"|\bpretend\s+(to\s+be|you\s+are)\b"
    r"|\broleplay\s+as\b"
    r"|\bjailbreak\b"
    r"|\bdeveloper\s+mode\b"
    r"|\bunrestricted\s+mode\b"
    r"|reveal\s+(your|the)\s+(system\s+)?prompt"
    r"|\bDAN\b",
    re.IGNORECASE,
)


def validate_message(message: str) -> str:
    stripped = message.strip()
    if not stripped:
        raise ValueError("Message cannot be empty.")
    if len(stripped) > _MAX_MESSAGE_LEN:
        raise ValueError(
            f"Message too long ({len(stripped)} chars). Maximum is {_MAX_MESSAGE_LEN}."
        )
    if _INJECTION_PATTERNS.search(stripped):
        raise ValueError("Message contains disallowed content.")
    return stripped


def check_token_budget(message: str, history_chars: int = 0) -> None:
    estimated = (len(message) + history_chars) // 4
    if estimated > _MAX_PROMPT_TOKENS:
        raise ValueError(
            f"Input too large (~{estimated} tokens). "
            "Please shorten your message or start a new session."
        )
