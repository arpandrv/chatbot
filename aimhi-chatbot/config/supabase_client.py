"""
Supabase Client Configuration
============================
Environment-driven initialization for Supabase clients. No hardcoded secrets.
"""

import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

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
except Exception:
    supabase_service = None  # type: ignore

try:
    supabase_anon: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)        # client-side
except Exception:
    supabase_anon = None  # type: ignore



def test_connection() -> bool:
    """Test Supabase connection"""
    try:
        if supabase_service is None:
            print("Supabase service client not initialized. Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars.")
            return False
        # Try to query the sessions table (will fail if schema not set up)
        supabase_service.table('sessions').select('count').limit(1).execute()
        print("Supabase connection successful")
        return True
    except Exception as e:
        print(f"Supabase connection failed: {e}")
        print("Ensure environment variables are set and run database/schema.sql in the Supabase SQL Editor.")
        return False


if __name__ == "__main__":
    test_connection()
