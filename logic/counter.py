import re
from typing import Dict

def count_stats(text: str) -> Dict:
    """
    Count words/characters and detect language type
    """
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Detect CJK (Chinese, Japanese, Korean) characters
    cjk_pattern = re.compile(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]')
    cjk_chars = cjk_pattern.findall(text)
    cjk_count = len(cjk_chars)
    
    # Count words (for Latin-based languages)
    words = text.split()
    word_count = len(words)
    
    # Determine language group and count type
    if cjk_count > word_count * 0.3:  # If 30%+ CJK characters
        return {
            'count': cjk_count,
            'type': 'characters',
            'language_group': 'CJK',
            'word_count': word_count,
            'char_count': len(text)
        }
    else:
        return {
            'count': word_count,
            'type': 'words',
            'language_group': 'Latin',
            'word_count': word_count,
            'char_count': len(text)
        }
