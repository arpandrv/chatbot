# DistilBERT Implementation Todo List

## Overview

This document tracks all tasks required to implement the DistilBERT-based intent classification system as detailed in DISTILBERT_IMPLEMENTATION_PLAN.md.

**Goal**: Replace rule-based intent classification with fine-tuned DistilBERT model while maintaining existing sentiment analysis.

**Timeline**: 4 weeks total

- Week 1: Data Preparation & Model Development
- Week 2: Training & System Integration
- Week 3: Testing & Validation
- Week 4: Deployment & Monitoring

---

## Phase 1: Data Preparation

### 1.1 Dataset Creation

- [ ] **Create training folder structure**
  
  - [ ] Create `aimhi-chatbot/training/` directory
  - [ ] Create subdirectories: `data/`, `scripts/`, `checkpoints/`

- [ ] **Merge intent categories**
  
  - [ ] Create `training/prepare_distilbert_data.py` script
  - [ ] Load `rawdata.txt` (476 samples)
  - [ ] Remove feeling_positive/neutral/negative samples (~45 samples)
  - [ ] Apply merging rules:
    - welcome + greetings → greeting
    - identity_questions + help_questions → question
    - affirmation + feeling_positive → affirmative
    - negative + deflection → negative
  - [ ] Remove all feeling intents completely
  - [ ] Map to 12 final intent classes

### 1.2 Data Augmentation

- [ ] **Balance dataset**
  - [ ] Analyze class distribution after merging
  - [ ] Generate synthetic samples for underrepresented classes
  - [ ] Use paraphrasing techniques for augmentation
  - [ ] Target: ~50 samples per major class, ~30 for no_* variants
  - [ ] Final dataset: ~600 samples total

### 1.3 Data Splitting

- [ ] **Create train/val/test splits**
  - [ ] Implement 70/15/15 split ratio
  - [ ] Ensure balanced distribution across splits
  - [ ] Save as `merged_training_data.csv`
  - [ ] Create separate files: `train.csv`, `val.csv`, `test.csv`
  - [ ] Generate data statistics report

### 1.4 Question Sub-classifier

- [ ] **Implement question type detection**
  - [ ] Create `classify_question_subtype()` function
  - [ ] Define identity_question markers
  - [ ] Define help_question markers
  - [ ] Test with various question inputs

---

## Phase 2: Model Development

### 2.1 DistilBERT Classifier Implementation

- [ ] **Create core classifier file**
  - [ ] Create `nlp/intent_distilbert.py`
  - [ ] Implement `DistilBertIntentClassifier` class
  - [ ] Add model loading/initialization
  - [ ] Implement preprocessing pipeline
  - [ ] Add inference method with confidence scores

### 2.2 Model Architecture

- [ ] **Configure model architecture**
  - [ ] Base model: distilbert-base-uncased
  - [ ] Add classification head (12 classes)
  - [ ] Implement dropout for regularization
  - [ ] Configure attention mechanisms

### 2.3 Training Script

- [ ] **Create training pipeline**
  - [ ] Create `training/train_distilbert.py`
  - [ ] Implement data loaders
  - [ ] Configure training parameters:
    - Learning rate: 2e-5
    - Batch size: 16
    - Max epochs: 10
    - Early stopping patience: 3
  - [ ] Add weighted loss for class imbalance
  - [ ] Implement validation loop
  - [ ] Add checkpointing mechanism

### 2.4 Model Features

- [ ] **Add advanced features**
  - [ ] Confidence thresholding (>0.3)
  - [ ] Context-aware boosting based on FSM state
  - [ ] Fallback to 'unclear' for low confidence
  - [ ] Question subtype detection integration
  - [ ] Singleton pattern for model loading

### 2.5 Model Serialization

- [ ] **Save and load utilities**
  - [ ] Save model to `models/distilbert_intent/`
  - [ ] Save tokenizer configuration
  - [ ] Save label mappings
  - [ ] Create model versioning system
  - [ ] Generate training report JSON

---

## Phase 3: System Integration

### 3.1 Router Enhancement

- [ ] **Modify router.py**
  
  - [ ] Import DistilBERT classifier
  
  - [ ] Add dual analysis pipeline:
    
    ```python
    intent, intent_conf = classify_intent_distilbert(message, fsm.state)
    sentiment, sentiment_conf = analyze_sentiment(message)
    ```
  
  - [ ] Implement confidence-based decision matrix
  
  - [ ] Add debug logging for both analyses

### 3.2 Response Selection Logic

- [ ] **Enhanced response selection**
  - [ ] Update `response_selector.py`
  - [ ] Implement decision matrix:
    - Clear both (>0.3, >0.5): Use both
    - Clear intent only: Use intent + neutral sentiment
    - Clear sentiment only: Apply empathetic tone
    - Both unclear: Progressive fallback
  - [ ] Add special case handlers

### 3.3 Progressive Fallback System

- [ ] **Implement fallback chain**
  - [ ] Attempt 1: Ask for clarification
  - [ ] Attempt 2: Offer choice to skip
  - [ ] Attempt 3: Force advance with acknowledgment
  - [ ] Track attempt counts in session
  - [ ] Reset counters on successful classification

### 3.4 Configuration Updates

- [ ] **Update configuration files**
  
  - [ ] Modify `conversation_patterns.json`:
    
    - Remove feeling patterns
    - Update intent mappings
  
  - [ ] Update `.env` with new flags:
    
    ```
    USE_DISTILBERT_INTENT=true
    DISTILBERT_MODEL_PATH=models/distilbert_intent
    INTENT_CONFIDENCE_THRESHOLD=0.3
    SENTIMENT_CONFIDENCE_THRESHOLD=0.5
    FALLBACK_TO_RULES=true
    ```
  
  - [ ] Keep `response_pools.json` unchanged

### 3.5 Backwards Compatibility

- [ ] **Maintain rule-based fallback**
  - [ ] Keep original `intent.py` as fallback
  - [ ] Add feature flag for switching
  - [ ] Implement smooth degradation
  - [ ] Log when fallback is used

---

## Phase 4: Testing & Validation

### 4.1 Unit Tests

- [ ] **Create test suite**
  - [ ] Create `tests/test_distilbert_intent.py`
  - [ ] Test intent classification accuracy
  - [ ] Test confidence threshold behavior
  - [ ] Test question subtype detection
  - [ ] Test context boosting logic
  - [ ] Test model loading/caching

### 4.2 Integration Tests

- [ ] **Test dual analysis pipeline**
  - [ ] Test clear cases (high confidence)
  - [ ] Test ambiguous cases (low confidence)
  - [ ] Test sentiment-driven cases
  - [ ] Test FSM context influence
  - [ ] Test progressive fallback triggering

### 4.3 End-to-End Tests

- [ ] **Complete conversation flows**
  - [ ] Normal flow with clear intents
  - [ ] Unclear intent handling
  - [ ] Mixed confidence scenarios
  - [ ] Sentiment-only guidance
  - [ ] Multiple fallback attempts

### 4.4 Performance Testing

- [ ] **Benchmark performance**
  - [ ] Measure DistilBERT inference time (<100ms target)
  - [ ] Measure total routing time (<200ms target)
  - [ ] Test memory usage (~500MB runtime)
  - [ ] Test concurrent sessions
  - [ ] Profile CPU/GPU usage

### 4.5 Accuracy Validation

- [ ] **Validate model accuracy**
  - [ ] Test set accuracy (>85% target)
  - [ ] Confusion matrix analysis
  - [ ] Per-class precision/recall
  - [ ] Error analysis report
  - [ ] Compare with rule-based baseline

---

## Phase 5: Documentation & Deployment

### 5.1 Documentation

- [ ] **Update documentation**
  - [ ] Update README.md with new architecture
  - [ ] Document API changes
  - [ ] Create model training guide
  - [ ] Update CLAUDE.md with new commands
  - [ ] Create troubleshooting guide

### 5.2 Deployment Preparation

- [ ] **Prepare for production**
  - [ ] Model optimization (quantization optional)
  - [ ] Create deployment checklist
  - [ ] Set up monitoring dashboard
  - [ ] Configure logging for production
  - [ ] Create rollback plan

### 5.3 A/B Testing Setup

- [ ] **Configure gradual rollout**
  - [ ] Implement session-based routing
  - [ ] Create metrics collection
  - [ ] Set up comparison dashboard
  - [ ] Define success criteria
  - [ ] Plan rollout phases (10% → 50% → 100%)

---

## Dependencies & Requirements

### Python Packages to Add

- [ ] Install transformers==4.35.0
- [ ] Install torch==2.1.0 (already have scikit-learn)
- [ ] Verify sentence-transformers compatibility
- [ ] Update requirements.txt

### Pre-training Setup

- [ ] Download distilbert-base-uncased model
- [ ] Set up CUDA/GPU if available
- [ ] Configure memory limits
- [ ] Test model loading

---

## Risk Mitigation Tasks

### Contingency Planning

- [ ] **Failure scenarios**
  - [ ] Test model loading failure → fallback
  - [ ] Test low accuracy handling
  - [ ] Test memory overflow protection
  - [ ] Test timeout handling
  - [ ] Document recovery procedures

### Monitoring Setup

- [ ] **Tracking metrics**
  - [ ] Set up confidence distribution logging
  - [ ] Track fallback frequency
  - [ ] Monitor response times
  - [ ] Track conversation completion rates
  - [ ] Set up alerts for anomalies

---

## Success Metrics Checklist

### Quantitative Goals

- [ ] Intent classification accuracy >85%
- [ ] Response time <200ms (95th percentile)
- [ ] Conversation completion rate >80%
- [ ] Fallback usage <20%
- [ ] Zero conversation dead-ends

### Qualitative Goals

- [ ] Smooth conversation flow
- [ ] Appropriate emotional responses
- [ ] Successful ambiguous input handling
- [ ] Cultural appropriateness maintained
- [ ] Positive user feedback

---

## Additional Considerations

### Cultural & Safety

- [ ] Review training data for cultural appropriateness
- [ ] Ensure Aboriginal and Torres Strait Islander context preserved
- [ ] Validate risk detection still works correctly
- [ ] Test with culturally specific language patterns

### Future Enhancements (Post-MVP)

- [ ] Multi-turn context awareness
- [ ] User adaptation over time
- [ ] Additional language support
- [ ] Model fine-tuning based on production data
- [ ] Advanced sentiment integration

---

## Task Priority Order

1. **Critical Path** (Must complete in order):
   
   - Data preparation → Model training → Integration → Testing

2. **Parallel Tasks** (Can be done simultaneously):
   
   - Documentation while testing
   - Performance optimization during integration
   - Monitoring setup during deployment prep

3. **Optional Enhancements** (If time permits):
   
   - Model quantization
   - Advanced logging
   - Dashboard creation
   - A/B testing infrastructure

---

## Timeline Summary

| Week | Focus                  | Key Deliverables                      |
| ---- | ---------------------- | ------------------------------------- |
| 1    | Data & Model           | Merged dataset, DistilBERT classifier |
| 2    | Training & Integration | Trained model, Modified router        |
| 3    | Testing & Validation   | Test suite, Performance metrics       |

---

## Notes

- Keep rule-based system as fallback throughout(make a new folder called fallback and move the current rule based logic over there and use that as modules for fallback)
- Prioritize conversation flow over perfect accuracy
- Maintain cultural sensitivity at all stages
- Document all decisions and changes
