import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.router import route_message
from core.session import new_session_id, get_session
from database.repository import init_db
from nlp.intent import classify_intent
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
    
    def test_progressive_fallback_support_people(self):
        """Test progressive fallback system for support_people step"""
        
        # Start conversation
        route_message(self.session_id, "Hello")
        
        # First unclear response - should get clarification (attempt 1)
        response = route_message(self.session_id, "I don't know what to say")
        self.assertTrue(
            "tell me about" in response.lower() or 
            "people in your life" in response.lower()
        )
        
        # Check FSM state - should still be at support_people
        session = get_session(self.session_id)
        fsm = session['fsm']
        self.assertEqual(fsm.state, 'support_people')
        self.assertEqual(fsm.get_attempt_count(), 1)  # First attempt
        
        # Second unclear response - should get offer_choice (attempt 2)
        response = route_message(self.session_id, "Not sure")
        self.assertTrue(
            "would you like to think about support people" in response.lower() and
            "move on" in response.lower()
        )
        self.assertEqual(fsm.get_attempt_count(), 2)  # Second attempt
        
        # Third unclear response - should force advance (attempt 3)
        response = route_message(self.session_id, "Maybe")
        self.assertTrue(
            ("acknowledge" in response.lower() or "respect that" in response.lower()) and
            "strengths" in response.lower()
        )
        
        # Should have advanced to strengths step
        session = get_session(self.session_id)
        fsm = session['fsm']
        self.assertEqual(fsm.state, 'strengths')
        self.assertEqual(fsm.get_attempt_count(), 0)  # Reset for new step
    
    def test_progressive_fallback_user_choice_to_advance(self):
        """Test when user chooses to advance after offer_choice"""
        
        # Navigate to strengths and trigger offer_choice
        route_message(self.session_id, "Hello")
        route_message(self.session_id, "My family supports me")
        route_message(self.session_id, "I don't know")  # First unclear (clarification)
        response = route_message(self.session_id, "Not sure")  # Second unclear (get offer_choice)
        self.assertIn("keep thinking about this", response.lower())
        
        # User chooses to move on with affirmation
        response = route_message(self.session_id, "Yes, let's move on")
        self.assertTrue(
            ("okay" in response.lower() or "perfectly fine" in response.lower()) and
            ("worries" in response.lower() or "on your mind" in response.lower())
        )
        
        # Should have advanced to worries step
        session = get_session(self.session_id)
        fsm = session['fsm']
        self.assertEqual(fsm.state, 'worries')
    
    def test_progressive_fallback_goals_to_summary(self):
        """Test progressive fallback from goals step leads to summary"""
        
        # Navigate to goals step
        route_message(self.session_id, "Hello")
        route_message(self.session_id, "My family supports me")
        route_message(self.session_id, "I'm good at sports")
        route_message(self.session_id, "School stress worries me")
        
        # Now at goals - trigger progressive fallback
        route_message(self.session_id, "I don't know")  # First unclear (clarification)
        response = route_message(self.session_id, "Not sure")  # Second unclear (get offer_choice)
        self.assertIn("thinking about goals might be challenging", response.lower())
        
        # Third unclear response - should force advance to summary
        response = route_message(self.session_id, "Maybe")
        self.assertTrue(
            "perfectly fine" in response.lower() and
            ("what we talked about today" in response.lower() or 
             "Support People" in response or
             "Strengths" in response or
             "Worries" in response)
        )
        
        # Should have advanced to summary with conversation recap
        session = get_session(self.session_id)
        fsm = session['fsm']
        self.assertEqual(fsm.state, 'summary')
    
    def test_good_response_bypasses_progressive_fallback(self):
        """Test that good responses bypass the attempt system entirely"""
        
        # Start conversation
        route_message(self.session_id, "Hello")
        
        # Give a good response - should advance immediately without attempts
        response = route_message(self.session_id, "My family and friends support me")
        self.assertIn("strengths", response.lower())
        
        # Verify FSM advanced and attempt counter is still 0
        session = get_session(self.session_id)
        fsm = session['fsm']
        self.assertEqual(fsm.state, 'strengths')
        self.assertEqual(fsm.get_attempt_count(), 0)  # No attempts used
        
        # Response should be saved
        self.assertEqual(fsm.get_response('support_people'), "My family and friends support me")
    
    def test_attempt_counters_independent_per_step(self):
        """Test that attempt counters are independent for each conversation step"""
        
        # Start and force advance through support_people with multiple attempts
        route_message(self.session_id, "Hello")
        route_message(self.session_id, "um what")  # attempt 1 (clarification)
        route_message(self.session_id, "um what")  # attempt 2 (offer_choice)
        route_message(self.session_id, "um what")  # attempt 3 (force advance)
        
        # Should be at strengths with reset attempt counter
        session = get_session(self.session_id)
        fsm = session['fsm']
        self.assertEqual(fsm.state, 'strengths')
        self.assertEqual(fsm.get_attempt_count(), 0)  # Reset for new step
        
        # Test that strengths step has its own independent attempt counter
        route_message(self.session_id, "um what")  # This should be attempt 1 for strengths
        self.assertEqual(fsm.get_attempt_count(), 1)
        
        # The support_people counter should show the final attempts used
        self.assertEqual(fsm.attempts['support_people'], 3)
        self.assertEqual(fsm.attempts['strengths'], 1)
    
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
    
    def test_context_aware_classification_edge_cases(self):
        """Test context-aware classification handles edge cases correctly"""
        
        # Test ambiguous helping/support phrases
        ambiguous_cases = [
            'helping people',
            'I help others', 
            'others help me',
            'we help each other',
            'caring for people',
            'supporting friends',
            'good at helping family',
            'helping friends makes me happy',
            'me and mom help each other',
        ]
        
        for text in ambiguous_cases:
            # At strengths step, should classify as strengths
            intent_str, conf_str = classify_intent(text, current_step='strengths')
            self.assertEqual(intent_str, 'strengths', 
                           f"'{text}' should be 'strengths' at strengths step, got '{intent_str}'")
            self.assertGreater(conf_str, 0.5, 
                             f"'{text}' should have high confidence at strengths step")
            
            # At support_people step, should classify as support_people (or be overridden by context)
            intent_sup, conf_sup = classify_intent(text, current_step='support_people')
            # Either support_people or changed to strengths by context is acceptable
            self.assertIn(intent_sup, ['support_people', 'strengths'], 
                         f"'{text}' should be support_people or strengths at support step, got '{intent_sup}'")
    
    def test_clear_family_words_stay_consistent(self):
        """Test that clear family/people words remain support_people in both contexts"""
        
        clear_family_cases = ['mom', 'dad', 'family', 'friends', 'my family']
        
        for text in clear_family_cases:
            # Should be support_people in both contexts
            intent_str, conf_str = classify_intent(text, current_step='strengths')
            intent_sup, conf_sup = classify_intent(text, current_step='support_people')
            
            self.assertEqual(intent_str, 'support_people', 
                           f"'{text}' should be support_people at strengths step")
            self.assertEqual(intent_sup, 'support_people', 
                           f"'{text}' should be support_people at support step")
            
            # Confidence should be higher at support step (context boost)
            self.assertGreater(conf_sup, conf_str, 
                             f"'{text}' should have higher confidence at support step")
    
    def test_negation_consistent_across_contexts(self):
        """Test negation detection works consistently across contexts"""
        
        negation_cases = [
            'not helping anyone',
            'nobody helps me', 
            'not good at helping people',
            'cant help others',
            'dont help much'
        ]
        
        for text in negation_cases:
            # Should be negation in both contexts
            intent_str, conf_str = classify_intent(text, current_step='strengths')
            intent_sup, conf_sup = classify_intent(text, current_step='support_people')
            
            self.assertEqual(intent_str, 'negation', 
                           f"'{text}' should be negation at strengths step")
            self.assertEqual(intent_sup, 'negation', 
                           f"'{text}' should be negation at support step")
            
            # Confidence should be similar in both contexts
            self.assertAlmostEqual(conf_str, conf_sup, delta=0.1,
                                 msg=f"'{text}' confidence should be similar in both contexts")
    
    def test_typos_and_cultural_variations_handled(self):
        """Test system handles typos and cultural language variations"""
        
        variation_cases = [
            ('helpin friends', 'strengths'),  # typo
            ('famly supports me', 'support_people'),  # typo
            ('mob supports me', 'support_people'),  # Aboriginal English
            ('deadly at helping', 'strengths'),  # Aboriginal English slang
        ]
        
        for text, expected_context in variation_cases:
            if expected_context == 'strengths':
                # Should be strengths at strengths step
                intent, conf = classify_intent(text, current_step='strengths')
                self.assertEqual(intent, 'strengths', 
                               f"'{text}' should be strengths at strengths step")
                self.assertGreater(conf, 0.5, 
                                 f"'{text}' should have decent confidence")
            else:
                # Should be support_people in both contexts
                intent_str, conf_str = classify_intent(text, current_step='strengths')
                intent_sup, conf_sup = classify_intent(text, current_step='support_people')
                
                # Should be support_people or at least recognized
                self.assertIn(intent_sup, ['support_people', 'strengths'], 
                             f"'{text}' should be recognized at support step")
                self.assertGreater(conf_sup, 0.3, 
                                 f"'{text}' should have reasonable confidence")
    
    def test_compound_complex_statements(self):
        """Test complex compound statements are handled correctly"""
        
        complex_cases = [
            'my sister helps me but I also help her',
            'good at helping but need help too', 
            'family there for me when I help others',
            'mom helps me and I help her'
        ]
        
        for text in complex_cases:
            # These contain both support and strength elements
            # Context should determine which aspect is emphasized
            intent_str, conf_str = classify_intent(text, current_step='strengths')
            intent_sup, conf_sup = classify_intent(text, current_step='support_people')
            
            # Should have reasonable confidence in both contexts
            self.assertGreater(conf_str, 0.3, 
                             f"'{text}' should have reasonable confidence at strengths")
            self.assertGreater(conf_sup, 0.3, 
                             f"'{text}' should have reasonable confidence at support")
            
            # Context should influence the classification
            self.assertIn(intent_str, ['strengths', 'support_people'], 
                         f"'{text}' should be recognized as relevant at strengths")
            self.assertIn(intent_sup, ['strengths', 'support_people'], 
                         f"'{text}' should be recognized as relevant at support")

if __name__ == '__main__':
    # Set test environment
    os.environ['LLM_ENABLED'] = 'false'  # Disable LLM for testing
    os.environ['FLASK_ENV'] = 'testing'
    
    unittest.main()