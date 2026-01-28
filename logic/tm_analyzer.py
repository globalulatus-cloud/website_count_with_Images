import re
from typing import Dict, List
from collections import Counter

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

def segment_text(text: str) -> List[str]:
    """
    Segment text into sentences/segments similar to CAT tools
    """
    # Split by common sentence terminators
    segments = re.split(r'(?<=[.!?。！？])\s+|\n+', text)
    
    # Clean and filter segments
    segments = [s.strip() for s in segments if s.strip()]
    
    return segments

def normalize_segment(segment: str) -> str:
    """
    Normalize segment for comparison
    - Remove extra whitespace
    - Keep case and punctuation for accurate matching
    """
    normalized = re.sub(r'\s+', ' ', segment)
    normalized = normalized.strip()
    
    return normalized

def count_words_in_segment(segment: str) -> int:
    """
    Count words/characters in a segment
    Handles both Latin and CJK text
    """
    # Check if CJK
    cjk_pattern = re.compile(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]')
    cjk_chars = cjk_pattern.findall(segment)
    
    if len(cjk_chars) > len(segment) * 0.3:
        # CJK: count characters
        return len(cjk_chars)
    else:
        # Latin: count words
        words = segment.split()
        return len(words)

def analyze_repetitions(text: str) -> Dict:
    """
    Simple TM-style analysis:
    - Total word/character count
    - Repetitions count (segments that appear more than once)
    - Unique count (segments that appear only once)
    
    Automatically handles both Latin (words) and CJK (characters)
    """
    # Detect language type
    language_type = detect_language_type(text)
    unit = "characters" if language_type == "cjk" else "words"
    
    # Segment the text
    segments = segment_text(text)
    
    if not segments:
        return {
            'language_type': language_type.upper(),
            'unit': unit,
            'total_segments': 0,
            'total_words': 0,
            'unique_segments': 0,
            'repeated_segments': 0,
            'repetition_words': 0,
            'unique_words': 0,
            'repetition_details': []
        }
    
    # Normalize segments
    normalized_segments = [normalize_segment(s) for s in segments]
    
    # Count occurrences of each segment
    segment_counts = Counter(normalized_segments)
    
    # Calculate total words/characters
    total_words = sum(count_words_in_segment(s) for s in normalized_segments)
    
    # Separate into unique and repeated
    unique_segments_list = []
    repeated_segments_list = []
    
    for segment, count in segment_counts.items():
        word_count = count_words_in_segment(segment)
        
        if count == 1:
            # Unique (appears only once)
            unique_segments_list.append({
                'segment': segment[:100] + '...' if len(segment) > 100 else segment,
                'full_segment': segment,
                'occurrences': 1,
                'words_per_segment': word_count,
                'total_words': word_count
            })
        else:
            # Repeated (appears 2+ times)
            repeated_segments_list.append({
                'segment': segment[:100] + '...' if len(segment) > 100 else segment,
                'full_segment': segment,
                'occurrences': count,
                'words_per_segment': word_count,
                'total_words': word_count * count,
                'repetition_count': count - 1  # How many times it's repeated
            })
    
    # Sort repeated by most occurrences first
    repeated_segments_list.sort(key=lambda x: x['occurrences'], reverse=True)
    
    # Calculate counts
    unique_segment_count = len(unique_segments_list)
    repeated_segment_count = len(repeated_segments_list)
    
    # Calculate word/character counts
    unique_words = sum(item['total_words'] for item in unique_segments_list)
    repetition_words = sum(item['total_words'] for item in repeated_segments_list)
    
    return {
        'language_type': language_type.upper(),
        'unit': unit,
        'total_segments': len(segments),
        'total_words': total_words,
        'unique_segments': unique_segment_count,
        'repeated_segments': repeated_segment_count,
        'unique_words': unique_words,
        'repetition_words': repetition_words,
        'repetition_details': repeated_segments_list,
        'unique_details': unique_segments_list
    }
