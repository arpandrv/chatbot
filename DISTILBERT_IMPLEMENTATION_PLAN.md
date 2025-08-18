# DistilBERT Intent Classification Implementation Plan

## Executive Summary

This document outlines the comprehensive plan to upgrade the AIMhi-Y Chatbot's intent classification system from rule-based pattern matching to a fine-tuned DistilBERT model, while maintaining the existing Twitter-RoBERTa sentiment analysis. The new architecture implements a dual-analysis pipeline where every user message is analyzed for both intent (what they want) and sentiment (how they feel).

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Intent Consolidation Strategy](#intent-consolidation-strategy)
3. [Implementation Phases](#implementation-phases)
4. [Integration Details](#integration-details)
5. [Error Handling Strategy](#error-handling-strategy)
6. [Testing Plan](#testing-plan)
7. [Performance Targets](#performance-targets)
8. [Risk Mitigation](#risk-mitigation)

---

## Architecture Overview

### Current System Analysis

The existing system has two separate emotional analysis systems creating redundancy:

1. **Sentiment Analysis** (`sentiment.py`)
   - Uses Twitter-RoBERTa model
   - Classifies messages into positive/negative/neutral
   - Used for response tone matching

2. **Feeling Intents** (in training data)
   - `feeling_positive`, `feeling_neutral`, `feeling_negative`
   - Redundant with sentiment analysis
   - Creates unnecessary complexity

### Proposed Dual-Analysis Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌─────────────┐
│ User Input  │────▶│Risk Detection│────▶│ Dual Analysis    │────▶│  Response   │
└─────────────┘     └──────────────┘     │ ├─Intent (BERT)  │     │ Selection   │
                                          │ └─Sentiment(RoBERTa)    └─────────────┘
                                          └──────────────────┘
```

### Key Design Principles

1. **Separation of Concerns**
   - Intent: WHAT the user wants to communicate
   - Sentiment: HOW the user is feeling
   
2. **Robust Fallback Chain**
   - DistilBERT → Rule-based → FSM-based → Force advance
   
3. **Context Awareness**
   - FSM state influences intent interpretation
   - Sentiment affects response tone selection

---

## Intent Consolidation Strategy

### Original Intent Classes (19 total)

Based on analysis of `rawdata.txt` and system files:

| Category | Intents |
|----------|---------|
| Core FSM | support_people, strengths, worries, goals |
| General | greeting, affirmation, negation, question, unclear |
| Feelings | feeling_positive, feeling_neutral, feeling_negative |
| Special | identity_question, help_question, deflection |
| Negatives | no_support, no_strengths, no_worries, no_goals |

### Consolidated Intent Classes (12 total)

| # | Intent | Description | Merged From |
|---|--------|-------------|-------------|
| 1 | **greeting** | Greetings and salutations | - |
| 2 | **question** | All questions | identity_question + help_question |
| 3 | **affirmative** | Agreement and confirmation | affirmation only (NOT feelings) |
| 4 | **negative** | Disagreement and avoidance | negation + deflection |
| 5 | **support_people** | Discussing support network | - |
| 6 | **strengths** | Personal strengths and skills | - |
| 7 | **worries** | Concerns and stressors | - |
| 8 | **goals** | Future aspirations | - |
| 9 | **no_support** | Lack of support network | - |
| 10 | **no_strengths** | Denial of strengths | - |
| 11 | **no_worries** | No current concerns | - |
| 12 | **no_goals** | Lack of goals | - |
| 13 | **unclear** | Ambiguous or off-topic | - |

**Note**: Feeling intents (feeling_positive/neutral/negative) are completely removed as sentiment analysis handles this.

### Question Sub-classification

Since we merge identity and help questions, we need a simple sub-classifier:

```python
def classify_question_subtype(text):
    """Simple keyword-based question type detection"""
    text_lower = text.lower()
    
    identity_markers = ["who are you", "what are you", "your name", "are you yarn"]
    help_markers = ["can you help", "need help", "support me", "what can you do"]
    
    if any(marker in text_lower for marker in identity_markers):
        return "identity_question"
    elif any(marker in text_lower for marker in help_markers):
        return "help_question"
    return "general_question"
```

---

## Implementation Phases

### Phase 1: Data Preparation (Week 1)

#### 1.1 Create Merged Dataset

**File**: `training/prepare_distilbert_data.py`

```python
Tasks:
- Load rawdata.txt (476 samples)
- Remove feeling_positive/neutral/negative samples (~45 samples)
- Apply intent merging rules
- Result: ~400 samples across 12 classes
- Generate augmented samples for balance
- Create 70/15/15 train/val/test split
- Save as merged_training_data.csv
```

**Expected Data Distribution**:
| Intent | Original Samples | After Augmentation |
|--------|-----------------|-------------------|
| support_people | ~30 | 50 |
| strengths | ~35 | 50 |
| worries | ~30 | 50 |
| goals | ~30 | 50 |
| greeting | ~30 | 50 |
| question | ~40 (merged) | 50 |
| affirmative | ~20 | 50 |
| negative | ~35 (merged) | 50 |
| no_* variants | ~20 each | 30 each |
| unclear | ~20 | 40 |

Total: ~600 samples after augmentation

### Phase 2: Model Development (Week 1-2)

#### 2.1 DistilBERT Classifier Implementation

**File**: `nlp/intent_distilbert.py`

```python
class DistilBertIntentClassifier:
    """
    Features:
    - Model: distilbert-base-uncased (66M parameters)
    - 12 output classes
    - Confidence thresholding
    - Context-aware boosting
    - Question subtype detection
    - Fallback to 'unclear' for low confidence
    """
```

#### 2.2 Training Script

**File**: `training/train_distilbert.py`

**Training Parameters**:
- Base model: distilbert-base-uncased
- Learning rate: 2e-5
- Batch size: 16
- Max epochs: 10
- Early stopping patience: 3
- Optimizer: AdamW
- Loss: Weighted CrossEntropy (for class imbalance)

**Expected Training Time**: 
- CPU: ~30-45 minutes
- GPU: ~5-10 minutes

### Phase 3: System Integration (Week 2)

#### 3.1 Router Enhancement

**File**: `core/router.py` (MODIFY)

Key changes:
```python
def route_message(session_id, message):
    # 1. Risk detection (unchanged)
    # 2. Dual analysis (NEW)
    intent, intent_conf = classify_intent_distilbert(message, fsm.state)
    sentiment, sentiment_conf = analyze_sentiment(message)
    # 3. Enhanced response selection (NEW)
    reply = select_response_with_dual_analysis(...)
```

#### 3.2 Response Selection Logic

The response selection uses a decision matrix based on confidence levels:

```python
def select_response_with_dual_analysis():
    """
    Decision flow:
    1. Check FSM state
    2. Evaluate intent and sentiment confidence
    3. Apply appropriate response strategy
    4. Handle edge cases with progressive fallback
    """
```

### Phase 4: Testing & Validation (Week 3)

#### 4.1 Unit Tests

**File**: `tests/test_distilbert_intent.py`

#### 4.2 Integration Tests

Test all FSM state transitions with various confidence combinations.

---

## Integration Details

### File Structure Changes

```
aimhi-chatbot/
├── nlp/
│   ├── intent_distilbert.py          # NEW: DistilBERT classifier
│   ├── intent.py                      # KEEP: Fallback classifier
│   ├── sentiment.py                   # UNCHANGED: Twitter-RoBERTa
│   └── response_selector.py           # ENHANCE: Already handles sentiment
├── training/
│   ├── prepare_distilbert_data.py    # NEW: Data preparation
│   ├── train_distilbert.py           # NEW: Training script
│   └── merged_training_data.csv      # NEW: Cleaned dataset
├── models/
│   └── distilbert_intent/            # NEW: Saved model directory
├── core/
│   ├── router.py                     # MODIFY: Add dual analysis
│   └── fsm.py                        # UNCHANGED
├── config/
│   ├── conversation_patterns.json    # MODIFY: Remove feeling patterns
│   └── response_pools.json           # UNCHANGED: Works as-is
└── tests/
    └── test_distilbert_intent.py     # NEW: Test suite
```

### Configuration Updates

**.env additions**:
```bash
# DistilBERT Configuration
USE_DISTILBERT_INTENT=true
DISTILBERT_MODEL_PATH=models/distilbert_intent
INTENT_CONFIDENCE_THRESHOLD=0.3
SENTIMENT_CONFIDENCE_THRESHOLD=0.5
FALLBACK_TO_RULES=true
```

### Integration Points

1. **Router.py Integration**
   - Lines 76-98: Replace intent classification
   - Lines 100-350: Enhance response selection logic

2. **Response Selector Enhancement**
   - Already handles sentiment in `_select_by_sentiment()`
   - No major changes needed

3. **FSM Compatibility**
   - No changes to FSM logic
   - Progressive fallback system remains

---

## Error Handling Strategy

### Confidence-Based Decision Matrix

| Scenario | Intent Conf | Sentiment Conf | FSM State | Action |
|----------|------------|----------------|-----------|---------|
| **Clear Both** | >0.3 | >0.5 | Any | Use both for response |
| **Clear Intent** | >0.3 | <0.5 | Any | Use intent + neutral sentiment |
| **Clear Sentiment** | <0.3 | >0.5 | Welcome | Use sentiment for feeling response |
| **Clear Sentiment** | <0.3 | >0.5 | Core states | Apply empathetic tone to clarification |
| **Both Unclear** | <0.3 | <0.5 | Welcome | Assume greeting, advance |
| **Both Unclear** | <0.3 | <0.5 | Core states | Progressive fallback |
| **Negative Sentiment** | Any | >0.8 | Any | Add empathy layer to response |

### Progressive Fallback System

```
Attempt 1: Ask for clarification
    ↓ (if unclear)
Attempt 2: Offer choice to skip
    ↓ (if still unclear)
Attempt 3: Force advance with acknowledgment
```

### Special Cases

1. **Welcome State + Sentiment**
   - If sentiment confidence > 0.7, use for "How are you?" response
   - Removes need for feeling_positive/negative/neutral intents

2. **Question Intent Handling**
   - Sub-classify into identity/help questions
   - Route to appropriate response pool

3. **Negative Intent Disambiguation**
   - Use sentiment to distinguish frustration from simple disagreement
   - Adjust response empathy accordingly

---

## Testing Plan

### Unit Testing

**Test Categories**:
1. Intent classification accuracy
2. Confidence threshold behavior
3. Question subtype detection
4. Context boosting logic

### Integration Testing

**Test Scenarios**:

```python
test_cases = [
    # Clear cases
    ("hello there", "greeting", "neutral"),
    ("my family helps me", "support_people", "positive"),
    
    # Ambiguous cases  
    ("idk", "unclear", "neutral"),
    ("not really", "negative", "neutral"),
    
    # Sentiment-driven cases
    ("fine", "unclear", "positive"),  # Sentiment helps
    ("terrible", "unclear", "negative"),  # Sentiment guides
    
    # FSM context cases
    ("helping others", "strengths", "positive"),  # In strengths state
    ("helping others", "support_people", "positive"),  # In support state
]
```

### End-to-End Testing

Complete conversation flows testing:
1. Normal flow with clear intents
2. Unclear intent handling
3. Mixed confidence scenarios
4. Sentiment-only guidance
5. Progressive fallback triggering

---

## Performance Targets

### Speed Metrics

| Component | Target | Acceptable |
|-----------|--------|------------|
| DistilBERT inference | <100ms | <150ms |
| Sentiment analysis | <50ms | <75ms |
| Total routing time | <200ms | <300ms |
| Fallback decision | <50ms | <100ms |

### Accuracy Metrics

| Metric | Target | Minimum |
|--------|--------|---------|
| Intent classification (test set) | >85% | >80% |
| Sentiment analysis | >90% | >85% |
| Conversation completion rate | >80% | >70% |
| User satisfaction | >4.0/5 | >3.5/5 |

### Resource Usage

- Model size: ~250MB (DistilBERT)
- Runtime memory: ~500MB
- CPU usage: <30% average
- GPU (optional): ~1GB VRAM

---

## Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Model fails to load | Low | High | Automatic fallback to rule-based |
| Low accuracy on production data | Medium | Medium | A/B testing with gradual rollout |
| Slow inference time | Low | Medium | Model quantization, caching |
| Memory constraints | Low | Low | Lazy loading, singleton pattern |

### Rollout Strategy

1. **Phase 1**: Deploy with feature flag disabled
2. **Phase 2**: Enable for 10% of sessions (A/B test)
3. **Phase 3**: Monitor metrics, adjust thresholds
4. **Phase 4**: Gradual increase to 100%
5. **Phase 5**: Remove rule-based system (optional)

### Monitoring Plan

**Key Metrics to Track**:
- Intent classification confidence distribution
- Sentiment analysis confidence distribution
- Fallback frequency by FSM state
- Average response time
- Conversation completion rates
- Error rates and types

**Logging Requirements**:
```python
logger.info({
    'session_id': session_id,
    'message': message,
    'intent': intent,
    'intent_conf': intent_conf,
    'sentiment': sentiment,
    'sentiment_conf': sentiment_conf,
    'fsm_state': fsm.state,
    'response_time_ms': elapsed,
    'fallback_used': fallback_used
})
```

---

## Success Criteria

### Quantitative Metrics

- [ ] Intent classification accuracy >85% on test set
- [ ] Response time <200ms for 95% of requests
- [ ] Conversation completion rate >80%
- [ ] Fallback usage <20% of interactions
- [ ] Zero conversation dead-ends

### Qualitative Metrics

- [ ] Smooth conversation flow maintained
- [ ] Appropriate emotional responses
- [ ] Successful handling of ambiguous inputs
- [ ] Cultural appropriateness preserved
- [ ] User feedback positive

---

## Implementation Timeline

| Week | Tasks | Deliverables |
|------|-------|--------------|
| **Week 1** | Data preparation, Model development | Merged dataset, DistilBERT classifier |
| **Week 2** | Training, Integration | Trained model, Modified router |
| **Week 3** | Testing, Optimization | Test suite, Performance tuning |
| **Week 4** | Deployment, Monitoring | Production deployment, Metrics dashboard |

---

## Appendices

### A. Sample Training Data Format

```csv
text,intent
"hello there",greeting
"my family supports me",support_people
"who are you",question
"can you help me",question
"yes please",affirmative
"no thanks",negative
"I don't want to talk about it",negative
```

### B. Model Artifacts Structure

```
models/
└── distilbert_intent/
    ├── config.json           # Model configuration
    ├── pytorch_model.bin     # Model weights
    ├── tokenizer_config.json # Tokenizer config
    ├── vocab.txt            # Vocabulary
    └── training_report.json # Training metrics
```

### C. Environment Setup

```bash
# Install required packages
pip install transformers==4.35.0
pip install torch==2.1.0
pip install scikit-learn==1.3.2

# Download base model (one-time)
python -c "from transformers import DistilBertModel; DistilBertModel.from_pretrained('distilbert-base-uncased')"
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-01-17 | AI Assistant | Initial comprehensive plan |

---

## Notes and Considerations

1. **Cultural Sensitivity**: Ensure training data maintains cultural appropriateness for Aboriginal and Torres Strait Islander youth.

2. **Privacy**: No PII in training data or logs.

3. **Fallback Philosophy**: Always progress conversation forward, never get stuck.

4. **Sentiment Priority**: In cases of high negative sentiment, empathy takes precedence over intent accuracy.

5. **Future Enhancements**: 
   - Multi-turn context awareness
   - User adaptation over time
   - Additional language support

---

*End of Document*