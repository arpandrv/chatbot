"""Deployment regressions; no external services or credentials required."""
import importlib
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from check_env import check_env_vars


class DeploymentTests(unittest.TestCase):
    def test_only_required_settings_are_required(self):
        names = ['SECRET_KEY', 'CORS_ORIGINS', 'SUPABASE_URL', 'SUPABASE_ANON_KEY',
                 'SUPABASE_SERVICE_ROLE_KEY', 'LLM_MODEL', 'LLM_API_KEY',
                 'LLM_SYSTEM_PROMPT_RISK', 'LLM_HANDOFF_SYSTEM_PROMPT']
        with patch.dict(os.environ, dict.fromkeys(names, 'configured'), clear=True):
            self.assertTrue(check_env_vars())
            os.environ['LLM_API_KEY'] = ''
            self.assertFalse(check_env_vars())
            os.environ.update(LLM_PROVIDER='ollama', OLLAMA_API_BASE='http://ollama:11434')
            self.assertTrue(check_env_vars())

    def test_authentication_and_production_pages(self):
        settings = {'FLASK_ENV': 'production', 'SECRET_KEY': 'test-only',
                    'CORS_ORIGINS': 'https://chatbot.arpanlabs.com',
                    'RATE_LIMIT_STORAGE': 'memory://'}
        with patch.dict(os.environ, settings), patch('config.supabase_client.test_connection', return_value=True):
            module = importlib.import_module('app')
        module.app.config['TESTING'] = True
        client = module.app.test_client()
        self.assertEqual(client.get('/healthz').status_code, 200)
        self.assertEqual(client.get('/auth/me').status_code, 401)
        fake = Mock()
        fake.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id='user-123'))
        headers = {'Authorization': 'Bearer verified-by-supabase'}
        with patch('config.auth_middleware.supabase_anon', fake):
            response = client.get('/auth/me', headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json['user_id'], 'user-123')
            fake.auth.get_user.assert_called_with('verified-by-supabase')
            with patch('app.get_user_sessions', side_effect=RuntimeError('database unavailable')):
                # Endpoint errors must not be mislabeled as authentication failures.
                with self.assertRaises(RuntimeError):
                    client.get('/sessions', headers=headers)
            fake.auth.get_user.side_effect = ValueError('invalid token')
            self.assertEqual(client.get('/auth/me', headers=headers).status_code, 401)
            with patch.dict(os.environ, {'FLASK_ENV': 'development'}):
                self.assertEqual(client.get('/auth/me', headers=headers).status_code, 401)
        for path in ['/', '/chat']:
            response = client.get(path)
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertNotIn('onclick=', html)
            self.assertNotIn('<script>', html)
            self.assertIn("style-src 'self' 'unsafe-inline'", response.headers['Content-Security-Policy'])


if __name__ == '__main__':
    unittest.main()
