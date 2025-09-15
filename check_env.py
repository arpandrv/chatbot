#!/usr/bin/env python3
"""
Environment Variables Checker for Render Deployment
Loads and logs all required environment variables to verify configuration
"""

import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_env_vars():
    """Load and log all environment variables"""

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

    logger.info("=" * 60)
    logger.info("ENVIRONMENT VARIABLES CHECK")
    logger.info("=" * 60)

    missing_vars = []
    secret_vars = ['SECRET_KEY', 'SUPABASE_SERVICE_ROLE_KEY', 'SUPABASE_JWT_SECRET', 'HF_TOKEN', 'LLM_API_KEY']

    for var in env_vars:
        value = os.getenv(var)
        if value is None:
            logger.warning(f"❌ {var}: NOT SET")
            missing_vars.append(var)
        else:
            if var in secret_vars:
                # Mask sensitive values
                masked_value = value[:8] + "*" * (len(value) - 16) + value[-8:] if len(value) > 16 else "*" * len(value)
                logger.info(f"✅ {var}: {masked_value}")
            else:
                logger.info(f"✅ {var}: {value}")

    logger.info("=" * 60)

    if missing_vars:
        logger.error(f"❌ MISSING VARIABLES ({len(missing_vars)}): {', '.join(missing_vars)}")
        return False
    else:
        logger.info(f"✅ ALL VARIABLES SET ({len(env_vars)} total)")
        return True

if __name__ == "__main__":
    success = check_env_vars()
    exit(0 if success else 1)