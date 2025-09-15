"""
Supabase Client Configuration
============================
Environment-driven initialization for Supabase clients. No hardcoded secrets.
"""

import os
import logging
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Supabase Configuration (from environment)
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
# JWT secret used to validate Supabase-issued JWTs
JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET')

# Direct PostgreSQL connections are not used in this app; all access goes through Supabase clients.

# Create Supabase clients (guarded to avoid import-time failures)
try:
    supabase_service: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)  # server-side
except Exception as e:
    logger.warning("Supabase service client not initialized: %s", e)
    supabase_service = None  # type: ignore

try:
    supabase_anon: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)        # client-side
except Exception as e:
    logger.warning("Supabase anon client not initialized: %s", e)
    supabase_anon = None  # type: ignore



def test_connection() -> bool:
    """Test Supabase connection"""
    try:
        if supabase_service is None:
            logger.error("Supabase service client not initialized. Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars.")
            return False
        # Try to query the sessions table (will fail if schema not set up)
        supabase_service.table('sessions').select('count').limit(1).execute()
        logger.info("Supabase connection successful")
        return True
    except Exception as e:
        logger.error("Supabase connection failed: %s", e)
        logger.error("Ensure environment variables are set and run database/schema.sql in the Supabase SQL Editor.")
        return False


if __name__ == "__main__":
    test_connection()
