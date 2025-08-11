# AIMhi-Y Chatbot Detailed Task List

This task list is based on the PRD and Implementation Plan.

## Week 1: Foundation & Core FSM (M1)

### Goals
- Establish project structure and development environment.
- Build core FSM logic for the 4-step model.
- Create a basic web UI shell.
- Implement the `/chat` endpoint.

### Tasks

#### Project Setup
- [ ] Initialize Git repository with a proper `.gitignore` file.
- [ ] Set up a Python virtual environment (Python 3.9+).
- [ ] Create the project directory structure as outlined in the implementation plan.
- [ ] Install core dependencies: `Flask`, `transitions`, `python-dotenv`, `gunicorn`.
- [ ] Create `config/llm_config.json` with initial model and safety configurations.

#### FSM Implementation
- [ ] Define states in `core/fsm.py`: `welcome`, `support_people`, `strengths`, `worries`, `goals`, `summary`.
- [ ] Implement state transition logic using the `transitions` library.
- [ ] Set up in-memory session management in `core/session.py`.
- [ ] Populate `config/content.json` with culturally appropriate prompts for each FSM step.

#### Web UI & API
- [ ] Create a responsive `index.html` template using Bootstrap 5.
- [ ] Implement a chat bubble interface in the frontend.
- [ ] Add a visual step progress indicator to the UI.
- [ ] Build the `/chat` POST endpoint in `app.py`.
- [ ] Implement session cookie handling.
- [ ] Add a persistent "Get Help" button to the UI.

#### Testing
- [ ] Write unit tests for FSM transitions in `tests/test_fsm.py`.
- [ ] Write basic API tests for the `/chat` endpoint in `tests/test_api.py`.

---

## Week 2: NLP & Safety Features (M2)

### Goals
- Implement the spaCy NLP pipeline.
- Build the risk detection system.
- Create the message router.
- Add accessibility features to the UI.

### Tasks

#### NLP Setup
- [ ] Install NLP dependencies: `spacy`, `rapidfuzz`, `textblob`.
- [ ] Download the `en_core_web_sm` spaCy model.
- [ ] Create a text normalization pipeline in `nlp/preprocessor.py`.
- [ ] Implement lemmatization for better keyword matching.

#### Risk Detection System
- [ ] Create `config/risk_phrases.json` with risk phrases and crisis resources.
- [ ] Build a `PhraseMatcher` with fuzzy matching in `nlp/risk_detector.py`.
- [ ] Implement the immediate risk response protocol in the router.
- [ ] Write comprehensive risk detection tests in `tests/test_risk.py`.

#### Message Router
- [ ] Implement the dispatcher logic in `core/router.py`.
- [ ] Create intent patterns for common user inputs.
- [ ] Add empathetic clarifier templates to `config/content.json`.

#### Accessibility
- [ ] Add ARIA labels to all interactive UI elements.
- [ ] Ensure full keyboard navigation for the chat interface.
- [ ] Check color contrast and font sizes for WCAG AA compliance.

---

## Week 3: LLM Integration & Data Layer (M3)

### Goals
- Add an optional LLM fallback for open-ended questions.
- Implement SQLite for chat history storage.
- Build robust guardrails and filters for the LLM.
- Create a comprehensive testing suite for the LLM.

### Tasks

#### Database Layer
- [ ] Create the SQLite schema in `database/schema.sql`.
- [ ] Implement chat history storage in `database/repository.py`.
- [ ] Add session management with UUIDs.
- [ ] Create a history retrieval function for the LLM context.
- [ ] Implement data retention limits.

#### LLM Integration
- [ ] Set up the LLM infrastructure (Hugging Face Inference API or local).
- [ ] Implement the LLM client in `llm/client.py`.
- [ ] Create a prompt engineering system in `llm/prompts.py`.
- [ ] Implement context management in `llm/context.py`.

#### Guardrails & Filters
- [ ] Build comprehensive guardrails in `llm/guardrails.py` (PII filtering, length checks).
- [ ] Create fallback templates for filtered LLM responses.
- [ ] Implement a circuit breaker for LLM failures.
- [ ] Add model selection logic based on configuration.

#### Testing
- [ ] Write LLM-specific tests in `tests/test_llm.py` (timeout, filtering, prompt injection).
- [ ] Write guardrail tests in `tests/test_guardrails.py`.

---

## Week 4: Testing, Documentation & Deployment (M4)

### Goals
- Complete the testing suite with high coverage.
- Deploy the application to a hosting platform.
- Create comprehensive documentation.
- Conduct a stakeholder demo.

### Tasks

#### Testing Sprint
- [ ] Write integration tests for the complete 4-step flow.
- [ ] Test risk trigger and recovery scenarios.
- [ ] Test LLM timeout and fallback handling.
- [ ] Perform manual accessibility testing with screen readers.

#### Deployment
- [ ] Prepare production environment configurations (`.env.production`).
- [ ] Deploy the application to Render or another hosting platform.
- [ ] Configure build and start commands.
- [ ] Set up environment variables and secrets.
- [ ] Test the deployed application on multiple devices.

#### Documentation
- [ ] Complete the `README.md` with setup and usage instructions.
- [ ] Create API documentation.
- [ ] Write a `SAFETY.md` document detailing safety protocols.
- [ ] Create an architecture diagram.

#### Demo
- [ ] Prepare a demo script covering all key features.
- [ ] Create a stakeholder presentation.
- [ ] Record a short demo video (3-5 minutes).
