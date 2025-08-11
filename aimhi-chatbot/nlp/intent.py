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
    Classify the intent of user input with confidence score.
    Args:
        text: User input text
        current_step: Current FSM step for context-aware classification
    Returns: (intent_name, confidence_score)
    """
    if not text:
        return 'unclear', 0.0
    
    text_lower = text.lower().strhoip()
    doc = nlp(text_lower)
    
    intent_scores = {}
    
    # Strong contextual patterns that should override other signals
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
    
    # First pass: Check for strong contextual patterns
    for intent_name, patterns in strong_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                # Strong context match - give high confidence and reduce conflicting intents
                intent_scores[intent_name] = intent_scores.get(intent_name, 0) + 0.8
    
    # Check for negation patterns that invalidate strength/support claims
    negation_patterns = [
        r"\b(not|n't|no|never|cannot|can't|cant|don't|dont|doesn't|doesnt|didn't|didnt|won't|wont|wouldn't|wouldnt|couldn't|couldnt)\b",
        r"\b(nothing|nobody|nowhere|neither|none)\b"
    ]
    has_negation = any(re.search(pattern, text_lower) for pattern in negation_patterns)
    
    # Second pass: Regular scoring for all intents
    for intent_name, intent_data in INTENT_PATTERNS.items():
        base_score = intent_scores.get(intent_name, 0)
        
        # Check keyword matches
        keywords = intent_data['keywords']
        keyword_score = 0
        for keyword in keywords:
            if keyword in text_lower:
                keyword_score += 0.2  # Reduced from 0.3 to give less weight
            # Fuzzy matching for typos
            elif fuzz.partial_ratio(keyword, text_lower) > 80:
                keyword_score += 0.15
        
        # Check regex patterns
        patterns = intent_data['patterns']
        pattern_score = 0
        for pattern in patterns:
            if re.search(pattern, text_lower):
                pattern_score += 0.3  # Reduced from 0.4
        
        # Boost score for exact matches
        exact_match_score = 0
        if len(text_lower.split()) <= 3:  # Short responses
            for keyword in keywords:
                if text_lower == keyword:
                    exact_match_score += 0.5
        
        total_score = base_score + keyword_score + pattern_score + exact_match_score
        intent_scores[intent_name] = min(total_score, 1.0)  # Cap at 1.0
    
    # Context-aware tie breaking
    if intent_scores:
        # If we have a strengths response that starts with "I'm good at", prioritize it
        if ('strengths' in intent_scores and 
            intent_scores['strengths'] >= 0.6 and
            re.search(r"\b(i'm|i am|im)\s+(good at|great at)", text_lower)):
            intent_scores['strengths'] += 0.2
        
        # SOLUTION 2: Context-aware classification based on current conversation step
        if current_step:
            # Words that could mean either strength or support depending on context
            ambiguous_words = ['help', 'helping', 'support', 'supporting', 'care', 'caring', 
                              'there for', 'assist', 'guide']
            has_ambiguous = any(word in text_lower for word in ambiguous_words)
            
            if current_step == 'strengths' and has_ambiguous:
                # At strengths step, boost strengths interpretation
                if 'strengths' not in intent_scores:
                    intent_scores['strengths'] = 0.0
                intent_scores['strengths'] += 0.5
                if 'support_people' in intent_scores:
                    intent_scores['support_people'] -= 0.3
                    
            elif current_step == 'support_people' and has_ambiguous:
                # At support_people step, boost support interpretation  
                if 'support_people' not in intent_scores:
                    intent_scores['support_people'] = 0.0
                intent_scores['support_people'] += 0.5
                if 'strengths' in intent_scores:
                    intent_scores['strengths'] -= 0.3
        
        # SOLUTION 3: Short response heuristics (2-4 words) with context awareness
        word_count = len(text_lower.split())
        if word_count <= 4 and current_step:
            if current_step == 'strengths':
                # Activity words that indicate strengths when mentioned briefly
                activity_words = ['helping', 'teaching', 'cooking', 'playing', 'singing', 
                                 'dancing', 'drawing', 'writing', 'gaming', 'listening',
                                 'caring', 'supporting', 'making', 'creating', 'building']
                if any(activity in text_lower for activity in activity_words):
                    if 'strengths' not in intent_scores:
                        intent_scores['strengths'] = 0.0
                    intent_scores['strengths'] += 0.7  # Strong boost for short activity responses
                    if 'support_people' in intent_scores:
                        intent_scores['support_people'] -= 0.4
                        
            elif current_step == 'support_people':
                # Person/relationship words that indicate support when mentioned briefly
                support_words = ['mom', 'mum', 'dad', 'mother', 'father', 'parents', 'family',
                                'friends', 'friend', 'teacher', 'counselor', 'counsellor', 
                                'therapist', 'elder', 'aunty', 'uncle', 'cousin', 'sister',
                                'brother', 'nan', 'pop', 'grandma', 'grandpa']
                if any(person in text_lower for person in support_words):
                    if 'support_people' not in intent_scores:
                        intent_scores['support_people'] = 0.0
                    intent_scores['support_people'] += 0.7  # Strong boost for short support responses
                    if 'strengths' in intent_scores:
                        intent_scores['strengths'] -= 0.4
            
            elif current_step == 'worries':
                # Short worry responses get boosted
                worry_indicators = ['stress', 'anxious', 'worried', 'scared', 'nervous']
                if any(worry in text_lower for worry in worry_indicators):
                    if 'worries' not in intent_scores:
                        intent_scores['worries'] = 0.0
                    intent_scores['worries'] += 0.7
                    
            elif current_step == 'goals':
                # Short goal responses get boosted
                goal_indicators = ['want', 'hope', 'plan', 'goal', 'dream', 'finish', 'achieve']
                if any(goal in text_lower for goal in goal_indicators):
                    if 'goals' not in intent_scores:
                        intent_scores['goals'] = 0.0
                    intent_scores['goals'] += 0.7
        
        # If there's negation with strength/support keywords, boost negation intent
        if has_negation:
            # Check if text contains strength-related words (even with low scores)
            strength_words = ['cook', 'play', 'help', 'teach', 'good', 'skill', 'talent']
            has_strength_words = any(word in text_lower for word in strength_words)
            
            # Check if text contains support-related words
            support_words = ['friends', 'family', 'support', 'help', 'care']
            has_support_words = any(word in text_lower for word in support_words)
            
            if has_strength_words or ('strengths' in intent_scores and intent_scores['strengths'] > 0.2):
                intent_scores['negation'] = intent_scores.get('negation', 0) + 0.8
                if 'strengths' in intent_scores:
                    intent_scores['strengths'] *= 0.2  # Drastically reduce strength score
                    
            if has_support_words or ('support_people' in intent_scores and intent_scores['support_people'] > 0.2):
                intent_scores['negation'] = intent_scores.get('negation', 0) + 0.6
                if 'support_people' in intent_scores:
                    intent_scores['support_people'] *= 0.2  # Drastically reduce support score
        
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
