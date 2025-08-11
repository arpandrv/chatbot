import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nlp.risk_detector import contains_risk, get_crisis_resources

class TestRiskDetection(unittest.TestCase):
    
    def test_exact_phrases(self):
        """Test detection of exact risk phrases"""
        test_phrases = [
            "I want to kill myself",
            "I'm suicidal",
            "I want to end my life",
            "I'm going to hurt myself",
            "I've been cutting",
            "I want to overdose",
            "I'm going to jump off a bridge",
            "I have a plan to die",
            "I'm worthless and want to die",
            "Nobody cares about me",
            "I want to disappear forever",
            "I'm ready to end it all"
        ]
        
        for phrase in test_phrases:
            with self.subTest(phrase=phrase):
                self.assertTrue(contains_risk(phrase), f"Failed to detect: {phrase}")
    
    def test_misspellings(self):
        """Test detection of common misspellings"""
        misspelled_phrases = [
            "I want to comit suicde",  # misspelled suicide
            "Im suicidal",  # missing apostrophe
            "i wanna kill myself",  # informal
            "gonna hurt myself",  # informal
            "wanna die",  # informal
            "cant go on",  # missing apostrophe
            "im worthles",  # misspelling
        ]
        
        for phrase in misspelled_phrases:
            with self.subTest(phrase=phrase):
                self.assertTrue(contains_risk(phrase), f"Failed to detect misspelling: {phrase}")
    
    def test_context_sensitive(self):
        """Test that context matters for some words"""
        # These should trigger
        risky_context = [
            "I want to die",
            "I'm going to kill myself",
            "I plan to hurt myself",
            "I will cut myself",
            "I can't go on living"
        ]
        
        for phrase in risky_context:
            with self.subTest(phrase=phrase):
                self.assertTrue(contains_risk(phrase), f"Failed to detect in context: {phrase}")
    
    def test_false_positives(self):
        """Test that normal phrases don't trigger false positives"""
        safe_phrases = [
            "I'm feeling happy today",
            "I love my family",
            "School is going well",
            "I'm excited about the future",
            "I had a good day",
            "I'm looking forward to tomorrow",
            "My friends are supportive",
            "I'm proud of myself",
            "Things are getting better"
        ]
        
        for phrase in safe_phrases:
            with self.subTest(phrase=phrase):
                self.assertFalse(contains_risk(phrase), f"False positive on: {phrase}")
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        # Empty or invalid input
        self.assertFalse(contains_risk(""))
        self.assertFalse(contains_risk(None))
        self.assertFalse(contains_risk("   "))
        
        # Very long input with risk phrase embedded
        long_text = "Today was okay, went to school and saw friends. " * 10
        long_text += "I want to kill myself"
        self.assertTrue(contains_risk(long_text))
    
    def test_case_insensitive(self):
        """Test that detection is case-insensitive"""
        variations = [
            "I WANT TO DIE",
            "i want to die",
            "I WaNt To DiE",
            "I Want To Die"
        ]
        
        for phrase in variations:
            with self.subTest(phrase=phrase):
                self.assertTrue(contains_risk(phrase), f"Failed case-insensitive: {phrase}")
    
    def test_crisis_resources(self):
        """Test that crisis resources are returned properly"""
        resources = get_crisis_resources()
        
        # Check it returns a string
        self.assertIsInstance(resources, str)
        
        # Check it contains key services
        self.assertIn("13YARN", resources)
        self.assertIn("13 92 76", resources)
        self.assertIn("Lifeline", resources)
        self.assertIn("Kids Helpline", resources)
        
        # Check it contains the crisis message
        self.assertIn("Your safety is the most important", resources)
        self.assertIn("You don't have to go through this alone", resources)
    
    def test_variants_detection(self):
        """Test detection of all variants in configuration"""
        test_variants = [
            "I'm going to off myself",
            "I want to self-harm",
            "Life's not worth living",
            "I'm going to OD",
            "I'll jump from the bridge", 
            "I have a noose ready",
            "I'll slit my wrists",
            "I'm a burden to everyone",
            "There's no hope left",
            "No one would miss me",
            "This is my final goodbye",
            "I hear voices telling me to die",
            "I've made a plan",
            "I found a method",
            "The pain is unbearable",
            "I feel trapped with no way out",
            "I want to sleep forever",
            "Everything is darkness",
            "I'm dead inside",
            "I'm tired of fighting",
            "Please help me, I'm desperate",
            "I'm scared of what I might do",
            "I'm losing control",
            "This is my final decision",
            "I just want peace",
            "I'll make it look like an accident",
            "I'm writing my goodbye letter",
            "I have the pills ready",
            "I'm going to the train tracks",
            "I'll drive off the road",
            "I'm drinking myself to death",
            "I have a blade",
            "I can't breathe anymore",
            "I have poison",
            "I'm on the rooftop",
            "I'm ready to go",
            "I'll do it tonight",
            "This weekend is it",
            "On my birthday I'll be gone",
            "Everyone would be better without me"
        ]
        
        for phrase in test_variants:
            with self.subTest(phrase=phrase):
                self.assertTrue(contains_risk(phrase), f"Failed to detect variant: {phrase}")
    
    def test_fuzzy_matching(self):
        """Test fuzzy matching for close misspellings"""
        fuzzy_phrases = [
            "I want to kil myself",  # missing l
            "Im suicidle",  # wrong spelling
            "I wnt to die",  # missing letter
            "selfharm",  # no space/hyphen
            "end mi life",  # mi instead of my
        ]
        
        for phrase in fuzzy_phrases:
            with self.subTest(phrase=phrase):
                self.assertTrue(contains_risk(phrase), f"Failed fuzzy match: {phrase}")

if __name__ == '__main__':
    unittest.main()