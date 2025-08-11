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

def contains_risk(text):
    """
    Check if text contains risk indicators using multiple methods:
    1. Exact phrase matching with spaCy
    2. Fuzzy matching for misspellings
    3. Lemmatization for word variations
    """
    if not text:
        return False
    
    text_lower = text.lower()
    doc = nlp(text_lower)
    
    # Method 1: Check exact phrase matches
    matches = matcher(doc)
    if len(matches) > 0:
        return True
    
    # Method 2: Fuzzy matching for common misspellings
    # Check critical phrases with fuzzy matching (threshold 80% for longer, 75% for short)
    critical_phrases = ['suicide', 'kill myself', 'end my life', 'self harm', 
                        'hurt myself', 'cutting', 'overdose', 'want to die',
                        'wanna die', 'slit wrists', 'slit my wrists']
    
    for phrase in critical_phrases:
        threshold = 75 if len(phrase) < 10 else 80
        if fuzz.partial_ratio(phrase, text_lower) > threshold:
            return True
    
    # Method 3: Check individual tokens for critical words
    critical_tokens = {'suicide', 'suicidal', 'kill', 'die', 'dead', 'death',
                      'harm', 'hurt', 'cut', 'cutting', 'overdose', 'pills',
                      'jump', 'hang', 'drown', 'blade', 'rope', 'gun', 'slit',
                      'wrists', 'wanna', 'gonna'}
    
    doc_tokens = {token.lemma_.lower() for token in doc}
    if doc_tokens.intersection(critical_tokens):
        # If critical token found, check context
        for token in doc:
            if token.lemma_.lower() in critical_tokens:
                # Check if it's in a concerning context
                context = text_lower[max(0, token.idx-20):min(len(text_lower), token.idx+30)]
                concerning_context = ['myself', 'my life', 'want to', 'going to', 
                                     'plan to', 'will', "can't", 'no point', 'tired of',
                                     'wanna', 'gonna', "i'll", "my wrists"]
                if any(ctx in context for ctx in concerning_context):
                    return True
                # Special case for short phrases like "wanna die"
                if token.lemma_.lower() in ['die', 'dead'] and 'wanna' in text_lower:
                    return True
    
    return False

def get_crisis_resources():
    """
    Return formatted crisis resources with the crisis message
    """
    resources = risk_data['crisis_resources']
    message = risk_data['crisis_message']
    
    # Format the complete crisis response
    response = f"\n🆘 **{message['header']}**\n\n"
    response += f"{message['body']}\n\n"
    
    for service, info in resources.items():
        response += f"**{service}**: {info['number']}\n"
        response += f"   {info['description']}\n\n"
    
    response += f"\n{message['footer']}\n"
    response += f"\n{message['continue_prompt']}"
    
    return response
