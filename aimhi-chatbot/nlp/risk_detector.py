import spacy
from spacy.matcher import PhraseMatcher
from rapidfuzz import fuzz
import json
import os

# Load smaller model for better performance
try:
    nlp = spacy.load('en_core_web_sm')
except:
    # Fallback if model not installed
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load('en_core_web_sm')

# Load risk phrases configuration
script_dir = os.path.dirname(__file__)
config_path = os.path.join(script_dir, '..', 'config', 'risk_phrases.json')

with open(config_path) as f:
    risk_data = json.load(f)

# Build comprehensive risk phrase list
risk_phrases = []
for item in risk_data['risk_phrases']:
    risk_phrases.append(item['phrase'].lower())
    risk_phrases.extend([v.lower() for v in item['variants']])

# Create spaCy patterns for exact matching
risk_phrase_patterns = [nlp.make_doc(text) for text in risk_phrases]

# Initialize PhraseMatcher for exact matching
matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
matcher.add('RiskPhrases', risk_phrase_patterns)

# Load additional detection data from JSON
fuzzy_phrases = risk_data['fuzzy_phrases']
critical_tokens = set(risk_data['critical_tokens'])
positive_indicators = risk_data['context_validation']['positive_indicators']
concerning_context = risk_data['context_validation']['concerning_context']
false_positive_phrases = risk_data['false_positives']['innocent_phrases']
false_positive_patterns = risk_data['false_positives']['context_patterns']

def contains_risk(text):
    """
    Check if text contains risk indicators using three methods:
    1. Exact phrase matching 
    2. Fuzzy matching for misspellings
    3. Critical word detection with context validation
    """
    if not text:
        return False
    
    text_lower = text.lower()
    
    # Early exit: Check for innocent phrases first
    if any(phrase in text_lower for phrase in false_positive_phrases):
        return False
    
    doc = nlp(text_lower)
    
    # Method 1: Exact phrase matching
    if _check_exact_phrases(doc):
        return True
    
    # Method 2: Fuzzy matching for misspellings  
    if _check_fuzzy_matches(text_lower):
        return True
        
    # Method 3: Critical word detection
    if _check_critical_words(doc, text_lower):
        return True
    
    return False

def _check_exact_phrases(doc):
    """Check for exact risk phrase matches with context validation"""
    matches = matcher(doc)
    for match_id, start, end in matches:
        matched_phrase = doc[start:end].text.lower()
        
        # Skip "help" phrases in positive context
        if any(word in matched_phrase for word in ['help', 'helping']):
            context = _get_word_context(doc, start, end, 10)
            if any(positive in context for positive in positive_indicators):
                continue
        
        return True  # Found genuine risk phrase
    return False

def _check_fuzzy_matches(text_lower):
    """Check for fuzzy matches of critical phrases"""
    # Special handling for wanna/gonna phrases - need exact dangerous combinations
    if 'wanna' in text_lower or 'gonna' in text_lower:
        # Only check for exact dangerous phrases with wanna/gonna
        dangerous_combos = ['wanna die', 'wanna kill', 'wanna hurt', 'wanna cut', 
                           'gonna die', 'gonna kill', 'gonna hurt', 'gonna cut',
                           'wanna end', 'gonna end']
        for combo in dangerous_combos:
            if combo in text_lower:
                return True
        # Don't do fuzzy matching on wanna/gonna phrases - too many false positives
        return False
    
    # For non-wanna/gonna phrases, use fuzzy matching but with higher threshold
    for phrase in fuzzy_phrases:
        # Skip wanna/gonna phrases - handled above
        if 'wanna' in phrase or 'gonna' in phrase:
            continue
            
        threshold = 85 if len(phrase) < 10 else 90  # Increased thresholds
        if fuzz.partial_ratio(phrase, text_lower) > threshold:
            # Skip if it's about helping others (specific to "want to die")
            if phrase == 'want to die' and any(word in text_lower for word in ['help', 'support', 'people']):
                continue
            return True
    return False

def _check_critical_words(doc, text_lower):
    """Check for critical words with context validation"""
    # Special handling for "wanna" and "gonna" - they need dangerous words nearby
    if 'wanna' in text_lower or 'gonna' in text_lower:
        # Only flag if followed by actually dangerous words
        dangerous_after_wanna = ['die', 'dead', 'kill', 'hurt', 'harm', 'cut', 'end', 'suicide', 'overdose', 'jump', 'hang', 'drown']
        for danger_word in dangerous_after_wanna:
            if danger_word in text_lower:
                # Check proximity - within 3 words
                words = text_lower.split()
                for i, word in enumerate(words):
                    if 'wanna' in word or 'gonna' in word:
                        # Check next 3 words for danger
                        next_words = ' '.join(words[i:i+4])
                        if danger_word in next_words:
                            return True
    
    for token in doc:
        token_lemma = token.lemma_.lower()
        if token_lemma not in critical_tokens:
            continue
            
        # Skip "wanna" and "gonna" - handled above
        if token_lemma in ['wanna', 'gonna']:
            continue
            
        # Check if token is in a safe context (false positive check)
        if _is_token_safe(token_lemma, text_lower):
            continue
            
        # Check if token is in concerning context
        context = _get_char_context(text_lower, token.idx, 20)
        if any(ctx in context for ctx in concerning_context):
            # Skip if it's just "wanna" or "gonna" in context without danger words
            if not any(danger in context for danger in ['die', 'dead', 'kill', 'hurt', 'harm', 'cut', 'end']):
                continue
            return True
    
    return False

def _is_token_safe(token_lemma, text_lower):
    """Check if a critical token is in a safe context (false positive)"""
    for pattern in false_positive_patterns:
        if pattern['token'] == token_lemma:
            if any(safe_ctx in text_lower for safe_ctx in pattern['safe_context']):
                return True
    return False

def _get_word_context(doc, start, end, word_count):
    """Get surrounding word context from spaCy doc"""
    context_start = max(0, start - word_count)
    context_end = min(len(doc), end + word_count)
    return doc[context_start:context_end].text.lower()

def _get_char_context(text, char_idx, char_count):
    """Get surrounding character context from text"""
    context_start = max(0, char_idx - char_count)
    context_end = min(len(text), char_idx + char_count)
    return text[context_start:context_end]

def get_crisis_resources():
    """
    Return formatted crisis resources with the crisis message
    """
    resources = risk_data['crisis_resources']
    message = risk_data['crisis_message']
    
    # Format the complete crisis response
    response = f"\n **{message['header']}**\n\n"
    response += f"{message['body']}\n\n"
    
    for service, info in resources.items():
        response += f"**{service}**: {info['number']}\n"
        response += f"   {info['description']}\n\n"
    
    response += f"\n{message['footer']}\n"
    response += f"\n{message['continue_prompt']}"
    
    return response
