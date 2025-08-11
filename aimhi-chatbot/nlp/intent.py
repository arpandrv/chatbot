import spacy
from rapidfuzz import fuzz
import re

try:
    nlp = spacy.load('en_core_web_sm')
except:
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load('en_core_web_sm')

# Intent patterns for each conversation step
INTENT_PATTERNS = {
    'support_people': {
        'keywords': ['family', 'friends', 'mom', 'dad', 'brother', 'sister', 'cousin', 
                    'aunt', 'uncle', 'grandma', 'grandpa', 'teacher', 'elder', 'mentor',
                    'counsellor', 'therapist', 'doctor', 'nurse', 'community', 'mob',
                    'people', 'support', 'help', 'care', 'love', 'there for me'],
        'patterns': [
            r'\b(my|have|got)\s+(family|friends|people)',
            r'\b(mom|dad|mum|mother|father|parents)',
            r'\b(brother|sister|sibling|cousin)',
            r'\b(no one|nobody|alone|by myself)',
            r'\b(elder|aunty|uncle|nan|pop)',
        ]
    },
    'strengths': {
        'keywords': ['good at', 'proud', 'strength', 'skill', 'talent', 'ability',
                    'smart', 'creative', 'funny', 'kind', 'caring', 'strong', 'brave',
                    'sport', 'music', 'art', 'cooking', 'gaming', 'reading', 'writing',
                    'helping', 'listening', 'learning', 'working'],
        'patterns': [
            r"\b(i'm|i am|im)\s+(good at|great at|skilled)",
            r"\b(proud of|pride in)",
            r"\b(my strength|my talent|my skill)",
            r"\b(nothing|not good|useless|worthless)",
            r"\b(sport|football|basketball|swimming)",
            r"\b(music|singing|dancing|art|drawing)",
        ]
    },
    'worries': {
        'keywords': ['worry', 'worried', 'stress', 'stressed', 'anxious', 'anxiety',
                    'scared', 'fear', 'afraid', 'concern', 'problem', 'issue',
                    'school', 'work', 'money', 'relationship', 'health', 'future',
                    'family problems', 'bullying', 'lonely', 'sad', 'depressed'],
        'patterns': [
            r'\b(worry|worried|worrying) about',
            r'\b(stressed?|anxious|anxiety)',
            r'\b(scared|afraid|fear)',
            r'\b(problem|issue|trouble)',
            r'\b(school|homework|exams|grades)',
            r'\b(money|bills|rent|job)',
            r'\b(relationship|boyfriend|girlfriend|friends)',
        ]
    },
    'goals': {
        'keywords': ['goal', 'want', 'hope', 'plan', 'future', 'dream', 'achieve',
                    'accomplish', 'work towards', 'aim', 'objective', 'target',
                    'finish school', 'get job', 'learn', 'improve', 'better',
                    'healthy', 'happy', 'success', 'graduate'],
        'patterns': [
            r'\b(want to|hope to|plan to|going to)',
            r'\b(my goal|my dream|my aim)',
            r'\b(achieve|accomplish|succeed)',
            r'\b(finish|complete|graduate)',
            r'\b(get a job|find work|career)',
            r'\b(learn|study|improve|better)',
        ]
    },
    'greeting': {
        'keywords': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 
                    'good evening', "g'day", 'howdy', 'greetings'],
        'patterns': [
            r'^(hello|hi|hey)\b',
            r'^(good\s+(morning|afternoon|evening))',
            r"^(g'day|howdy|greetings)",
        ]
    },
    'affirmation': {
        'keywords': ['yes', 'yeah', 'yep', 'sure', 'okay', 'ok', 'alright', 
                    'definitely', 'absolutely', 'agree', 'correct', 'right'],
        'patterns': [
            r'^(yes|yeah|yep|yup|ya)\b',
            r'^(sure|okay|ok|alright)\b',
            r'^(definitely|absolutely|certainly)\b',
        ]
    },
    'negation': {
        'keywords': ['no', 'nope', 'not', "don't", "doesn't", "won't", "can't",
                    'never', 'nothing', 'none', 'nobody'],
        'patterns': [
            r'^(no|nope|nah)\b',
            r"\b(don't|doesn't|won't|can't|cannot)\b",
            r'\b(never|nothing|none|nobody)\b',
        ]
    },
    'question': {
        'keywords': ['what', 'why', 'how', 'when', 'where', 'who', 'which',
                    'can you', 'could you', 'would you', 'will you'],
        'patterns': [
            r'^(what|why|how|when|where|who|which)\b',
            r'\?$',
            r'\b(can you|could you|would you|will you)',
        ]
    },
    'unclear': {
        'keywords': ["don't know", "not sure", "maybe", "perhaps", "confused",
                    "don't understand", "what do you mean", "huh", "umm"],
        'patterns': [
            r"(don't know|not sure|unsure)",
            r'^(maybe|perhaps|possibly)\b',
            r"(confused|don't understand)",
            r'^(um+|uh+|hmm+|err+)',
        ]
    }
}

def classify_intent(text):
    """
    Classify the intent of user input with confidence score.
    Returns: (intent_name, confidence_score)
    """
    if not text:
        return 'unclear', 0.0
    
    text_lower = text.lower().strip()
    doc = nlp(text_lower)
    
    intent_scores = {}
    
    for intent_name, intent_data in INTENT_PATTERNS.items():
        score = 0.0
        
        # Check keyword matches
        keywords = intent_data['keywords']
        for keyword in keywords:
            if keyword in text_lower:
                score += 0.3
            # Fuzzy matching for typos
            elif fuzz.partial_ratio(keyword, text_lower) > 80:
                score += 0.2
        
        # Check regex patterns
        patterns = intent_data['patterns']
        for pattern in patterns:
            if re.search(pattern, text_lower):
                score += 0.4
        
        # Boost score for exact matches
        if len(text_lower.split()) <= 3:  # Short responses
            for keyword in keywords:
                if text_lower == keyword:
                    score += 0.5
        
        intent_scores[intent_name] = min(score, 1.0)  # Cap at 1.0
    
    # Get the highest scoring intent
    if intent_scores:
        best_intent = max(intent_scores.items(), key=lambda x: x[1])
        intent_name, confidence = best_intent
        
        # If confidence is too low, mark as unclear
        if confidence < 0.2:
            return 'unclear', confidence
        
        return intent_name, confidence
    
    return 'unclear', 0.0

def get_intent_for_step(current_step):
    """
    Get the expected intent for the current FSM step
    """
    step_to_intent = {
        'welcome': 'greeting',
        'support_people': 'support_people',
        'strengths': 'strengths', 
        'worries': 'worries',
        'goals': 'goals',
        'summary': 'affirmation'
    }
    return step_to_intent.get(current_step, 'unclear')
