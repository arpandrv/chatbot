# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIMhi-Y Supportive Yarn Chatbot - A culturally safe web-based chatbot for Aboriginal and Torres Strait Islander youth, implementing the AIMhi Stay Strong 4-step model (support people → strengths → worries → goals).

## Key Architecture

### Core Components
- **Flask API** (`app.py`): Main web server with `/chat` endpoint
- **FSM State Management** (`core/fsm.py`): Manages conversation flow through 4 steps using transitions library
- **Message Router** (`core/router.py`): Routes messages through risk detection → intent classification → FSM → response generation
- **Hybrid Intent Classification**: 
  - Primary: DistilBERT model (`nlp/intent_distilbert.py`) - 13 intent classes
  - Fallback: Rule-based system (`fallbacks/rule_based_intent.py`)
- **Risk Detection** (`nlp/risk_detector.py`): Priority-1 safety system for crisis language
- **Sentiment Analysis** (`nlp/sentiment.py`): Twitter-RoBERTa model for emotional context

### Data Flow
1. User input → Risk detection (first priority)
2. Intent classification (DistilBERT with rule-based fallback)  
3. FSM state management and response selection
4. Optional LLM fallback for open-ended inputs
5. Response generation with cultural safety filters

## Common Commands

### Development
```bash
# Setup virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r aimhi-chatbot/requirements.txt

# Run application
cd aimhi-chatbot
python app.py

# Application runs on http://127.0.0.1:5000
```

### Testing
```bash
cd aimhi-chatbot
python -m pytest tests/              # Run all tests
python -m pytest tests/test_risk.py  # Run specific test file
python -m pytest -v                  # Verbose output
python -m pytest -k "test_name"      # Run specific test
```

### Training DistilBERT Model
```bash
cd aimhi-chatbot/training
python train_distilbert.py           # Train intent classifier (~45-90 min on CPU)
python test_distilbert_inference.py  # Test inference performance
```

## Performance Requirements
- **Response time**: <500ms total (FSM path)
- **DistilBERT inference**: <100ms target
- **Risk detection**: Deterministic, immediate response
- **LLM fallback**: Optional, 3s timeout

## Safety & Cultural Considerations
- **Risk protocol**: Immediate escalation for crisis language (configured in `config/risk_phrases.json`)
- **Cultural terms**: Normalized in preprocessing (e.g., "mob" → "family", "deadly" → "good")
- **No PII storage**: Session IDs are anonymous UUIDs
- **Strengths-based language**: Warm, non-clinical tone throughout

## Key Files to Know
- `config/risk_phrases.json`: Crisis language patterns
- `config/responses.json`: Pre-approved response templates  
- `database/repository.py`: Optional chat history storage
- `llm/guardrails.py`: Output filtering for LLM responses
- `nlp/preprocessor.py`: Text normalization with cultural terms

## Environment Variables
Create `.env` file with:
- `SECRET_KEY`: Flask secret key
- `LLM_ENABLED`: Enable/disable LLM fallback
- `PRIVACY_STRICT`: Strict privacy mode
- `MAX_HISTORY`: LLM context window size

## Important Notes
- This is a prototype/demo only - not for clinical use
- Maintains conversation state in memory (per session)
- Uses SQLite for optional chat history storage
- Models stored in `ai_models/` and `models/` directories
- All responses must pass cultural safety filters