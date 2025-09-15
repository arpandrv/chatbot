#!/usr/bin/env python3
"""
Environment Variables Checker for Render Deployment
Loads and prints all required environment variables to verify configuration
"""

import os
from pathlib import Path

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Look for .env in current directory and aimhi-chatbot subdirectory
    env_paths = [
        Path('.env'),
        Path('aimhi-chatbot/.env'),
        Path('./.env'),
        Path('./aimhi-chatbot/.env')
    ]

    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded environment from: {env_path}")
            break
    else:
        print("No .env file found, using system environment variables only")

except ImportError:
    print("python-dotenv not installed, using system environment variables only")

def check_env_vars():
    """Load and print all environment variables"""

    env_vars = [
        # Flask Configuration
        'FLASK_ENV',
        'SECRET_KEY',
        'CORS_ORIGINS',
        'PORT',
        'LOG_LEVEL',
        'RATE_LIMIT_STORAGE',
        'RATE_LIMIT_DAY',
        'RATE_LIMIT_HOUR',
        'WEB_CONCURRENCY',
        'GUNICORN_CMD_ARGS',

        # Supabase Configuration
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY',
        'SUPABASE_SERVICE_ROLE_KEY',
        'SUPABASE_JWT_SECRET',
        'SUPABASE_TIMEOUT',
        'SUPABASE_RETRY_ATTEMPTS',

        # Hugging Face
        'HF_TOKEN',

        # LLM Configuration
        'LLM_PROVIDER',
        'LLM_API_KEY',
        'LLM_MODEL',
        'LLM_API_BASE',
        'OLLAMA_API_BASE',
        'LLM_MAX_TOKENS',

        # Risk Detection LLM
        'LLM_TIMEOUT_RISK',
        'LLM_TEMPERATURE_RISK',
        'LLM_SYSTEM_PROMPT_RISK',

        # Intent Classification LLM
        'LLM_TIMEOUT_INTENT',
        'LLM_TEMPERATURE_INTENT',
        'LLM_SYSTEM_PROMPT_INTENT',

        # Sentiment Analysis LLM
        'LLM_TIMEOUT_SENTIMENT',
        'LLM_TEMPERATURE_SENTIMENT',
        'LLM_SYSTEM_PROMPT_SENTIMENT',

        # Handoff LLM
        'LLM_TIMEOUT_HANDOFF',
        'LLM_TEMPERATURE_HANDOFF',
        'LLM_HANDOFF_SYSTEM_PROMPT',

        # NLP Thresholds and URLs
        'INTENT_CONFIDENCE_THRESHOLD',
        'HF_INTENT_API_URL',
        'SENTIMENT_CONFIDENCE_THRESHOLD',
        'HF_SENTIMENT_API_URL',
        'RISK_CONFIDENCE_THRESHOLD',
        'HF_RISK_API_URL'
    ]

    print("=" * 60)
    print("ENVIRONMENT VARIABLES CHECK")
    print("=" * 60)

    missing_vars = []
    secret_vars = ['SECRET_KEY', 'SUPABASE_SERVICE_ROLE_KEY', 'SUPABASE_JWT_SECRET', 'HF_TOKEN', 'LLM_API_KEY']

    for var in env_vars:
        value = os.getenv(var)
        if value is None:
            print(f"[NOT SET] {var}: NOT SET")
            missing_vars.append(var)
        else:
            if var in secret_vars:
                # Mask sensitive values
                masked_value = value[:8] + "*" * (len(value) - 16) + value[-8:] if len(value) > 16 else "*" * len(value)
                print(f"[OK] {var}: {masked_value}")
            else:
                print(f"[OK] {var}: {value}")

    print("=" * 60)

    if missing_vars:
        print(f"[ERROR] MISSING VARIABLES ({len(missing_vars)}): {', '.join(missing_vars)}")
        return False
    else:
        print(f"[SUCCESS] ALL VARIABLES SET ({len(env_vars)} total)")
        return True

if __name__ == "__main__":
    success = check_env_vars()
    exit(0 if success else 1)