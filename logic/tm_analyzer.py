import re
from typing import Dict, List, Tuple
from collections import Counter
import difflib

def segment_text(text: str) -> List[str]:
    """
    Segment text into sentences/segments similar to CAT tools
    """
    # Split by common sentence terminators
    # This mimics how CAT tools segment content
    segments = re.split(r'(?<=[.!?。！？])\s+|\n+', text)
    
    # Clean and filter segments
    segments = [s.strip() for s in segments if s.strip()]
    
    return segments

def normalize_segment(segment: str) -> str:
    """
    Normalize segment for comparison (like CAT tools do)
    - Remove extra whitespace
    - Normalize punctuation spacing
    - Keep case and punctuation for accurate matching
    """
    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', segment)
    normalized = normalized.strip()
    
    return normalized

def calculate_similarity(seg1: str, seg2: str) -> float:
    """
    Calculate similarity between two segments (0-100%)
    Similar to fuzzy matching in CAT tools
    """
    return difflib.SequenceMatcher(None, seg1, seg2).ratio() * 100

def count_words_in_segment(segment: str) -> int:
    """
    Count words in a segment (for word count)
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

def analyze_repetitions(text: str, fuzzy_threshold: int = 75) -> Dict:
    """
    Analyze text repetitions like Memsource/memoQ
    
    Returns:
    - Total segments
    - Total words
    - 100% match repetitions (exact duplicates)
    - Fuzzy match repetitions (75-99% similar)
    - New segments (unique content)
    - Word count breakdown
    """
    # Segment the text
    segments = segment_text(text)
    
    if not segments:
        return {
            'total_segments': 0,
            'total_words': 0,
            'repetitions_100': 0,
            'repetitions_fuzzy': 0,
            'new_segments': 0,
            'words_100': 0,
            'words_fuzzy': 0,
            'words_new': 0,
            'repetition_details': [],
            'segment_breakdown': []
        }
    
    # Normalize segments
    normalized_segments = [normalize_segment(s) for s in segments]
    
    # Count occurrences of each segment (100% matches)
    segment_counts = Counter(normalized_segments)
    
    # Calculate total words
    total_words = sum(count_words_in_segment(s) for s in normalized_segments)
    
    # Categorize segments
    segment_analysis = []
    processed = set()
    
    for i, segment in enumerate(normalized_segments):
        if segment in processed:
            continue
        
        word_count = count_words_in_segment(segment)
        occurrence_count = segment_counts[segment]
        
        if occurrence_count > 1:
            # 100% match (exact repetition)
            segment_analysis.append({
                'segment': segment[:100] + '...' if len(segment) > 100 else segment,
                'full_segment': segment,
                'type': '100%',
                'occurrences': occurrence_count,
                'repetitions': occurrence_count - 1,
                'words_per_segment': word_count,
                'total_words': word_count * occurrence_count,
                'savings': word_count * (occurrence_count - 1)  # Words saved by repetition
            })
            processed.add(segment)
        else:
            # Check for fuzzy matches
            fuzzy_matches = []
            for j, other_segment in enumerate(normalized_segments):
                if i != j and other_segment not in processed:
                    similarity = calculate_similarity(segment, other_segment)
                    if fuzzy_threshold <= similarity < 100:
                        fuzzy_matches.append((other_segment, similarity))
            
            if fuzzy_matches:
                # Fuzzy match found
                total_fuzzy_words = word_count * (1 + len(fuzzy_matches))
                segment_analysis.append({
                    'segment': segment[:100] + '...' if len(segment) > 100 else segment,
                    'full_segment': segment,
                    'type': f'Fuzzy ({fuzzy_threshold}-99%)',
                    'occurrences': 1 + len(fuzzy_matches),
                    'repetitions': len(fuzzy_matches),
                    'words_per_segment': word_count,
                    'total_words': total_fuzzy_words,
                    'savings': int(total_fuzzy_words * 0.3)  # Approximate 30% savings for fuzzy
                })
                processed.add(segment)
                for fm, _ in fuzzy_matches:
                    processed.add(fm)
            else:
                # New segment (no matches)
                segment_analysis.append({
                    'segment': segment[:100] + '...' if len(segment) > 100 else segment,
                    'full_segment': segment,
                    'type': 'New',
                    'occurrences': 1,
                    'repetitions': 0,
                    'words_per_segment': word_count,
                    'total_words': word_count,
                    'savings': 0
                })
                processed.add(segment)
    
    # Calculate totals by category
    segments_100 = sum(1 for s in segment_analysis if s['type'] == '100%')
    segments_fuzzy = sum(1 for s in segment_analysis if 'Fuzzy' in s['type'])
    segments_new = sum(1 for s in segment_analysis if s['type'] == 'New')
    
    words_100 = sum(s['total_words'] for s in segment_analysis if s['type'] == '100%')
    words_fuzzy = sum(s['total_words'] for s in segment_analysis if 'Fuzzy' in s['type'])
    words_new = sum(s['total_words'] for s in segment_analysis if s['type'] == 'New')
    
    # Calculate repetition counts (how many times segments are repeated)
    repetitions_100_count = sum(s['repetitions'] for s in segment_analysis if s['type'] == '100%')
    repetitions_fuzzy_count = sum(s['repetitions'] for s in segment_analysis if 'Fuzzy' in s['type'])
    
    # Calculate total savings
    total_savings = sum(s['savings'] for s in segment_analysis)
    
    # Sort by savings (most valuable repetitions first)
    segment_analysis.sort(key=lambda x: x['savings'], reverse=True)
    
    return {
        'total_segments': len(segments),
        'total_words': total_words,
        'unique_segments': len(segment_counts),
        
        # Segment counts
        'segments_100': segments_100,
        'segments_fuzzy': segments_fuzzy,
        'segments_new': segments_new,
        
        # Word counts
        'words_100': words_100,
        'words_fuzzy': words_fuzzy,
        'words_new': words_new,
        
        # Repetition counts
        'repetitions_100_count': repetitions_100_count,
        'repetitions_fuzzy_count': repetitions_fuzzy_count,
        
        # Savings
        'total_savings': total_savings,
        'savings_percentage': (total_savings / total_words * 100) if total_words > 0 else 0,
        
        # Detailed breakdown
        'repetition_details': segment_analysis[:100],  # Top 100 most repeated
        
        # Summary for display
        'summary': {
            '100% Match': {'segments': segments_100, 'words': words_100},
            'Fuzzy Match': {'segments': segments_fuzzy, 'words': words_fuzzy},
            'New': {'segments': segments_new, 'words': words_new}
        }
    }

def get_repetition_summary(results: Dict) -> str:
    """
    Generate a summary string similar to CAT tool analysis
    """
    summary = f"""
Translation Memory Analysis Summary:
=====================================
Total Segments: {results['total_segments']:,}
Total Words: {results['total_words']:,}
Unique Segments: {results['unique_segments']:,}

Breakdown:
----------
100% Match: {results['segments_100']} segments ({results['words_100']:,} words)
Fuzzy Match: {results['segments_fuzzy']} segments ({results['words_fuzzy']:,} words)
New: {results['segments_new']} segments ({results['words_new']:,} words)

Translation Savings:
-------------------
Words saved by repetitions: {results['total_savings']:,}
Savings percentage: {results['savings_percentage']:.2f}%
"""
    return summary
