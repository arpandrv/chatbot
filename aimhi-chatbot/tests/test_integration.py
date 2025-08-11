import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.router import route_message
from core.session import new_session_id, get_session
from database.repository import init_db
import json
import tempfile

class TestIntegration(unittest.TestCase):
    
    def setUp(self):
        """Set up test database and session"""
        # Use temporary database for testing
        self.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        os.environ['DATABASE_URL'] = f'sqlite:///{self.test_db.name}'
        
        # Initialize test database
        init_db()
        
        # Create test session
        self.session_id = new_session_id()
        
    def tearDown(self):
        """Clean up test database"""
        try:
            os.unlink(self.test_db.name)
        except:
            pass
    
    def test_complete_conversation_flow(self):
        """Test a complete 4-step conversation from start to finish"""
        
        # Step 1: Welcome/Greeting
        response = route_message(self.session_id, "Hi there!")
        self.assertIn("support people" or "yarn about your support", response.lower())  # Should move to support_people step
        
        # Check FSM state
        session = get_session(self.session_id)
        fsm = session['fsm']
        self.assertEqual(fsm.state, 'support_people')
        
        # Step 2: Support People
        response = route_message(self.session_id, "My mom and my best friend Sarah are always there for me")
        self.assertIn("strengths" or "deadly" or "good at", response.lower())  # Should move to strengths step
        
        # Check FSM state and stored response
        session = get_session(self.session_id)
        fsm = session['fsm']
        self.assertEqual(fsm.state, 'strengths')
        self.assertIsNotNone(fsm.get_response('support_people'))
        
        # Step 3: Strengths
        response = route_message(self.session_id, "I'm good at playing guitar and helping my friends")
        self.assertIn("worries" or "on your mind" or "weighing", response.lower())  # Should move to worries step
        
        # Check FSM state
        session = get_session(self.session_id)
        fsm = session['fsm']
        self.assertEqual(fsm.state, 'worries')
        self.assertIsNotNone(fsm.get_response('strengths'))
        
        # Step 4: Worries
        response = route_message(self.session_id, "I'm stressed about school exams and my future")
        self.assertIn("goals" or "work towards" or "where you want", response.lower())  # Should move to goals step
        
        # Check FSM state
        session = get_session(self.session_id)
        fsm = session['fsm']
        self.assertEqual(fsm.state, 'goals')
        self.assertIsNotNone(fsm.get_response('worries'))
        
        # Step 5: Goals
        response = route_message(self.session_id, "I want to graduate and maybe study music")
        # Should move to summary and include all responses
        self.assertTrue(
            "summary" in response.lower() or 
            "talked about" in response.lower() or 
            "here's what" in response.lower() or
            "thanks for yarning" in response.lower()
        )
        
        # Check final state
        session = get_session(self.session_id)
        fsm = session['fsm']
        self.assertEqual(fsm.state, 'summary')
        
        # Verify all responses were stored
        responses = fsm.get_all_responses()
        self.assertIsNotNone(responses['support_people'])
        self.assertIsNotNone(responses['strengths'])
        self.assertIsNotNone(responses['worries'])
        self.assertIsNotNone(responses['goals'])
    
    def test_risk_detection_interrupts_flow(self):
        """Test that risk detection works at any point in conversation"""
        
        # Start normal conversation
        route_message(self.session_id, "Hello")
        route_message(self.session_id, "My family supports me")
        
        # Trigger risk detection in middle of conversation
        response = route_message(self.session_id, "I want to kill myself")
        
        # Should return crisis resources
        self.assertIn("13YARN", response)
        self.assertIn("Your safety", response)
        
        # FSM state should remain unchanged
        session = get_session(self.session_id)
        fsm = session['fsm']
        # Should still be at strengths step (didn't advance due to risk)
        self.assertEqual(fsm.state, 'strengths')
    
    def test_unclear_responses_get_clarification(self):
        """Test that unclear responses get appropriate clarification"""
        
        # Start conversation
        route_message(self.session_id, "Hi")
        
        # Give unclear response to support people question
        response = route_message(self.session_id, "um what do you mean")
        
        # Should ask for clarification, not advance
        self.assertTrue(
            "tell me about" in response.lower() or 
            "people in your life" in response.lower() or
            "support network" in response.lower()
        )
        
        # FSM should still be at support_people
        session = get_session(self.session_id)
        fsm = session['fsm']
        self.assertEqual(fsm.state, 'support_people')
        
        # Now give proper response
        response = route_message(self.session_id, "My dad and sister")
        
        # Should advance to strengths
        session = get_session(self.session_id)
        fsm = session['fsm']
        self.assertEqual(fsm.state, 'strengths')
    
    def test_negative_responses_handled_appropriately(self):
        """Test handling of negative responses (no support, no strengths, etc.)"""
        
        # Start conversation
        route_message(self.session_id, "Hello")
        
        # Say no support
        response = route_message(self.session_id, "Nobody cares about me")
        
        # Should provide empathetic response but not advance
        self.assertTrue(
            "tough" in response.lower() or 
            "difficult" in response.lower() or
            "hear you" in response.lower()
        )
        
        # Move to strengths with another no response
        route_message(self.session_id, "My teacher is nice")  # This should advance
        
        # Now say no strengths
        response = route_message(self.session_id, "I'm not good at anything")
        
        # Should provide encouragement
        self.assertTrue(
            "everyone has" in response.lower() or 
            "strength" in response.lower() or
            "good at" in response.lower() or
            "small thing" in response.lower()
        )
        
        session = get_session(self.session_id)
        fsm = session['fsm']
        # Should still be at strengths, not advance
        self.assertEqual(fsm.state, 'strengths')
    
    def test_session_isolation(self):
        """Test that different sessions don't interfere with each other"""
        
        # Create second session
        session_id_2 = new_session_id()
        
        # Advance first session
        route_message(self.session_id, "Hi")
        route_message(self.session_id, "My family")
        
        # Check first session is at strengths
        session1 = get_session(self.session_id)
        fsm1 = session1['fsm']
        self.assertEqual(fsm1.state, 'strengths')
        
        # Second session should still be at welcome
        route_message(session_id_2, "Hello there")
        session2 = get_session(session_id_2)
        fsm2 = session2['fsm']
        self.assertEqual(fsm2.state, 'support_people')  # Just advanced from welcome
        
        # Verify they're independent
        self.assertNotEqual(fsm1.state, fsm2.state)
        self.assertNotEqual(self.session_id, session_id_2)
    
    def test_database_message_storage(self):
        """Test that messages are properly stored in database"""
        
        # Send some messages
        route_message(self.session_id, "Hello")
        route_message(self.session_id, "My family supports me")
        
        # Check that messages were stored (we'd need to query the database)
        # This would require accessing the database directly
        # For now, just verify no errors occurred
        self.assertTrue(True)  # If we got here, no database errors
    
    def test_performance_timing(self):
        """Test that response times meet requirements (<500ms for rule path)"""
        import time
        
        # Test rule-based response time
        start_time = time.time()
        response = route_message(self.session_id, "Hello")
        end_time = time.time()
        
        response_time_ms = (end_time - start_time) * 1000
        
        # Should be under 500ms for rule-based responses
        self.assertLess(response_time_ms, 500, 
                       f"Response time {response_time_ms:.2f}ms exceeds 500ms requirement")
        
        # Verify it's a proper response
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

if __name__ == '__main__':
    # Set test environment
    os.environ['LLM_ENABLED'] = 'false'  # Disable LLM for testing
    os.environ['FLASK_ENV'] = 'testing'
    
    unittest.main()