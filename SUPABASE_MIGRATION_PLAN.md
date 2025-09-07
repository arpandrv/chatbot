# Supabase Migration Plan - AIMhi-Y Chatbot
**Version:** 1.0  
**Date:** 2025-01-07  
**Status:** Planning Phase

## Executive Summary
This document outlines the complete migration strategy from SQLite to Supabase for the AIMhi-Y Supportive Yarn Chatbot. The migration will dramatically simplify database operations, improve scalability, and reduce maintenance overhead while preserving all existing functionality.

**Expected Benefits:**
- **~400+ lines of database code reduction** (90%+ reduction)
- **Zero database maintenance** (managed by Supabase)
- **Built-in real-time capabilities** for future features
- **Automatic scaling** and connection management
- **Enhanced security** with Row Level Security (RLS)

---

## Current Architecture Analysis

### Database Components to Migrate

#### 1. **app.py - Connection Management** (Lines 119-208, ~90 lines)
```python
# CURRENT: Complex SQLite connection pooling
_pool: LifoQueue[sqlite3.Connection] = LifoQueue(maxsize=POOL_SIZE)
@contextmanager
def get_db(): # ~70 lines of connection pool logic

# TARGET: Simple Supabase client
from supabase import create_client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
```

#### 2. **database/repository_v2.py** (371 lines → ~50 lines, 87% reduction)
- **Current:** Complex transaction management, SQL queries, error handling
- **Target:** Simple Supabase client method calls

#### 3. **Database Schema** (8 tables, 157 lines SQL)
- **sessions** - User session state management
- **chat_history** - Message storage with CASCADE deletes
- **user_responses** - FSM step responses with UNIQUE constraints
- **risk_detections** - Crisis intervention logging
- **analytics** - Event tracking for insights
- **session_summaries** - Conversation summaries
- **intent_classifications** - NLP model results tracking
- **system_logs** - Application logging

#### 4. **router.py - Database Calls** (Moderate changes)
- `save_message()`, `save_analytics_event()`, `update_session_state()`
- **Current:** Function calls to repository layer
- **Target:** Direct Supabase client calls

---

## Supabase Architecture Design

### Database Setup

#### Schema Migration Strategy
```sql
-- 1. Create tables in Supabase dashboard or via migration
-- 2. Enable Row Level Security (RLS) for data privacy
-- 3. Set up automatic backups and point-in-time recovery
-- 4. Configure database webhooks for real-time features (future)
```

#### Environment Variables
```bash
# New variables to add to .env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-key  # For server-side operations
DATABASE_PROVIDER=supabase  # Feature flag for migration
```

### Code Architecture Changes

#### 1. **Supabase Client Initialization**
```python
# config/supabase.py (NEW FILE)
from supabase import create_client, Client
import os

def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Use service role for server
    if not url or not key:
        raise ValueError("Supabase credentials not configured")
    return create_client(url, key)

# Global client instance
supabase = get_supabase_client()
```

#### 2. **Repository Pattern Simplification**
```python
# Old: Complex transaction management
@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        # 20+ lines of setup, transaction handling
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# New: Simple client calls
def save_message(session_id: str, role: str, message: str):
    return supabase.table('chat_history').insert({
        'session_id': session_id,
        'role': role, 
        'message': message
    }).execute()
```

---

## Migration Strategy

### Phase 1: Preparation (Day 1-2)
1. **Supabase Project Setup**
   - Create new Supabase project
   - Configure authentication (if needed for admin features)
   - Set up development and production environments

2. **Schema Migration**
   - Import existing schema to Supabase
   - Configure Row Level Security policies
   - Set up proper indexes for query performance
   - Test schema with sample data

3. **Environment Setup**
   - Add Supabase credentials to environment variables
   - Install Supabase Python client: `pip install supabase`
   - Create feature flag for gradual migration

### Phase 2: Code Preparation (Day 3-4)
1. **Create Supabase Wrapper Layer**
   - `config/supabase.py` - Client initialization
   - `database/supabase_repository.py` - New repository implementation
   - Maintain same function signatures for drop-in replacement

2. **Implement Feature Flag System**
   ```python
   # Allow toggling between SQLite and Supabase
   DB_PROVIDER = os.getenv('DATABASE_PROVIDER', 'sqlite')  # 'sqlite' or 'supabase'
   
   if DB_PROVIDER == 'supabase':
       from database.supabase_repository import *
   else:
       from database.repository_v2 import *
   ```

### Phase 3: Implementation (Day 5-7)
1. **Replace Repository Functions**
   - Convert each function from `repository_v2.py` to Supabase equivalent
   - Maintain identical return types and error handling patterns
   - Add proper logging and error recovery

2. **Update Application Layer**
   - Remove SQLite connection pooling from `app.py`
   - Simplify error handling (no more transaction rollbacks)
   - Update health check to test Supabase connectivity

3. **Testing Phase**
   - Unit tests for each repository function
   - Integration tests for full chat workflows
   - Performance testing to ensure <500ms response times
   - Data consistency verification

### Phase 4: Deployment & Cleanup (Day 8-10)
1. **Production Migration**
   - Deploy with feature flag to production
   - Monitor for errors and performance issues
   - Gradually migrate existing sessions (if any)

2. **Cleanup**
   - Remove SQLite-specific code after successful migration
   - Delete unused database files and schema
   - Update documentation and deployment instructions

---

## Detailed Code Changes

### 1. app.py Changes
```python
# REMOVE: Lines 119-208 (Connection Pool Management)
# - _pool: LifoQueue[sqlite3.Connection]
# - _create_db_connection()
# - _get_conn()
# - _return_conn()
# - get_db() context manager
# - _close_pool()
# - atexit.register(_close_pool)

# ADD: Simple Supabase client import
from config.supabase import supabase

# MODIFY: Health check to test Supabase connectivity
@app.route("/health")
def health_check():
    try:
        # Simple connectivity test
        response = supabase.table('sessions').select('count').limit(1).execute()
        return jsonify({"status": "ok", "database": "connected"}), 200
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return jsonify({"status": "error", "database": "disconnected"}), 503
```

### 2. database/supabase_repository.py (NEW FILE)
```python
"""
Supabase repository implementation - replaces repository_v2.py complexity
"""
from config.supabase import supabase
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Session Management (5 lines vs 45 lines in SQLite version)
def create_session(session_id: str, fsm_state: str = 'welcome'):
    return supabase.table('sessions').upsert({
        'session_id': session_id, 
        'fsm_state': fsm_state
    }).execute()

def get_session_data(session_id: str) -> Optional[Dict[str, Any]]:
    response = supabase.table('sessions').select('*').eq('session_id', session_id).execute()
    return response.data[0] if response.data else None

def update_session_state(session_id: str, fsm_state: str):
    return supabase.table('sessions').update({
        'fsm_state': fsm_state,
        'last_activity': 'now()'
    }).eq('session_id', session_id).execute()

# Chat History (3 lines vs 20+ lines)
def save_message(session_id: str, role: str, message: str):
    return supabase.table('chat_history').insert({
        'session_id': session_id,
        'role': role,
        'message': message
    }).execute()

def get_history(session_id: str, limit: int = 6) -> List[Dict]:
    response = supabase.table('chat_history')\
        .select('role, message')\
        .eq('session_id', session_id)\
        .order('ts', desc=True)\
        .limit(limit)\
        .execute()
    return response.data

# Analytics (1 line vs 10+ lines)
def save_analytics_event(event_type: str, event_data: Optional[Dict] = None):
    return supabase.table('analytics').insert({
        'event_type': event_type,
        'event_data': event_data
    }).execute()

# Additional functions follow same pattern...
```

### 3. router.py Changes
```python
# MINIMAL CHANGES - just import source
# OLD:
from database.repository_v2 import save_message, save_analytics_event, update_session_state

# NEW:
if os.getenv('DATABASE_PROVIDER') == 'supabase':
    from database.supabase_repository import save_message, save_analytics_event, update_session_state
else:
    from database.repository_v2 import save_message, save_analytics_event, update_session_state

# All function calls remain identical - no changes needed to router logic
```

---

## Testing Strategy

### 1. Unit Tests
```python
# tests/test_supabase_repository.py
def test_create_session():
    session_id = str(uuid.uuid4())
    create_session(session_id, 'welcome')
    session = get_session_data(session_id)
    assert session['fsm_state'] == 'welcome'

def test_save_and_retrieve_message():
    session_id = str(uuid.uuid4())
    save_message(session_id, 'user', 'Hello')
    history = get_history(session_id, 1)
    assert len(history) == 1
    assert history[0]['message'] == 'Hello'
```

### 2. Integration Tests
```python
# tests/test_full_chat_flow.py
def test_complete_chat_session():
    """Test full FSM flow with Supabase backend"""
    # Create session, advance through all FSM states
    # Verify data persistence at each step
    # Test risk detection and analytics events
```

### 3. Performance Tests
```python
# tests/test_performance.py
def test_response_time_under_500ms():
    """Ensure Supabase calls don't slow down chat responses"""
    # Measure end-to-end response times
    # Target: <500ms for FSM-driven responses
```

---

## Risk Assessment & Mitigation

### High Risk Items
1. **Data Loss During Migration**
   - **Mitigation:** Comprehensive backup of SQLite data before migration
   - **Testing:** Dry run migration with production data copy

2. **Supabase Service Downtime**
   - **Mitigation:** Implement circuit breaker pattern with fallback responses
   - **Monitoring:** Health checks and alerting for database connectivity

3. **Performance Regression**
   - **Mitigation:** Load testing before production deployment
   - **Rollback:** Keep SQLite code available via feature flag

### Medium Risk Items
1. **Authentication/Authorization Issues**
   - **Mitigation:** Use service role key for server-side operations
   - **Testing:** Verify all operations work correctly with chosen auth method

2. **Schema Incompatibilities**
   - **Mitigation:** Careful schema mapping and validation
   - **Testing:** Data type compatibility verification

---

## Deployment Plan

### Development Environment
1. Set `DATABASE_PROVIDER=supabase` in development `.env`
2. Test all chat flows with Supabase backend
3. Verify data persistence and analytics collection
4. Performance testing with realistic data volumes

### Staging Environment
1. Deploy with feature flag defaulting to SQLite
2. Manual testing of Supabase mode
3. Load testing to verify performance requirements
4. Data migration dry run if migrating existing data

### Production Deployment
1. **Phase 1:** Deploy with `DATABASE_PROVIDER=sqlite` (no change)
2. **Phase 2:** Switch to `DATABASE_PROVIDER=supabase` after validation
3. **Phase 3:** Remove SQLite code after 1 week of stable operation

### Rollback Plan
```python
# Emergency rollback via environment variable
DATABASE_PROVIDER=sqlite  # Switch back to SQLite immediately
# Keep SQLite files until migration is confirmed successful
```

---

## Timeline & Dependencies

### Week 1: Setup & Development
- **Day 1-2:** Supabase project setup, schema migration
- **Day 3-4:** Code implementation, repository replacement
- **Day 5-6:** Testing, debugging, performance optimization
- **Day 7:** Final integration testing

### Week 2: Deployment & Validation
- **Day 8-9:** Staging deployment, user acceptance testing
- **Day 10:** Production deployment with monitoring
- **Day 11-14:** Monitoring period, cleanup, documentation

### Dependencies
- **External:** Supabase service availability and performance
- **Internal:** No other features depend on this migration
- **Blocking:** Must complete before implementing real-time features

---

## Success Metrics

### Technical Metrics
- **Code Reduction:** >85% reduction in database-related code
- **Response Time:** Maintain <500ms chat response times
- **Reliability:** >99.9% uptime (measured via health checks)
- **Performance:** No degradation in concurrent user handling

### Operational Metrics
- **Deployment Time:** <2 hours for full migration
- **Rollback Time:** <15 minutes if issues arise
- **Maintenance Effort:** Eliminate database administration tasks

### Quality Metrics
- **Test Coverage:** >95% for all new Supabase repository functions
- **Zero Data Loss:** Complete data integrity during migration
- **Feature Parity:** All existing functionality preserved

---

## Post-Migration Benefits

### Immediate Benefits
- **Simplified Codebase:** Easier maintenance and onboarding
- **Reduced Infrastructure:** No SQLite file management
- **Better Monitoring:** Supabase dashboard for insights
- **Automatic Scaling:** Handle traffic spikes without configuration

### Future Opportunities
- **Real-time Features:** Live chat status, typing indicators
- **Advanced Analytics:** Built-in analytics and custom queries
- **API Generation:** Auto-generated REST and GraphQL endpoints
- **Edge Functions:** Server-side logic closer to users
- **Multi-region:** Global deployment with data residency

---

## Appendix

### A. Environment Variables Reference
```bash
# Required for Supabase migration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DATABASE_PROVIDER=supabase  # 'sqlite' or 'supabase'

# Optional optimization
SUPABASE_TIMEOUT=10  # Connection timeout in seconds
SUPABASE_MAX_RETRIES=3  # Retry failed requests
```

### B. Supabase Schema Export
```sql
-- Use this for creating tables in Supabase dashboard
-- (Copy of schema_v2.sql adapted for PostgreSQL)
-- Available in separate file: supabase_schema.sql
```

### C. Migration Checklist
- [ ] Supabase project created and configured
- [ ] Schema migrated and tested
- [ ] Environment variables configured
- [ ] Supabase repository implemented
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Performance benchmarks met
- [ ] Staging deployment successful
- [ ] Production deployment planned
- [ ] Rollback procedure documented
- [ ] Team trained on new architecture

---

**Document Owner:** Development Team  
**Review Date:** Every sprint during migration  
**Next Review:** Post-migration retrospective