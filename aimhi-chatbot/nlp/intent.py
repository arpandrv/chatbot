import spacy
from rapidfuzz import fuzz
import re

try:
    nlp = spacy.load('en_core_web_sm')
except:
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load('en_core_web_sm')

# Restore the comprehensive intent patterns - this was valuable linguistic knowledge
INTENT_PATTERNS = {
    'support_people': {
        'keywords': ['family', 'friends', 'mom', 'dad', 'brother', 'sister', 'cousin', 
                    'aunt', 'uncle', 'grandma', 'grandpa', 'teacher', 'elder', 'mentor',
                    'counsellor', 'therapist', 'doctor', 'nurse', 'community', 'mob',
                    'people', 'support', 'help', 'care', 'love', 'there for me', 'nice',
                    'kind', 'counselor', 'psychologist', 'social worker'],
        'patterns': [
            r'\b(my|have|got)\s+(family|friends|people)',
            r'\b(mom|dad|mum|mother|father|parents)',
            r'\b(brother|sister|sibling|cousin)',
            r'\b(no one|nobody|alone|by myself)',
            r'\b(elder|aunty|uncle|nan|pop)',
            r'\b(teacher|counselor|therapist)\s+(is|was|seems)',
            r'\btalk to (my|a|the)\s+(counselor|therapist|teacher)',
            r'\b(nice|kind|caring|supportive)\s+(teacher|person|family)',
            r'\b(have|got)\s+(good|great|close|supportive)\s+(friends|family)',
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

def classify_intent(text, current_step=None):
    """
    Hybrid intent classification: comprehensive patterns + context awareness
    Args:
        text: User input text
        current_step: Current FSM step for context-aware classification
    Returns: (intent_name, confidence_score)
    """
    if not text:
        return 'unclear', 0.0
    
    text_lower = text.lower().strip()
    doc = nlp(text_lower)
    
    intent_scores = {}
    
    # LAYER 1: Strong contextual patterns that should override other signals
    strong_patterns = {
        'strengths': [
            r"\b(i'm|i am|im)\s+(good at|great at|skilled|talented)",
            r"\bproud of\b",
            r"\bmy strength\b",
            r"\bi can\b",
            r"\bi love (doing|playing|making)",
        ],
        'support_people': [
            r"\b(my|have|got)\s+(family|friends|people)\s+(support|help|care|love|there for)",
            r"\bpeople who support\b",
            r"\bpeople in my life\b",
        ],
        'worries': [
            r"\bworr(y|ied|ying) about\b",
            r"\bstressed about\b",
            r"\bon my mind\b",
            r"\bkeeps me up\b",
        ],
        'goals': [
            r"\bwant to (be|become|get|achieve|finish|complete)\b",
            r"\bmy goal\b",
            r"\bplan to\b",
            r"\bhope to\b",
        ]
    }
    
    # Apply strong patterns first
    for intent_name, patterns in strong_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                intent_scores[intent_name] = intent_scores.get(intent_name, 0) + 0.8
    
    # Special handling for "don't know" phrases - should be unclear, not negation
    dont_know_patterns = [r"don't know", r"dont know", r"not sure", r"unsure"]
    if any(re.search(pattern, text_lower) for pattern in dont_know_patterns):
        intent_scores['unclear'] = intent_scores.get('unclear', 0) + 0.9  # High score for unclear
        # Reduce negation score if it was triggered by "don't"
        if 'negation' in intent_scores:
            intent_scores['negation'] *= 0.3
    
    # LAYER 2: Check for negation patterns that invalidate strength/support claims
    negation_patterns = [
        r"\b(not|n't|no|never|cannot|can't|cant|don't|dont|doesn't|doesnt|didn't|didnt|won't|wont|wouldn't|wouldnt|couldn't|couldnt)\b",
        r"\b(nothing|nobody|nowhere|neither|none)\b"
    ]
    has_negation = any(re.search(pattern, text_lower) for pattern in negation_patterns)
    
    # LAYER 3: Regular scoring for all intents using original comprehensive patterns
    for intent_name, intent_data in INTENT_PATTERNS.items():
        base_score = intent_scores.get(intent_name, 0)
        
        # Check keyword matches
        keywords = intent_data['keywords']
        keyword_score = 0
        for keyword in keywords:
            if keyword in text_lower:
                keyword_score += 0.2
            # Fuzzy matching for typos (but more conservative)
            elif fuzz.partial_ratio(keyword, text_lower) > 85:  # Raised threshold from 80
                keyword_score += 0.1  # Reduced from 0.15
        
        # Check regex patterns
        patterns = intent_data['patterns']
        pattern_score = 0
        for pattern in patterns:
            if re.search(pattern, text_lower):
                pattern_score += 0.3
        
        # Boost score for exact matches (short responses)
        exact_match_score = 0
        if len(text_lower.split()) <= 3:
            for keyword in keywords:
                if text_lower == keyword:
                    exact_match_score += 0.5
        
        total_score = base_score + keyword_score + pattern_score + exact_match_score
        intent_scores[intent_name] = min(total_score, 1.0)
    
    # LAYER 4: Context-aware boosting (Solutions 2 & 3)
    if current_step:
        # Context-aware disambiguation for ambiguous words
        ambiguous_words = ['help', 'helping', 'support', 'supporting', 'care', 'caring', 
                          'there for', 'assist', 'guide']
        has_ambiguous = any(word in text_lower for word in ambiguous_words)
        
        if current_step == 'strengths' and has_ambiguous:
            # At strengths step, strongly boost strengths interpretation
            if 'strengths' not in intent_scores:
                intent_scores['strengths'] = 0.0
            intent_scores['strengths'] += 0.7  # Increased from 0.4
            if 'support_people' in intent_scores:
                intent_scores['support_people'] *= 0.5  # More aggressive reduction
                
        elif current_step == 'support_people' and has_ambiguous:
            # At support_people step, boost support interpretation  
            if 'support_people' not in intent_scores:
                intent_scores['support_people'] = 0.0
            intent_scores['support_people'] += 0.7  # Increased from 0.4
            if 'strengths' in intent_scores:
                intent_scores['strengths'] *= 0.5  # More aggressive reduction
        
        # Short response heuristics (Solution 3)
        word_count = len(text_lower.split())
        if word_count <= 4:
            if current_step == 'strengths':
                activity_words = ['helping', 'teaching', 'cooking', 'playing', 'singing', 
                                 'dancing', 'drawing', 'writing', 'gaming', 'listening',
                                 'caring', 'supporting', 'making', 'creating', 'building']
                if any(activity in text_lower for activity in activity_words):
                    if 'strengths' not in intent_scores:
                        intent_scores['strengths'] = 0.0
                    intent_scores['strengths'] += 0.3
                    if 'support_people' in intent_scores:
                        intent_scores['support_people'] *= 0.6
                        
            elif current_step == 'support_people':
                support_words = ['mom', 'mum', 'dad', 'mother', 'father', 'parents', 'family',
                                'friends', 'friend', 'teacher', 'counselor', 'counsellor', 
                                'therapist', 'elder', 'aunty', 'uncle', 'cousin', 'sister',
                                'brother', 'nan', 'pop', 'grandma', 'grandpa']
                if any(person in text_lower for person in support_words):
                    if 'support_people' not in intent_scores:
                        intent_scores['support_people'] = 0.0
                    intent_scores['support_people'] += 0.3
                    if 'strengths' in intent_scores:
                        intent_scores['strengths'] *= 0.6
    
    # LAYER 5: Handle negation (overrides context in some cases)
    if has_negation:
        strength_words = ['cook', 'play', 'help', 'teach', 'good', 'skill', 'talent']
        support_words = ['friends', 'family', 'support', 'help', 'care']
        
        has_strength_context = any(word in text_lower for word in strength_words)
        has_support_context = any(word in text_lower for word in support_words)
        
        if has_strength_context or has_support_context:
            intent_scores['negation'] = intent_scores.get('negation', 0) + 0.8
            # Reduce but don't eliminate other scores
            if 'strengths' in intent_scores:
                intent_scores['strengths'] *= 0.3
            if 'support_people' in intent_scores:
                intent_scores['support_people'] *= 0.3
    
    # LAYER 6: Final scoring and selection
    if intent_scores:
        # Context-aware tie breaking
        if ('strengths' in intent_scores and 'support_people' in intent_scores and
            'helping' in text_lower and 'good at' in text_lower):
            intent_scores['strengths'] += 0.2
            intent_scores['support_people'] -= 0.2
        
        # Get the highest scoring intent
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