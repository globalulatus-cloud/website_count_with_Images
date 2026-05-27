import re
from typing import Dict


def count_stats(text: str) -> Dict:
    """
    Count words/characters and detect language type.
    """
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return {
            "count": 0,
            "type": "words",
            "language_group": "Latin",
            "word_count": 0,
            "char_count": 0,
        }

    cjk_pattern = re.compile(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]")
    cjk_chars = cjk_pattern.findall(text)
    cjk_count = len(cjk_chars)

    words = re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE)
    word_count = len(words)

    if cjk_count > word_count * 0.3:
        return {
            "count": cjk_count,
            "type": "characters",
            "language_group": "CJK",
            "word_count": word_count,
            "char_count": len(text),
        }

    return {
        "count": word_count,
        "type": "words",
        "language_group": "Latin",
        "word_count": word_count,
        "char_count": len(text),
    }
