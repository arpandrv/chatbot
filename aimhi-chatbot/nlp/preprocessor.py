import spacy

nlp = spacy.load('en_core_web_md')

def normalize_text(text):
    text = text.lower().strip()
    doc = nlp(text)
    lemmatized_text = " ".join([token.lemma_ for token in doc])
    return lemmatized_text
