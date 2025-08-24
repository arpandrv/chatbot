from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    BOT = "bot"


class FSMState(str, Enum):
    WELCOME = "welcome"
    SUPPORT_PEOPLE = "support_people"
    STRENGTHS = "strengths"
    WORRIES = "worries"
    GOALS = "goals"
    SUMMARY = "summary"


class FSMStep(str, Enum):
    SUPPORT_PEOPLE = "support_people"
    STRENGTHS = "strengths"
    WORRIES = "worries"
    GOALS = "goals"


class IntentMethod(str, Enum):
    DISTILBERT = "distilbert"
    RULE_BASED = "rule_based"
    HYBRID = "hybrid"


class SummaryType(str, Enum):
    PARTIAL = "partial"
    COMPLETE = "complete"
    LLM_CONTEXT = "llm_context"


class EventType(str, Enum):
    SESSION_STARTED = "session_started"
    SESSION_COMPLETED = "session_completed"
    STEP_COMPLETED = "step_completed"
    RISK_TRIGGERED = "risk_triggered"
    LLM_FALLBACK_USED = "llm_fallback_used"
    DISTILBERT_USED = "distilbert_used"
    RULE_BASED_USED = "rule_based_used"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ============== Core Models ==============

class Session(BaseModel):
    session_id: str
    fsm_state: FSMState = FSMState.WELCOME
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    completed: bool = False
    completion_time: Optional[datetime] = None


class ChatMessage(BaseModel):
    session_id: str
    role: MessageRole
    message: str
    timestamp: Optional[datetime] = None

    class Config:
        use_enum_values = True


class UserResponse(BaseModel):
    session_id: str
    step: FSMStep
    response: Optional[str] = None
    attempt_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class RiskDetection(BaseModel):
    session_id: str
    trigger_phrase: str
    user_message: str
    detected_at: Optional[datetime] = None
    resources_shown: bool = True


class SessionSummary(BaseModel):
    session_id: str
    summary_type: SummaryType
    summary_data: Dict[str, Any]
    generated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class AnalyticsEvent(BaseModel):
    event_type: EventType
    event_data: Optional[Dict[str, Any]] = None
    session_count: int = 1
    timestamp: Optional[datetime] = None

    class Config:
        use_enum_values = True


class IntentClassification(BaseModel):
    session_id: str
    user_message: str
    classified_intent: str
    confidence: Optional[float] = None
    method: IntentMethod
    fsm_state: Optional[str] = None
    inference_time_ms: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class SystemLog(BaseModel):
    log_level: LogLevel
    component: str
    message: str
    session_id: Optional[str] = None
    error_trace: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


# ============== Request/Response Models ==============

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    state: str
    flags: Dict[str, Any] = {}
    debug: Optional[Dict[str, Any]] = None


class SessionStats(BaseModel):
    total_sessions: int
    completed_sessions: int
    completion_rate: float
    active_sessions: int


class AnalyticsSummary(BaseModel):
    event_counts: Dict[str, int]
    completion_stats: Dict[str, Any]
    date_range: str


# ============== FSM Models ==============

class FSMAttempts(BaseModel):
    support_people: int = 0
    strengths: int = 0
    worries: int = 0
    goals: int = 0


class FSMResponses(BaseModel):
    support_people: Optional[str] = None
    strengths: Optional[str] = None
    worries: Optional[str] = None
    goals: Optional[str] = None


class FSMData(BaseModel):
    session_id: str
    state: FSMState
    responses: FSMResponses
    attempts: FSMAttempts

    class Config:
        use_enum_values = True


# ============== Validation Models ==============

class UserInputValidation(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    is_valid: bool = True
    validation_errors: list[str] = []


class IntentResult(BaseModel):
    intent: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    method: IntentMethod
    inference_time_ms: Optional[int] = None

    class Config:
        use_enum_values = True


class RiskAssessment(BaseModel):
    is_risk: bool
    trigger_phrases: list[str] = []
    confidence: float = Field(..., ge=0.0, le=1.0)
    action_required: bool = False
