# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains the AIMhi-Y Supportive Yarn Chatbot - a mental health support chatbot designed specifically for Aboriginal and Torres Strait Islander youth. The chatbot implements the AIMhi Stay Strong 4-step therapeutic model through a carefully designed conversation flow.

## Repository Structure

The main application is located in the `aimhi-chatbot/` directory. Key components:

- **aimhi-chatbot/** - Main application directory containing all source code
- **sentiment_test_dataset.csv/json** - Test datasets for sentiment analysis
- **chatbot_flow_diagram.html** - Visual representation of conversation flow
- **RULE_BASED_LIMITATIONS_ANALYSIS.md** - Analysis of rule-based approach limitations

## Development Commands

### Environment Setup
```bash
cd aimhi-chatbot
pip install -r requirements.txt

# Download spaCy language model if needed
python -m spacy download en_core_web_sm

# Configure environment
cp .env.example .env  # Then edit .env with your settings
```

### Running the Application
```bash
cd aimhi-chatbot
# Development server
python app.py

# Production server
gunicorn app:app
```

### Testing
```bash
cd aimhi-chatbot
# Run all tests
python -m pytest tests/

# Run specific test suite
python -m pytest tests/test_integration.py -v

# Run with coverage
python -m pytest --cov=. tests/
```

### Linting and Code Quality
```bash
# Install dev dependencies
pip install pylint black isort

# Format code
black .
isort .

# Lint code
pylint core/ nlp/ llm/ database/
```

## Architecture Overview

### Core Application Flow
1. **Risk Detection First** - Every message passes through risk detection (nlp/risk_detector.py)
2. **FSM State Management** - Conversation follows predefined states: welcome → support_people → strengths → worries → goals → summary
3. **Intent Classification** - 6-layer hybrid system for understanding user intent
4. **LLM Fallback** - Optional OpenAI/Anthropic integration for handling edge cases

### Key Components

**Core Systems:**
- `core/fsm.py` - Finite state machine managing conversation flow
- `core/router.py` - Message routing logic and component integration
- `core/session.py` - Session management (anonymous, UUID-based)
- `core/user_profile.py` - User context building for LLM

**NLP Pipeline:**
- `nlp/risk_detector.py` - Deterministic crisis detection
- `nlp/intent.py` - 6-layer intent classification system
- `nlp/sentiment.py` - Sentiment analysis using Twitter-RoBERTa
- `nlp/preprocessor.py` - Text normalization and preprocessing

**LLM Integration:**
- `llm/client.py` - API client for OpenAI/Anthropic
- `llm/guardrails.py` - Safety filters for LLM outputs
- `llm/context_builder.py` - Context preparation for LLM

### Configuration
- `config/risk_phrases.json` - Risk detection patterns
- `config/content.json` - Conversation prompts and responses
- `config/conversation_patterns.json` - Intent classification patterns
- `config/llm_config.json` - LLM model settings
- `.env` - Environment variables and feature flags

## Testing Strategy

### Unit Tests
- `test_fsm.py` - State machine transitions
- `test_risk.py` - Risk detection accuracy
- `test_guardrails.py` - LLM output filtering

### Integration Tests
- `test_integration.py` - End-to-end conversation flows
- `test_api.py` - Flask endpoint testing
- `test_llm.py` - LLM integration (requires API keys)

## Important Implementation Details

### Safety and Privacy
- Risk detection runs FIRST on every message - no exceptions
- No PII storage - only anonymous session IDs
- All LLM outputs filtered through guardrails
- Crisis resources provided immediately when risk detected

### Performance Requirements
- Rule-based path: < 500ms response time
- LLM fallback: < 3s response time
- Session timeout: 30 minutes of inactivity

### Cultural Considerations
- Content designed for Aboriginal and Torres Strait Islander youth
- Language and examples culturally appropriate
- Follows AIMhi Stay Strong therapeutic model

## Current Status

### Completed Features
- ✅ Core FSM with 4-step flow
- ✅ Web interface (Flask + Bootstrap)
- ✅ 6-layer intent classification
- ✅ Sentiment analysis integration
- ✅ Risk detection system
- ✅ Database for chat history
- ✅ LLM fallback with guardrails
- ✅ Comprehensive test suite

### Known Limitations
- Prototype only - not for clinical use
- Limited to English language
- Requires internet for LLM fallback
- No voice interface

## Deployment Notes

### Local Development
The application runs on Flask development server by default. Use `python app.py` for quick testing.

### Production Deployment
Use Gunicorn or similar WSGI server. Ensure:
- Set `FLASK_ENV=production` in environment
- Configure proper SECRET_KEY in .env
- Enable HTTPS for production
- Set up proper logging and monitoring

## Database

SQLite database (`chat_history.db`) stores:
- Session IDs (anonymous)
- Message history (for LLM context)
- Timestamps

Schema defined in `database/schema.sql`. Initialize with `init_db()` function.