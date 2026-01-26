import re
from collections import Counter
from typing import Dict, List
import string

def is_cjk_character(char: str) -> bool:
    """Check if a character is CJK (Chinese, Japanese, Korean)"""
    cjk_ranges = [
        (0x4E00, 0x9FFF),    # CJK Unified Ideographs
        (0x3400, 0x4DBF),    # CJK Unified Ideographs Extension A
        (0x20000, 0x2A6DF),  # CJK Unified Ideographs Extension B
        (0x2A700, 0x2B73F),  # CJK Unified Ideographs Extension C
        (0x2B740, 0x2B81F),  # CJK Unified Ideographs Extension D
        (0x3040, 0x309F),    # Hiragana
        (0x30A0, 0x30FF),    # Katakana
        (0xAC00, 0xD7AF),    # Hangul Syllables
    ]
    code = ord(char)
    return any(start <= code <= end for start, end in cjk_ranges)

def detect_language_type(text: str) -> str:
    """Detect if text is primarily CJK or Latin-based"""
    if not text:
        return "unknown"
    
    # Sample first 1000 characters for detection
    sample = text[:1000]
    cjk_count = sum(1 for char in sample if is_cjk_character(char))
    
    # If more than 30% CJK characters, treat as CJK
    if cjk_count / len(sample) > 0.3:
        return "cjk"
    return "latin"

def analyze_vocabulary(text: str) -> Dict:
    """
    Analyze text for vocabulary statistics including:
    - Total words/characters (based on language)
    - Unique words/characters
    - Most repeated words/characters
    - Vocabulary richness
    
    Supports both Latin-based (word-separated) and CJK languages
    """
    language_type = detect_language_type(text)
    
    if language_type == "cjk":
        return analyze_cjk_vocabulary(text)
    else:
        return analyze_latin_vocabulary(text)

def analyze_cjk_vocabulary(text: str) -> Dict:
    """Analyze CJK text (character-based)"""
    # Extract only CJK characters
    cjk_chars = [char for char in text if is_cjk_character(char)]
    
    # Count all characters
    total_chars = len(cjk_chars)
    
    # Get unique characters
    unique_chars = set(cjk_chars)
    unique_count = len(unique_chars)
    
    # Count character frequencies
    char_freq = Counter(cjk_chars)
    
    # Get most common characters
    most_common = char_freq.most_common(50)
    
    # Calculate repetition metrics
    repetitions = {char: count for char, count in char_freq.items() if count > 1}
    repetition_count = len(repetitions)
    
    # Vocabulary richness (Character Diversity Ratio)
    vocabulary_richness = (unique_count / total_chars * 100) if total_chars > 0 else 0
    
    # Average character repetition
    total_repetitions = sum(count - 1 for count in char_freq.values())
    avg_repetition = total_repetitions / unique_count if unique_count > 0 else 0
    
    return {
        'language_type': 'CJK',
        'unit': 'characters',
        'total_words': total_chars,  # Keep same key for consistency
        'unique_words': unique_count,
        'repeated_words': repetition_count,
        'vocabulary_richness': round(vocabulary_richness, 2),
        'avg_repetition': round(avg_repetition, 2),
        'most_common_words': most_common[:20],
        'total_repetitions': total_repetitions,
        'word_frequencies': dict(char_freq.most_common(100))
    }

def analyze_latin_vocabulary(text: str) -> Dict:
    """Analyze Latin-based text (word-separated)"""
    # Clean and tokenize text
    text_lower = text.lower()
    # Remove punctuation
    translator = str.maketrans(string.punctuation, ' ' * len(string.punctuation))
    text_clean = text_lower.translate(translator)
    
    # Split into words
    words = text_clean.split()
    
    # Filter out very short words (likely not meaningful)
    words = [w for w in words if len(w) > 2]
    
    # Common stop words to optionally filter
    stop_words = {
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her',
        'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how',
        'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 'did',
        'car', 'let', 'put', 'say', 'she', 'too', 'use', 'with', 'this', 'that',
        'have', 'from', 'they', 'been', 'were', 'what', 'your', 'more', 'will',
        'there', 'their', 'which', 'about', 'other', 'would', 'these', 'could',
        'than', 'then', 'them', 'some', 'into', 'only', 'over', 'also', 'back',
        'after', 'being', 'where', 'when', 'much', 'very', 'such', 'because',
        'through', 'between', 'under', 'during', 'before', 'should', 'those'
    }
    
    # Count all words
    total_words = len(words)
    
    # Get unique words
    unique_words = set(words)
    unique_count = len(unique_words)
    
    # Count word frequencies
    word_freq = Counter(words)
    
    # Get most common words (excluding stop words for meaningful insights)
    content_words = [w for w in words if w not in stop_words]
    content_word_freq = Counter(content_words)
    most_common = content_word_freq.most_common(50)
    
    # Calculate repetition metrics
    repetitions = {word: count for word, count in word_freq.items() if count > 1}
    repetition_count = len(repetitions)
    
    # Vocabulary richness (Type-Token Ratio)
    vocabulary_richness = (unique_count / total_words * 100) if total_words > 0 else 0
    
    # Average word repetition
    total_repetitions = sum(count - 1 for count in word_freq.values())
    avg_repetition = total_repetitions / unique_count if unique_count > 0 else 0
    
    return {
        'language_type': 'Latin',
        'unit': 'words',
        'total_words': total_words,
        'unique_words': unique_count,
        'repeated_words': repetition_count,
        'vocabulary_richness': round(vocabulary_richness, 2),
        'avg_repetition': round(avg_repetition, 2),
        'most_common_words': most_common[:20],
        'total_repetitions': total_repetitions,
        'word_frequencies': dict(word_freq.most_common(100))
    }

def get_repetition_details(text: str, min_repetitions: int = 3) -> List[Dict]:
    """
    Get detailed list of words/characters repeated more than min_repetitions times
    Handles both Latin and CJK languages
    """
    language_type = detect_language_type(text)
    
    if language_type == "cjk":
        # Character-based analysis
        cjk_chars = [char for char in text if is_cjk_character(char)]
        char_freq = Counter(cjk_chars)
        
        repeated = [
            {'word': char, 'count': count, 'repetitions': count - 1}
            for char, count in char_freq.most_common()
            if count >= min_repetitions
        ]
        return repeated
    else:
        # Word-based analysis
        text_lower = text.lower()
        translator = str.maketrans(string.punctuation, ' ' * len(string.punctuation))
        text_clean = text_lower.translate(translator)
        words = [w for w in text_clean.split() if len(w) > 2]
        
        word_freq = Counter(words)
        
        repeated = [
            {'word': word, 'count': count, 'repetitions': count - 1}
            for word, count in word_freq.most_common()
            if count >= min_repetitions
        ]
        return repeated
