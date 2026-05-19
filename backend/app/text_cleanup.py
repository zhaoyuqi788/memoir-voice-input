from __future__ import annotations

import re

FILLER_PATTERNS = [
    r"[嗯呃额啊]{1,3}[，,、\s]*",
    r"(?:这个|那个|就是|然后呢|就是说|你知道吧|对吧)[，,、\s]*",
]

ENDING_PUNCTUATION = "。！？"


def strip_fillers(text: str) -> str:
    normalized = text.strip()
    for pattern in FILLER_PATTERNS:
        normalized = re.sub(pattern, "", normalized)
    return normalized


def compress_repetitions(text: str) -> str:
    value = text
    for size in range(1, 5):
        pattern = re.compile(rf"(.{{{size}}})\1+")
        value = pattern.sub(r"\1", value)
    return value


def normalize_spacing(text: str) -> str:
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[，,、]{2,}", "，", text)
    text = re.sub(r"[。]{2,}", "。", text)
    return text.strip("，,、 ")


def add_light_punctuation(text: str, max_clause_chars: int = 28) -> str:
    if not text:
        return ""
    chars: list[str] = []
    count = 0
    for char in text:
        chars.append(char)
        if char in "，。！？；":
            count = 0
            continue
        count += 1
        if count >= max_clause_chars:
            chars.append("，")
            count = 0
    result = "".join(chars).rstrip("，,、； ")
    if result and result[-1] not in ENDING_PUNCTUATION:
        result += "。"
    return result


def clean_transcript(text: str) -> str:
    value = strip_fillers(text)
    value = compress_repetitions(value)
    value = normalize_spacing(value)
    return add_light_punctuation(value)
