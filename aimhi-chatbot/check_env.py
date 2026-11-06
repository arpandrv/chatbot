"""Validate required deployment settings without printing credentials."""
import os


def check_env_vars():
    required = ['SECRET_KEY', 'CORS_ORIGINS', 'SUPABASE_URL', 'SUPABASE_ANON_KEY',
                'SUPABASE_SERVICE_ROLE_KEY', 'LLM_MODEL', 'LLM_SYSTEM_PROMPT_RISK',
                'LLM_HANDOFF_SYSTEM_PROMPT']
    provider = os.getenv('LLM_PROVIDER', 'openai')
    if provider == 'openai':
        required.append('LLM_API_KEY')
    elif provider == 'ollama':
        required.append('OLLAMA_API_BASE')
    else:
        print('LLM_PROVIDER must be openai or ollama')
        return False
    missing = [name for name in required if not os.getenv(name, '').strip()]
    if missing:
        print('Missing required settings: ' + ', '.join(missing))
        return False
    print('Required deployment settings are configured')
    return True


if __name__ == '__main__':
    raise SystemExit(0 if check_env_vars() else 1)
