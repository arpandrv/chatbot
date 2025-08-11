# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the AIMhi-Y Supportive Yarn Chatbot - a web-based mental health support chatbot for Aboriginal and Torres Strait Islander youth. It implements the AIMhi Stay Strong 4-step model (support people → strengths → worries → goals) with deterministic risk detection and optional LLM fallback.

## Development Commands

### Setup Environment
```bash
# Install dependencies globally
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env
# Edit .env to configure LLM settings if needed
```

### Running the Application
```bash
# Development mode
python app.py

# Production server
gunicorn app:app
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_fsm.py

# Run with coverage
python -m pytest --cov=. tests/
```

## Architecture

### Core Components

1. **FSM (Finite State Machine)** - `core/fsm.py`
   - Manages conversation flow through 4 steps: welcome → support_people → strengths → worries → goals → summary
   - Uses the `transitions` library for state management

2. **Message Router** - `core/router.py`
   - Decision order: Risk check → FSM step gate → Intent classification → LLM fallback
   - Integrates all components (risk detection, FSM, NLP, LLM)
   - Handles session management and message persistence

3. **Risk Detection** - `nlp/risk_detector.py`
   - Deterministic pattern matching using spaCy PhraseMatcher
   - Configured via `config/risk_phrases.json`
   - Immediate crisis resource response when triggered

4. **LLM Integration** - `llm/`
   - Optional fallback for low-confidence inputs
   - Guardrails in `llm/guardrails.py` for output safety
   - Context management from chat history (last 6 messages)

5. **Database** - `database/repository.py`
   - SQLite for chat history storage (optional, required for LLM)
   - No PII storage, only session_id and messages

### Configuration Files

- `config/content.json` - Conversation prompts and templates
- `config/risk_phrases.json` - Risk detection patterns
- `config/llm_config.json` - LLM model settings
- `.env` - Environment variables (LLM keys, feature flags)

## Key Implementation Notes

### Safety First
- Risk detection ALWAYS runs first in the routing logic
- Deterministic crisis response, no ML gating
- All LLM outputs pass through guardrails

### Session Management
- Anonymous session IDs (UUID-based)
- Sessions stored in memory with FSM state
- Chat history in SQLite for LLM context only

### Feature Flags (in .env)
- `LLM_ENABLED` - Enable/disable LLM fallback
- `PRIVACY_STRICT` - Enhanced privacy mode
- `HISTORY_ENABLED` - Enable chat history storage
- `TELEMETRY_ENABLED` - Anonymous usage metrics

## Current Implementation Status

### Completed
- Core FSM with 4-step flow
- Web UI (Flask + Bootstrap)
- Basic NLP pipeline (spaCy)
- Risk detection system
- Database integration
- LLM fallback with guardrails

### TODO
- Comprehensive testing suite
- Expand risk phrase list
- Implement proper intent classification (currently placeholder)
- Deploy to hosting platform
- Accessibility improvements
- Cultural content review

## Testing Focus Areas

1. **Risk Detection**: Test with variations, misspellings, and edge cases
2. **FSM Transitions**: Verify all state transitions work correctly
3. **LLM Guardrails**: Ensure inappropriate content is filtered
4. **End-to-end Flow**: Complete conversation paths
5. **Error Handling**: Network failures, timeouts, invalid inputs

## Important Constraints

- **Non-clinical**: This is a prototype only - no diagnosis or clinical advice
- **Privacy**: No PII collection, anonymous sessions only
- **Performance**: Rule path should respond < 500ms, LLM < 3s
- **Cultural Safety**: All content must be culturally appropriate for Aboriginal and Torres Strait Islander youth