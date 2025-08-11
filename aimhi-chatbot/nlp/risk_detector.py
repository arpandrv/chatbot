import spacy
from spacy.matcher import PhraseMatcher
import json

nlp = spacy.load('en_core_web_md')

with open('config/risk_phrases.json') as f:
    risk_data = json.load(f)

risk_phrases = []
for item in risk_data['risk_phrases']:
    risk_phrases.append(item['phrase'])
    risk_phrases.extend(item['variants'])

risk_phrase_patterns = [nlp(text) for text in risk_phrases]

matcher = PhraseMatcher(nlp.vocab)
matcher.add('RiskPhrases', None, *risk_phrase_patterns)

def contains_risk(text):
    doc = nlp(text)
    matches = matcher(doc)
    return len(matches) > 0

def get_crisis_resources():
    return risk_data['crisis_resources']
