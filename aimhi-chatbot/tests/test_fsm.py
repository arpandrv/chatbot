import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.fsm import ChatBotFSM

class TestFSM(unittest.TestCase):
    
    def setUp(self):
        """Set up a fresh FSM for each test"""
        self.fsm = ChatBotFSM("test_session_123")
    
    def test_initial_state(self):
        """Test that FSM starts in welcome state"""
        self.assertEqual(self.fsm.state, 'welcome')
        self.assertTrue(self.fsm.is_welcome())
    
    def test_state_transitions(self):
        """Test the complete state transition flow"""
        # Start at welcome
        self.assertEqual(self.fsm.state, 'welcome')
        
        # Move to support_people
        self.fsm.next_step()
        self.assertEqual(self.fsm.state, 'support_people')
        self.assertTrue(self.fsm.is_support_people())
        
        # Move to strengths
        self.fsm.next_step()
        self.assertEqual(self.fsm.state, 'strengths')
        self.assertTrue(self.fsm.is_strengths())
        
        # Move to worries
        self.fsm.next_step()
        self.assertEqual(self.fsm.state, 'worries')
        self.assertTrue(self.fsm.is_worries())
        
        # Move to goals
        self.fsm.next_step()
        self.assertEqual(self.fsm.state, 'goals')
        self.assertTrue(self.fsm.is_goals())
        
        # Move to summary
        self.fsm.next_step()
        self.assertEqual(self.fsm.state, 'summary')
        self.assertTrue(self.fsm.is_summary())
    
    def test_no_transition_from_summary(self):
        """Test that summary is the final state"""
        # Fast forward to summary
        for _ in range(5):
            self.fsm.next_step()
        
        self.assertEqual(self.fsm.state, 'summary')
        
        # Try to move forward - should stay at summary
        try:
            self.fsm.next_step()
        except:
            pass  # Expected - no transition defined
        
        # Should still be at summary
        self.assertEqual(self.fsm.state, 'summary')
    
    def test_session_id_preserved(self):
        """Test that session ID is preserved throughout transitions"""
        session_id = "test_session_123"
        fsm = ChatBotFSM(session_id)
        
        self.assertEqual(fsm.session_id, session_id)
        
        # Session ID should remain same after transitions
        fsm.next_step()
        self.assertEqual(fsm.session_id, session_id)
        
        fsm.next_step()
        self.assertEqual(fsm.session_id, session_id)
    
    def test_state_check_methods(self):
        """Test the is_<state>() helper methods"""
        # Welcome state
        self.assertTrue(self.fsm.is_welcome())
        self.assertFalse(self.fsm.is_support_people())
        self.assertFalse(self.fsm.is_strengths())
        self.assertFalse(self.fsm.is_worries())
        self.assertFalse(self.fsm.is_goals())
        self.assertFalse(self.fsm.is_summary())
        
        # Support people state
        self.fsm.next_step()
        self.assertFalse(self.fsm.is_welcome())
        self.assertTrue(self.fsm.is_support_people())
        self.assertFalse(self.fsm.is_strengths())
        
        # Strengths state
        self.fsm.next_step()
        self.assertFalse(self.fsm.is_support_people())
        self.assertTrue(self.fsm.is_strengths())
        self.assertFalse(self.fsm.is_worries())
    
    def test_multiple_fsm_instances(self):
        """Test that multiple FSM instances work independently"""
        fsm1 = ChatBotFSM("session1")
        fsm2 = ChatBotFSM("session2")
        
        # Both start at welcome
        self.assertEqual(fsm1.state, 'welcome')
        self.assertEqual(fsm2.state, 'welcome')
        
        # Move fsm1 forward
        fsm1.next_step()
        fsm1.next_step()
        
        # fsm1 should be at strengths, fsm2 still at welcome
        self.assertEqual(fsm1.state, 'strengths')
        self.assertEqual(fsm2.state, 'welcome')
        
        # Move fsm2 forward
        fsm2.next_step()
        
        # Different states
        self.assertEqual(fsm1.state, 'strengths')
        self.assertEqual(fsm2.state, 'support_people')

if __name__ == '__main__':
    unittest.main()