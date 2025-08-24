# AIMhi-Y Chatbot Codebase Remediation Guide

## Executive Summary

This document provides a comprehensive analysis and remediation plan for critical security vulnerabilities, architectural flaws, and code quality issues identified in the AIMhi-Y Supportive Yarn Chatbot codebase. The issues range from **CRITICAL** security vulnerabilities that could lead to system compromise, to architectural problems that prevent proper scaling and maintenance.

**Risk Level: HIGH** - Multiple critical security vulnerabilities require immediate attention before any production deployment.

---

## 🚨 CRITICAL SECURITY ISSUES (Immediate Action Required)

### 1. SQL Injection Vulnerability in Database Layer

**File:** `database/repository_v2.py:69-74`  
**Risk Level:** CRITICAL  
**Impact:** Complete database compromise, data theft, system takeover

#### Current Problem
```python
def insert_record(conn: sqlite3.Connection, table: str, data: Dict[str, Any]):
    columns = ', '.join(data.keys())
    placeholders = ', '.join('?' * len(data))
    conn.execute(f'INSERT INTO {table} ({columns}) VALUES ({placeholders})', 
                 tuple(data.values()))
```

**Issue:** Direct string interpolation of table and column names creates SQL injection vulnerability if user input reaches these parameters.

#### Solution
```python
def insert_record(conn: sqlite3.Connection, table: str, data: Dict[str, Any]):
    # Validate table name against whitelist
    ALLOWED_TABLES = {
        'sessions', 'chat_history', 'user_responses', 'risk_detections', 
        'analytics', 'session_summaries', 'intent_classifications', 'system_logs'
    }
    
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: {table}")
    
    # Validate column names against known schema
    if not all(isinstance(key, str) and key.replace('_', '').isalnum() for key in data.keys()):
        raise ValueError("Invalid column names detected")
    
    columns = ', '.join(f'"{key}"' for key in data.keys())  # Quote column names
    placeholders = ', '.join('?' * len(data))
    
    # Use parameterized query with quoted identifiers
    query = f'INSERT INTO "{table}" ({columns}) VALUES ({placeholders})'
    conn.execute(query, tuple(data.values()))
```

**Why this works:**
- Whitelist validation prevents arbitrary table access
- Column name sanitization prevents injection via column names
- Quoted identifiers prevent SQL injection in identifiers
- Parameterized values remain secure

### 2. Subprocess Command Injection in Risk Detector

**File:** `nlp/risk_detector.py:8-14`  
**Risk Level:** CRITICAL  
**Impact:** Remote code execution, system compromise

#### Current Problem
```python
try:
    nlp = spacy.load('en_core_web_sm')
except:
    # Fallback if model not installed
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load('en_core_web_sm')
```

**Issues:**
- Arbitrary subprocess execution in production code
- No error handling for subprocess failure
- Will fail in containerized/restricted environments

#### Solution
```python
import spacy
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

def load_spacy_model():
    """Safely load spaCy model with proper error handling."""
    try:
        return spacy.load('en_core_web_sm')
    except OSError as e:
        logger.error(
            f"spaCy model 'en_core_web_sm' not found. "
            f"Please install it manually: python -m spacy download en_core_web_sm"
        )
        
        # Check if we're in a development environment
        if os.getenv('FLASK_ENV') == 'development':
            logger.info("Development environment detected, attempting auto-download...")
            try:
                import subprocess
                result = subprocess.run(
                    ["python", "-m", "spacy", "download", "en_core_web_sm"],
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                    check=True
                )
                logger.info("Model downloaded successfully")
                return spacy.load('en_core_web_sm')
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as download_error:
                logger.error(f"Failed to download model: {download_error}")
                raise RuntimeError("spaCy model unavailable and download failed") from e
        else:
            raise RuntimeError(
                "spaCy model not available in production environment. "
                "Please ensure 'en_core_web_sm' is installed in the container image."
            ) from e

# Use the safe loader
try:
    nlp = load_spacy_model()
except RuntimeError:
    # Fallback: create a minimal NLP pipeline or disable risk detection
    logger.critical("Risk detection disabled due to missing spaCy model")
    nlp = None
```

### 3. Insecure CORS Configuration

**File:** `app.py:64`  
**Risk Level:** HIGH  
**Impact:** Cross-origin attacks, data theft, CSRF bypass

#### Current Problem
```python
CORS(app, resources={r"/api/*": {"origins": "*"}})
```

#### Solution
```python
# In config/settings.py - add CORS configuration
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Development frontend
    "http://127.0.0.1:3000",
    "https://yourdomain.com",  # Production domain
    # Add specific trusted origins only
]

if os.getenv('FLASK_ENV') == 'development':
    ALLOWED_ORIGINS.extend([
        "http://localhost:8080",
        "http://127.0.0.1:8080"
    ])

# In app.py - secure CORS setup
CORS(app, 
     resources={
         r"/api/*": {
             "origins": ALLOWED_ORIGINS,
             "methods": ["GET", "POST"],
             "allow_headers": ["Content-Type", "Authorization"],
             "supports_credentials": True,
             "max_age": 86400  # Cache preflight for 24 hours
         }
     },
     vary_header=True
)
```

### 4. Missing CSRF Protection

**File:** `app.py` (entire application)  
**Risk Level:** HIGH  
**Impact:** Cross-site request forgery attacks

#### Solution
```python
# Add to requirements.txt
# Flask-WTF==1.1.1

# In app.py - add CSRF protection
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.secret_key = SECRET_KEY or 'dev-key-for-development-only'

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Configure CSRF
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
app.config['WTF_CSRF_SSL_STRICT'] = FLASK_ENV == 'production'

# Add CSRF token to all responses
@app.after_request
def inject_csrf_token(response):
    if request.endpoint and not request.endpoint.startswith('static'):
        # Add CSRF token to JSON responses
        if response.content_type and 'application/json' in response.content_type:
            try:
                from flask_wtf.csrf import generate_csrf
                data = response.get_json()
                if data and isinstance(data, dict):
                    data['csrf_token'] = generate_csrf()
                    response.data = json.dumps(data)
            except Exception:
                pass  # Don't break response if CSRF injection fails
    return response
```

---

## ⚡ ARCHITECTURAL PROBLEMS (High Priority)

### 5. Misleading File Names and Intent Classification Logic

**File:** `nlp/intent_distilbert.py`  
**Risk Level:** MEDIUM  
**Impact:** Maintenance confusion, incorrect model expectations

#### Current Problem
The file is named `intent_distilbert.py` but implements RoBERTa zero-shot classification, creating confusion for developers and potentially incorrect performance expectations.

#### Solution

**Step 1: Rename and restructure files**
```bash
# Rename the file to reflect actual implementation
mv nlp/intent_distilbert.py nlp/intent_classifier.py
```

**Step 2: Create proper abstraction** 
Create `nlp/intent_classifier.py`:
```python
"""
Intent Classification Module - Multi-Model Support
Supports both DistilBERT fine-tuned and RoBERTa zero-shot approaches
"""

import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class IntentClassifier(ABC):
    """Abstract base class for intent classifiers."""
    
    @abstractmethod
    def classify(self, text: str, current_step: Optional[str] = None) -> Dict[str, Any]:
        """Classify intent of given text."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if classifier is ready for use."""
        pass

class HybridIntentClassifier:
    """
    Hybrid intent classifier that tries multiple approaches in order of preference:
    1. Fine-tuned DistilBERT (if available)
    2. RoBERTa zero-shot (if available)  
    3. Rule-based fallback (always available)
    """
    
    def __init__(self):
        self.classifiers = []
        self._initialize_classifiers()
    
    def _initialize_classifiers(self):
        """Initialize available classifiers in priority order."""
        
        # Try to load fine-tuned DistilBERT
        try:
            from .distilbert_classifier import DistilBERTClassifier
            distilbert = DistilBERTClassifier()
            if distilbert.is_available():
                self.classifiers.append(('distilbert', distilbert))
                logger.info("DistilBERT classifier loaded successfully")
        except Exception as e:
            logger.warning(f"DistilBERT classifier not available: {e}")
        
        # Try to load RoBERTa zero-shot
        try:
            from .roberta_zeroshot import RoBERTaZeroShotClassifier
            roberta = RoBERTaZeroShotClassifier()
            if roberta.is_available():
                self.classifiers.append(('roberta_zeroshot', roberta))
                logger.info("RoBERTa zero-shot classifier loaded successfully")
        except Exception as e:
            logger.warning(f"RoBERTa zero-shot classifier not available: {e}")
        
        # Always add rule-based fallback
        try:
            from fallbacks.rule_based_intent import RuleBasedClassifier
            rule_based = RuleBasedClassifier()
            self.classifiers.append(('rule_based', rule_based))
            logger.info("Rule-based classifier loaded as fallback")
        except Exception as e:
            logger.error(f"Critical: Even rule-based classifier failed: {e}")
    
    def classify(self, text: str, current_step: Optional[str] = None) -> Dict[str, Any]:
        """Classify using the best available classifier."""
        
        if not text or not text.strip():
            return {'label': 'unclear', 'confidence': 0.0, 'method': 'empty_input'}
        
        for classifier_name, classifier in self.classifiers:
            try:
                result = classifier.classify(text, current_step)
                result['method'] = classifier_name
                
                # If confidence is high enough, return result
                confidence_threshold = 0.7 if classifier_name == 'rule_based' else 0.4
                if result.get('confidence', 0) >= confidence_threshold:
                    return result
                    
                # For ML models, if confidence is low, try next classifier
                if classifier_name in ['distilbert', 'roberta_zeroshot']:
                    logger.debug(f"{classifier_name} confidence too low ({result.get('confidence')}), trying next")
                    continue
                else:
                    # Rule-based is last fallback, return regardless of confidence
                    return result
                    
            except Exception as e:
                logger.error(f"Classifier {classifier_name} failed: {e}")
                continue
        
        # If all classifiers failed
        return {'label': 'unclear', 'confidence': 0.0, 'method': 'all_failed'}

# Global instance
_intent_classifier = HybridIntentClassifier()

def classify_intent(text: str, current_step: Optional[str] = None) -> Dict[str, Any]:
    """Main function for intent classification - used by router."""
    return _intent_classifier.classify(text, current_step)
```

### 6. Database Connection Resource Management

**File:** `app.py:88-97`  
**Risk Level:** HIGH  
**Impact:** Resource exhaustion, connection leaks, poor performance

#### Current Problem
```python
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(str(DATABASE_PATH))
        g.db.row_factory = sqlite3.Row
    return g.db
```

**Issues:**
- No connection timeout settings
- No connection pooling  
- No retry logic for connection failures
- No monitoring of connection health

#### Solution

**Step 1: Create connection pool manager**
Create `database/connection_pool.py`:
```python
"""
Database Connection Pool Manager
Provides efficient, thread-safe database connections with proper resource management.
"""

import sqlite3
import threading
import time
import logging
from contextlib import contextmanager
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ConnectionConfig:
    database_path: Path
    max_connections: int = 20
    connection_timeout: int = 30
    busy_timeout: int = 30000  # 30 seconds in milliseconds
    check_same_thread: bool = False
    enable_wal: bool = True

class DatabaseConnectionPool:
    """Thread-safe SQLite connection pool with health monitoring."""
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self._pool = []
        self._pool_lock = threading.RLock()
        self._created_connections = 0
        self._last_health_check = 0
        
        # Create initial connections
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Create initial pool of connections."""
        try:
            # Create a test connection to validate database
            test_conn = self._create_connection()
            test_conn.execute("SELECT 1")
            test_conn.close()
            
            logger.info(f"Database connection pool initialized for {self.config.database_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with proper settings."""
        conn = sqlite3.connect(
            str(self.config.database_path),
            timeout=self.config.connection_timeout,
            check_same_thread=self.config.check_same_thread
        )
        
        # Set row factory for dict-like access
        conn.row_factory = sqlite3.Row
        
        # Configure SQLite settings
        conn.execute(f"PRAGMA busy_timeout = {self.config.busy_timeout}")
        conn.execute("PRAGMA foreign_keys = ON")
        
        if self.config.enable_wal:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
        
        # Enable connection health monitoring
        conn.execute("PRAGMA optimize")
        
        return conn
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool with automatic cleanup."""
        conn = None
        try:
            with self._pool_lock:
                if self._pool:
                    conn = self._pool.pop()
                elif self._created_connections < self.config.max_connections:
                    conn = self._create_connection()
                    self._created_connections += 1
                else:
                    # Pool exhausted, wait briefly and try again
                    pass
            
            if not conn:
                # Create temporary connection if pool is exhausted
                logger.warning("Connection pool exhausted, creating temporary connection")
                conn = self._create_connection()
            
            # Health check on retrieved connection
            if not self._is_connection_healthy(conn):
                conn.close()
                conn = self._create_connection()
            
            yield conn
            conn.commit()
            
        except sqlite3.Error:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self._return_connection(conn)
    
    def _is_connection_healthy(self, conn: sqlite3.Connection) -> bool:
        """Check if connection is still healthy."""
        try:
            conn.execute("SELECT 1").fetchone()
            return True
        except sqlite3.Error:
            return False
    
    def _return_connection(self, conn: sqlite3.Connection):
        """Return connection to pool if healthy, otherwise close it."""
        try:
            if self._is_connection_healthy(conn):
                with self._pool_lock:
                    if len(self._pool) < self.config.max_connections:
                        self._pool.append(conn)
                        return
            
            # Connection unhealthy or pool full
            conn.close()
            with self._pool_lock:
                self._created_connections -= 1
                
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
            try:
                conn.close()
            except:
                pass

# Global connection pool
_connection_pool: Optional[DatabaseConnectionPool] = None
_pool_lock = threading.Lock()

def initialize_connection_pool(database_path: Path, **kwargs) -> None:
    """Initialize the global connection pool."""
    global _connection_pool
    
    with _pool_lock:
        if _connection_pool is None:
            config = ConnectionConfig(database_path=database_path, **kwargs)
            _connection_pool = DatabaseConnectionPool(config)

def get_db_connection():
    """Get a database connection from the pool."""
    if _connection_pool is None:
        raise RuntimeError("Connection pool not initialized")
    
    return _connection_pool.get_connection()
```

**Step 2: Update app.py to use connection pool**
```python
# In app.py - replace get_db function

from database.connection_pool import initialize_connection_pool, get_db_connection

# Initialize connection pool on startup
try:
    initialize_connection_pool(
        DATABASE_PATH,
        max_connections=20,
        connection_timeout=30,
        enable_wal=True
    )
    logger.info("Database connection pool initialized")
except Exception as e:
    logger.error(f"Failed to initialize connection pool: {e}")
    raise

# Replace the get_db function
def get_db():
    """Get database connection from pool."""
    return get_db_connection()

# Update teardown handler
@app.teardown_appcontext
def close_db(e=None):
    # Connection pool handles cleanup automatically
    pass
```

### 7. Silent Failure Patterns in Router

**File:** `core/router.py:16-26`  
**Risk Level:** HIGH  
**Impact:** Silent data loss, debugging difficulties, false success indicators

#### Current Problem
```python
try:
    from database.repository_v2 import save_message, save_analytics_event, update_session_state
    DB_AVAILABLE = True
except ImportError:
    logger.warning("Database repository_v2 not found. Chat history will not be saved.")
    DB_AVAILABLE = False
    # Create dummy functions so the app doesn't crash
    def save_message(session_id, role, message): pass
    def save_analytics_event(event_type, event_data): pass
    def update_session_state(session_id, state): pass
```

#### Solution
```python
"""
Improved error handling with proper fallback strategies and monitoring.
"""

import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"

@dataclass
class ServiceHealth:
    status: ServiceStatus
    error_message: Optional[str] = None
    fallback_active: bool = False

class DatabaseService:
    """Database service with proper error handling and fallback."""
    
    def __init__(self):
        self.status = ServiceStatus.UNAVAILABLE
        self.error_count = 0
        self.last_error = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize database service with proper error handling."""
        try:
            from database.repository_v2 import (
                save_message as _save_message,
                save_analytics_event as _save_analytics_event,
                update_session_state as _update_session_state
            )
            
            self._save_message_impl = _save_message
            self._save_analytics_impl = _save_analytics_event
            self._update_session_impl = _update_session_state
            
            # Test database connection
            from database.connection_pool import get_db_connection
            with get_db_connection() as conn:
                conn.execute("SELECT 1")
            
            self.status = ServiceStatus.AVAILABLE
            logger.info("Database service initialized successfully")
            
        except ImportError as e:
            self.status = ServiceStatus.UNAVAILABLE
            self.last_error = f"Database module not found: {e}"
            logger.error(self.last_error)
            self._setup_fallback_implementations()
            
        except Exception as e:
            self.status = ServiceStatus.DEGRADED
            self.last_error = f"Database connection failed: {e}"
            logger.error(self.last_error)
            self._setup_fallback_implementations()
    
    def _setup_fallback_implementations(self):
        """Setup fallback implementations that properly handle failures."""
        
        def _fallback_save_message(session_id: str, role: str, message: str):
            self.error_count += 1
            logger.warning(
                f"Database unavailable - message not saved: "
                f"session={session_id}, role={role}, message_length={len(message)}"
            )
            # Could implement file-based logging here as fallback
            self._log_to_fallback_storage({
                'type': 'message',
                'session_id': session_id,
                'role': role,
                'message': message[:100] + '...' if len(message) > 100 else message
            })
        
        def _fallback_save_analytics(event_type: str, event_data: Optional[Dict] = None):
            self.error_count += 1
            logger.warning(f"Database unavailable - analytics not saved: {event_type}")
            self._log_to_fallback_storage({
                'type': 'analytics',
                'event_type': event_type,
                'event_data': event_data
            })
        
        def _fallback_update_session(session_id: str, state: str):
            self.error_count += 1
            logger.warning(
                f"Database unavailable - session state not updated: "
                f"session={session_id}, state={state}"
            )
            self._log_to_fallback_storage({
                'type': 'session_state',
                'session_id': session_id,
                'state': state
            })
        
        self._save_message_impl = _fallback_save_message
        self._save_analytics_impl = _fallback_save_analytics
        self._update_session_impl = _fallback_update_session
    
    def _log_to_fallback_storage(self, data: Dict[str, Any]):
        """Log failed database operations to fallback storage."""
        try:
            import json
            from datetime import datetime
            
            fallback_log = {
                'timestamp': datetime.utcnow().isoformat(),
                'data': data,
                'error_count': self.error_count
            }
            
            # Could write to file, send to external logging service, etc.
            logger.info(f"Fallback storage: {json.dumps(fallback_log)}")
            
        except Exception as e:
            logger.error(f"Fallback storage also failed: {e}")
    
    def save_message(self, session_id: str, role: str, message: str):
        """Save message with proper error handling."""
        try:
            self._save_message_impl(session_id, role, message)
            # Reset error count on success
            if self.error_count > 0:
                logger.info("Database service recovered")
                self.error_count = 0
                
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            logger.error(f"Failed to save message: {e}")
            
            # Switch to fallback if too many errors
            if self.error_count > 5:
                logger.error("Too many database errors, switching to fallback mode")
                self.status = ServiceStatus.DEGRADED
                self._setup_fallback_implementations()
    
    def save_analytics_event(self, event_type: str, event_data: Optional[Dict] = None):
        """Save analytics with proper error handling."""
        try:
            self._save_analytics_impl(event_type, event_data)
        except Exception as e:
            self.error_count += 1
            logger.error(f"Failed to save analytics: {e}")
    
    def update_session_state(self, session_id: str, state: str):
        """Update session state with proper error handling."""
        try:
            self._update_session_impl(session_id, state)
        except Exception as e:
            self.error_count += 1
            logger.error(f"Failed to update session state: {e}")
    
    def get_health(self) -> ServiceHealth:
        """Get current service health status."""
        return ServiceHealth(
            status=self.status,
            error_message=self.last_error,
            fallback_active=(self.status != ServiceStatus.AVAILABLE)
        )

# Global database service instance
_database_service = DatabaseService()

# Export functions for backward compatibility
def save_message(session_id: str, role: str, message: str):
    """Save chat message."""
    return _database_service.save_message(session_id, role, message)

def save_analytics_event(event_type: str, event_data: Optional[Dict] = None):
    """Save analytics event."""
    return _database_service.save_analytics_event(event_type, event_data)

def update_session_state(session_id: str, state: str):
    """Update session FSM state."""
    return _database_service.update_session_state(session_id, state)

def get_database_health() -> ServiceHealth:
    """Get database service health for monitoring."""
    return _database_service.get_health()

# Add health check endpoint to app.py
@app.route("/health/detailed")
def detailed_health_check():
    """Detailed health check including service status."""
    from core.router import get_database_health
    
    db_health = get_database_health()
    
    health_data = {
        "status": "healthy" if db_health.status == ServiceStatus.AVAILABLE else "degraded",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "services": {
            "database": {
                "status": db_health.status.value,
                "error_message": db_health.error_message,
                "fallback_active": db_health.fallback_active
            }
        }
    }
    
    status_code = 200 if db_health.status == ServiceStatus.AVAILABLE else 503
    return jsonify(health_data), status_code
```

---

## ⚡ PERFORMANCE ISSUES (Medium Priority)

### 8. Inefficient Model Loading and Caching

**File:** `nlp/intent_distilbert.py`  
**Risk Level:** MEDIUM  
**Impact:** High latency, resource waste, poor user experience

#### Current Problem
- Models loaded on every import without lazy loading
- No caching of inference results
- Thread locks create bottlenecks
- No warmup strategy for cold starts

#### Solution

Create `nlp/model_manager.py`:
```python
"""
Centralized ML Model Manager with caching and performance optimization.
"""

import threading
import time
import logging
from typing import Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from functools import lru_cache
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    model_type: str
    cache_size: int = 1000
    cache_ttl_seconds: int = 300  # 5 minutes
    warmup_samples: Optional[list] = None
    preload: bool = True

class CacheEntry:
    def __init__(self, result: Any, timestamp: float):
        self.result = result
        self.timestamp = timestamp

class ModelManager:
    """Thread-safe model manager with intelligent caching."""
    
    def __init__(self):
        self._models = {}
        self._model_locks = {}
        self._inference_cache = {}
        self._cache_locks = {}
        self._global_lock = threading.RLock()
        
    def register_model(self, name: str, loader_func: Callable, config: ModelConfig):
        """Register a model with its loader function."""
        with self._global_lock:
            self._models[name] = {
                'loader': loader_func,
                'config': config,
                'instance': None,
                'loaded': False,
                'load_time': None,
                'error': None
            }
            self._model_locks[name] = threading.RLock()
            self._cache_locks[name] = threading.RLock()
            self._inference_cache[name] = {}
            
            if config.preload:
                # Schedule preloading in background
                threading.Thread(
                    target=self._preload_model,
                    args=(name,),
                    daemon=True
                ).start()
    
    def _preload_model(self, name: str):
        """Preload model in background thread."""
        try:
            self.get_model(name)
            logger.info(f"Model {name} preloaded successfully")
        except Exception as e:
            logger.error(f"Failed to preload model {name}: {e}")
    
    def get_model(self, name: str):
        """Get model instance, loading if necessary."""
        if name not in self._models:
            raise ValueError(f"Model {name} not registered")
        
        model_info = self._models[name]
        
        # Fast path: model already loaded
        if model_info['loaded'] and model_info['instance'] is not None:
            return model_info['instance']
        
        # Slow path: need to load model
        with self._model_locks[name]:
            # Double-check pattern
            if model_info['loaded'] and model_info['instance'] is not None:
                return model_info['instance']
            
            try:
                logger.info(f"Loading model {name}...")
                start_time = time.time()
                
                model_info['instance'] = model_info['loader']()
                
                load_time = time.time() - start_time
                model_info['load_time'] = load_time
                model_info['loaded'] = True
                model_info['error'] = None
                
                logger.info(f"Model {name} loaded in {load_time:.2f}s")
                
                # Run warmup if configured
                self._warmup_model(name, model_info['instance'], model_info['config'])
                
                return model_info['instance']
                
            except Exception as e:
                model_info['error'] = str(e)
                model_info['loaded'] = False
                logger.error(f"Failed to load model {name}: {e}")
                raise
    
    def _warmup_model(self, name: str, model_instance, config: ModelConfig):
        """Run warmup inference to prime the model."""
        if not config.warmup_samples:
            return
            
        try:
            logger.info(f"Warming up model {name}...")
            for sample in config.warmup_samples:
                if hasattr(model_instance, 'classify'):
                    model_instance.classify(sample)
                elif hasattr(model_instance, 'predict'):
                    model_instance.predict(sample)
            logger.info(f"Model {name} warmed up successfully")
        except Exception as e:
            logger.warning(f"Model warmup failed for {name}: {e}")
    
    def cached_inference(self, model_name: str, method_name: str, cache_key: str, 
                        inference_func: Callable) -> Any:
        """Perform cached inference with TTL."""
        
        config = self._models[model_name]['config']
        cache = self._inference_cache[model_name]
        
        with self._cache_locks[model_name]:
            # Check cache first
            if cache_key in cache:
                entry = cache[cache_key]
                if time.time() - entry.timestamp < config.cache_ttl_seconds:
                    return entry.result
                else:
                    # Expired entry
                    del cache[cache_key]
            
            # Cache miss - run inference
            result = inference_func()
            
            # Store in cache with size limit
            if len(cache) >= config.cache_size:
                # Remove oldest entries (simple FIFO)
                oldest_key = min(cache.keys(), key=lambda k: cache[k].timestamp)
                del cache[oldest_key]
            
            cache[cache_key] = CacheEntry(result, time.time())
            return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = {}
        
        with self._global_lock:
            for name, info in self._models.items():
                cache_size = len(self._inference_cache[name])
                stats[name] = {
                    'loaded': info['loaded'],
                    'load_time': info['load_time'],
                    'error': info['error'],
                    'cache_size': cache_size,
                    'cache_limit': info['config'].cache_size
                }
        
        return stats
    
    def clear_cache(self, model_name: Optional[str] = None):
        """Clear inference cache for specific model or all models."""
        if model_name:
            with self._cache_locks[model_name]:
                self._inference_cache[model_name].clear()
        else:
            with self._global_lock:
                for name in self._models.keys():
                    with self._cache_locks[name]:
                        self._inference_cache[name].clear()

# Global model manager
model_manager = ModelManager()

def create_cache_key(text: str, **kwargs) -> str:
    """Create cache key from input parameters."""
    # Create deterministic hash from inputs
    key_data = f"{text}:{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
    return hashlib.md5(key_data.encode()).hexdigest()
```

**Updated classifier using model manager:**
```python
# In nlp/intent_classifier.py

from .model_manager import model_manager, ModelConfig, create_cache_key

def _load_roberta_classifier():
    """Loader function for RoBERTa classifier."""
    from .roberta_zeroshot import RoBERTaZeroShotClassifier
    return RoBERTaZeroShotClassifier()

# Register models on import
model_manager.register_model(
    'roberta_zeroshot',
    _load_roberta_classifier,
    ModelConfig(
        model_type='roberta_zeroshot',
        cache_size=1000,
        cache_ttl_seconds=300,
        warmup_samples=['hello', 'I need help', 'goodbye'],
        preload=True
    )
)

def classify_intent_cached(text: str, current_step: Optional[str] = None) -> Dict[str, Any]:
    """Cached intent classification with performance optimization."""
    
    if not text or not text.strip():
        return {'label': 'unclear', 'confidence': 0.0, 'method': 'empty_input'}
    
    # Create cache key
    cache_key = create_cache_key(text, current_step=current_step)
    
    def _run_inference():
        try:
            classifier = model_manager.get_model('roberta_zeroshot')
            result = classifier.classify(text, current_step)
            result['cached'] = False
            return result
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return {'label': 'unclear', 'confidence': 0.0, 'method': 'error'}
    
    # Use cached inference
    result = model_manager.cached_inference(
        'roberta_zeroshot',
        'classify',
        cache_key,
        _run_inference
    )
    
    # Mark if result came from cache
    if 'cached' not in result:
        result['cached'] = True
    
    return result
```

### 9. Database Query Optimization

**File:** `database/repository_v2.py`  
**Risk Level:** MEDIUM  
**Impact:** Slow response times, high CPU usage, poor scalability

#### Current Problem
Multiple separate database calls without batching, missing indexes, N+1 query patterns.

#### Solution

**Step 1: Add proper database indexes**
Create `database/indexes_v2.sql`:
```sql
-- Performance indexes for common queries
-- Add these to your schema_v2.sql or run separately

-- Session lookups (most common operation)
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_sessions_fsm_state ON sessions(fsm_state);

-- Chat history queries
CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_ts ON chat_history(ts DESC);
CREATE INDEX IF NOT EXISTS idx_chat_history_session_ts ON chat_history(session_id, ts DESC);

-- User responses for FSM state reconstruction  
CREATE INDEX IF NOT EXISTS idx_user_responses_session_id ON user_responses(session_id);
CREATE INDEX IF NOT EXISTS idx_user_responses_step ON user_responses(step);

-- Analytics queries
CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON analytics(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics(timestamp DESC);

-- Risk detection queries
CREATE INDEX IF NOT EXISTS idx_risk_detections_session_id ON risk_detections(session_id);
CREATE INDEX IF NOT EXISTS idx_risk_detections_detected_at ON risk_detections(detected_at DESC);

-- Intent classification performance tracking
CREATE INDEX IF NOT EXISTS idx_intent_classifications_session_id ON intent_classifications(session_id);
CREATE INDEX IF NOT EXISTS idx_intent_classifications_method ON intent_classifications(method);
CREATE INDEX IF NOT EXISTS idx_intent_classifications_confidence ON intent_classifications(confidence);

-- System logs for debugging
CREATE INDEX IF NOT EXISTS idx_system_logs_component ON system_logs(component);
CREATE INDEX IF NOT EXISTS idx_system_logs_log_level ON system_logs(log_level);
CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp DESC);
```

**Step 2: Batch operations for better performance**
Add to `database/repository_v2.py`:
```python
def bulk_save_chat_turn(session_id: str, user_message: str, bot_response: str, 
                       debug_info: Optional[Dict] = None):
    """Save complete chat turn in single transaction."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # All operations in single transaction
        cursor.execute(
            'INSERT OR IGNORE INTO sessions (session_id) VALUES (?)',
            (session_id,)
        )
        
        cursor.execute(
            'INSERT INTO chat_history (session_id, role, message) VALUES (?, ?, ?)',
            (session_id, 'user', user_message)
        )
        
        cursor.execute(
            'INSERT INTO chat_history (session_id, role, message) VALUES (?, ?, ?)',
            (session_id, 'bot', bot_response)
        )
        
        cursor.execute(
            'UPDATE sessions SET last_activity = CURRENT_TIMESTAMP WHERE session_id = ?',
            (session_id,)
        )
        
        if debug_info:
            cursor.execute(
                'INSERT INTO analytics (event_type, event_data) VALUES (?, ?)',
                ('chat_turn_completed', json.dumps({
                    'session_id': session_id,
                    'debug_info': debug_info
                }))
            )

def get_session_context(session_id: str) -> Dict[str, Any]:
    """Get complete session context in single query."""
    with get_db_connection() as conn:
        # Use JOIN to get all session data efficiently  
        result = conn.execute("""
            SELECT 
                s.session_id,
                s.fsm_state,
                s.created_at,
                s.last_activity,
                s.completed,
                -- Get latest messages
                (SELECT json_group_array(
                    json_object(
                        'role', ch.role,
                        'message', ch.message,
                        'timestamp', ch.ts
                    )
                ) FROM (
                    SELECT role, message, ts 
                    FROM chat_history 
                    WHERE session_id = s.session_id 
                    ORDER BY ts DESC 
                    LIMIT 10
                ) ch) as recent_messages,
                -- Get user responses
                (SELECT json_group_object(ur.step, ur.response)
                 FROM user_responses ur 
                 WHERE ur.session_id = s.session_id
                 AND ur.response IS NOT NULL) as user_responses
            FROM sessions s
            WHERE s.session_id = ?
        """, (session_id,)).fetchone()
        
        if result:
            session_data = dict(result)
            
            # Parse JSON fields
            session_data['recent_messages'] = json.loads(session_data['recent_messages'] or '[]')
            session_data['user_responses'] = json.loads(session_data['user_responses'] or '{}')
            
            return session_data
        
        return {}

def get_analytics_dashboard_data(days: int = 7) -> Dict[str, Any]:
    """Get comprehensive analytics in single query."""
    with get_db_connection() as conn:
        # Complex analytics query optimized for performance
        result = conn.execute("""
            WITH daily_stats AS (
                SELECT 
                    date(timestamp) as day,
                    event_type,
                    COUNT(*) as event_count
                FROM analytics 
                WHERE timestamp > datetime('now', printf('-%d days', ?))
                GROUP BY date(timestamp), event_type
            ),
            session_stats AS (
                SELECT 
                    date(created_at) as day,
                    COUNT(*) as total_sessions,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed_sessions,
                    AVG(CASE 
                        WHEN completion_time IS NOT NULL 
                        THEN (julianday(completion_time) - julianday(created_at)) * 24 * 60 
                        ELSE NULL 
                    END) as avg_session_duration_minutes
                FROM sessions
                WHERE created_at > datetime('now', printf('-%d days', ?))
                GROUP BY date(created_at)
            )
            SELECT 
                json_object(
                    'daily_events', (
                        SELECT json_group_object(
                            day || '_' || event_type,
                            event_count
                        ) FROM daily_stats
                    ),
                    'session_metrics', (
                        SELECT json_group_array(
                            json_object(
                                'day', day,
                                'total_sessions', total_sessions,
                                'completed_sessions', completed_sessions,
                                'completion_rate', 
                                ROUND(100.0 * completed_sessions / total_sessions, 2),
                                'avg_duration_minutes', 
                                ROUND(avg_session_duration_minutes, 2)
                            )
                        ) FROM session_stats
                    )
                ) as dashboard_data
        """, (days, days)).fetchone()
        
        if result:
            return json.loads(result[0])
        
        return {}
```

---

## 🧹 CODE QUALITY ISSUES (Lower Priority)

### 10. Global Warning Suppression

**File:** `nlp/intent_distilbert.py:29`  
**Risk Level:** LOW  
**Impact:** Hidden legitimate warnings, debugging difficulties

#### Current Problem
```python
warnings.filterwarnings('ignore')
```

#### Solution
```python
# Replace global suppression with specific suppression
import warnings

# Suppress only specific known warnings
warnings.filterwarnings('ignore', category=FutureWarning, module='transformers')
warnings.filterwarnings('ignore', message='.*resume_download.*', module='transformers')
warnings.filterwarnings('ignore', category=UserWarning, message='.*TypedStorage.*')

# Keep other warnings visible for debugging
```

---

## 📋 IMPLEMENTATION ROADMAP

### Phase 1: Critical Security Fixes (Week 1)
1. **SQL Injection Fix** - Implement table/column validation
2. **CSRF Protection** - Add Flask-WTF and token validation  
3. **CORS Security** - Configure specific allowed origins
4. **Subprocess Security** - Replace with safe model loading

### Phase 2: Architectural Improvements (Week 2-3)
1. **Connection Pool** - Implement database connection pooling
2. **Error Handling** - Replace silent failures with proper monitoring
3. **Model Management** - Add caching and performance optimization
4. **File Restructure** - Fix misleading file names and create proper abstractions

### Phase 3: Performance Optimization (Week 4)
1. **Database Indexes** - Add performance indexes
2. **Query Optimization** - Implement batch operations
3. **Caching Strategy** - Add intelligent caching layers
4. **Background Processing** - Move heavy operations to background threads

### Phase 4: Code Quality & Monitoring (Week 5)
1. **Comprehensive Testing** - Add missing test coverage
2. **Monitoring Dashboard** - Implement health checks and metrics
3. **Documentation** - Update all misleading documentation
4. **Configuration Management** - Centralize all configuration

### Testing Strategy for Each Phase

```python
# Example comprehensive test for critical security fixes
class TestSecurityFixes(unittest.TestCase):
    
    def test_sql_injection_prevention(self):
        """Test that SQL injection attempts are blocked."""
        from database.repository_v2 import insert_record
        
        # Test table name injection
        with self.assertRaises(ValueError):
            conn = get_test_db_connection()
            insert_record(conn, "users; DROP TABLE sessions; --", {"name": "test"})
        
        # Test column name injection  
        with self.assertRaises(ValueError):
            conn = get_test_db_connection()
            insert_record(conn, "sessions", {"name; DROP TABLE --": "test"})
    
    def test_csrf_protection_active(self):
        """Test that CSRF protection is active."""
        response = self.client.post('/chat', 
                                  json={'message': 'test'},
                                  headers={'Content-Type': 'application/json'})
        self.assertEqual(response.status_code, 400)  # Should reject without CSRF token
    
    def test_cors_restrictions(self):
        """Test that CORS properly restricts origins."""
        response = self.client.post('/chat',
                                  json={'message': 'test'},
                                  headers={'Origin': 'http://malicious-site.com'})
        self.assertNotIn('Access-Control-Allow-Origin', response.headers)
```

### Monitoring and Alerting

```python
# Health check endpoints for monitoring
@app.route("/metrics")
def metrics():
    """Prometheus-style metrics endpoint."""
    from core.router import get_database_health
    from nlp.model_manager import model_manager
    
    db_health = get_database_health()
    model_stats = model_manager.get_stats()
    
    metrics = []
    
    # Database metrics
    metrics.append(f'database_status{{status="{db_health.status.value}"}} 1')
    metrics.append(f'database_errors_total {getattr(db_health, "error_count", 0)}')
    
    # Model metrics
    for model_name, stats in model_stats.items():
        metrics.append(f'model_loaded{{model="{model_name}"}} {int(stats["loaded"])}')
        metrics.append(f'model_cache_size{{model="{model_name}"}} {stats["cache_size"]}')
        if stats["load_time"]:
            metrics.append(f'model_load_time_seconds{{model="{model_name}"}} {stats["load_time"]}')
    
    return '\n'.join(metrics), 200, {'Content-Type': 'text/plain'}
```

This comprehensive remediation guide provides concrete solutions for all identified issues. Each fix includes detailed code examples, explanations of why the solution works, and proper testing strategies. Implementation should follow the phased approach to ensure system stability while addressing the most critical security vulnerabilities first.