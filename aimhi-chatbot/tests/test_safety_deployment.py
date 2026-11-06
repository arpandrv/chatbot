import os
import unittest
from unittest.mock import patch

os.environ.setdefault('LLM_SYSTEM_PROMPT_RISK', 'test classifier')
from nlp.risk_detector import parse_json_response
from core.router import route_message


class SafetyTests(unittest.TestCase):
    def test_invalid_output_is_not_no_risk(self):
        for output in ['not json', '{}', '{"label":"safe"}']:
            with self.assertRaises(ValueError):
                parse_json_response(output)
        self.assertEqual(parse_json_response('{"label":"no_risk"}')['label'], 'no_risk')

    def test_safety_paths_do_not_advance_or_generate(self):
        for label in ['risk', 'unavailable']:
            with self.subTest(label=label), patch('core.router._detect_risk_flag', return_value={
                'risk_detected': label == 'risk', 'risk_details': {'label': label}
            }), patch('core.router.record_risk_detection'), patch('core.router.get_fsm_state') as state:
                result = route_message('test-user', 'test-session', 'test message')
                state.assert_not_called()
                self.assertEqual(result['debug']['response_source'], 'safety')
                self.assertEqual(result['debug']['risk_detected'], label == 'risk')


if __name__ == '__main__':
    unittest.main()
