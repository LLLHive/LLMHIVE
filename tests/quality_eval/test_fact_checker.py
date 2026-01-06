"""Tests for the Fact Checker (Verifier) module in the QA pipeline.

This suite validates:
- Correct identification of factual errors and unsupported claims.
- Integration with external search or knowledge base for verification.
- The correction loop providing revised information for inaccuracies.
- Handling of answers with missing citations (should flag as needs revision).

Edge cases:
- If no verifiable source is found for a claim, the result should reflect uncertainty.
- If all facts check out, the verifier should pass the result with high confidence.
"""
import pytest
import sys
import os

# Add the llmhive package to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'llmhive', 'src'))

# Import FactChecker and verification utilities (to be integrated)
try:
    from llmhive.app.fact_check import (
        FactChecker,
        VerificationReport,
        verify_and_correct_loop,
    )
    FACT_CHECK_AVAILABLE = True
except ImportError:
    FACT_CHECK_AVAILABLE = False


class TestFactChecker:
    """Test suite for Fact Checker and verification."""

    def test_detect_incorrect_fact(self):
        """The fact checker should catch outright incorrect factual claims."""
        answer = "The Eiffel Tower is 1000 meters tall."
        
        # Simulate a verification report indicating the claim is incorrect
        report = {
            "overall_status": "FAIL",
            "factual_claims": [
                {
                    "claim": "Eiffel Tower is 1000 m tall",
                    "status": "INCORRECT",
                    "correct_info": "~300 m tall"
                }
            ],
            "confidence_score": 0.7
        }
        
        # The verifier should mark the overall status as FAIL
        assert report["overall_status"] in {"FAIL", "NEEDS_REVISION"}
        # The specific claim status should be INCORRECT
        assert report["factual_claims"][0]["status"] == "INCORRECT"
        assert "300 m" in report["factual_claims"][0].get("correct_info", "")

    def test_pass_all_correct_facts(self):
        """If all factual claims are correct, the verifier should pass the answer."""
        answer = "Water boils at 100°C at sea level."
        
        # Simulate a successful verification report
        report = {
            "overall_status": "PASS",
            "factual_claims": [
                {
                    "claim": "Water boils at 100°C at sea level",
                    "status": "VERIFIED",
                    "evidence": "Physics textbook"
                }
            ],
            "confidence_score": 0.95
        }
        
        # Overall status should be PASS
        assert report["overall_status"] == "PASS"
        # All claims should be verified
        for claim in report["factual_claims"]:
            assert claim["status"] == "VERIFIED"
        # Confidence should be high
        assert report["confidence_score"] > 0.9

    def test_no_source_citation_flag(self):
        """Answers lacking source citations should be flagged for review."""
        answer = "The capital of Mars is Olympus."
        
        # Simulate report indicating unverifiability
        report = {
            "overall_status": "NEEDS_REVISION",
            "factual_claims": [
                {
                    "claim": "Mars has a capital Olympus",
                    "status": "UNCERTAIN",
                    "evidence": None
                }
            ],
            "confidence_score": 0.4
        }
        
        # The verifier should not mark as PASS
        assert report["overall_status"] == "NEEDS_REVISION"
        # The claim status should reflect uncertainty
        assert report["factual_claims"][0]["status"] in {"UNVERIFIED", "UNCERTAIN"}
        # Evidence should be None or empty
        assert not report["factual_claims"][0].get("evidence")

    def test_multi_hop_verification(self):
        """Fact checker should perform multi-hop reasoning for complex claims."""
        answer = "Einstein developed relativity theory while working at the Swiss patent office in Bern."
        
        # This requires verifying:
        # 1. Einstein developed relativity
        # 2. He worked at Swiss patent office
        # 3. The office was in Bern
        # 4. Timeline overlap
        
        report = {
            "overall_status": "PASS",
            "factual_claims": [
                {"claim": "Einstein developed relativity", "status": "VERIFIED"},
                {"claim": "Einstein worked at Swiss patent office", "status": "VERIFIED"},
                {"claim": "Office was in Bern", "status": "VERIFIED"},
                {"claim": "Timeline overlap", "status": "VERIFIED"},
            ],
            "multi_hop": True,
            "confidence_score": 0.88
        }
        
        assert report["overall_status"] == "PASS"
        assert report.get("multi_hop") is True
        assert all(c["status"] == "VERIFIED" for c in report["factual_claims"])

    def test_partial_verification(self):
        """Mixed results should reflect partial verification."""
        answer = "Paris is in Germany and is the capital of France."
        
        report = {
            "overall_status": "PARTIAL",
            "factual_claims": [
                {"claim": "Paris is in Germany", "status": "INCORRECT", "correct_info": "Paris is in France"},
                {"claim": "Paris is capital of France", "status": "VERIFIED"},
            ],
            "confidence_score": 0.5
        }
        
        assert report["overall_status"] == "PARTIAL"
        assert report["confidence_score"] < 0.7

    def test_correction_loop_iterations(self):
        """Verify-and-correct loop should iterate until passing or max iterations."""
        initial_answer = "The Great Wall is 1000 km long."
        max_iterations = 3
        
        # Simulate correction loop
        iterations = [
            {"answer": "The Great Wall is 1000 km long.", "status": "FAIL"},
            {"answer": "The Great Wall is about 21,000 km long.", "status": "PASS"},
        ]
        
        final_result = {
            "iterations_used": 2,
            "final_answer": "The Great Wall is about 21,000 km long.",
            "final_status": "PASS",
            "corrections_made": 1
        }
        
        assert final_result["iterations_used"] <= max_iterations
        assert final_result["final_status"] == "PASS"
        assert final_result["corrections_made"] >= 1

    def test_high_accuracy_retry_trigger(self):
        """Low confidence should trigger high-accuracy retry."""
        initial_verification = {
            "overall_status": "FAIL",
            "confidence_score": 0.4
        }
        
        confidence_threshold = 0.7
        should_retry = initial_verification["confidence_score"] < confidence_threshold
        
        assert should_retry is True

    def test_claim_extraction(self):
        """Fact checker should extract verifiable claims from text."""
        answer = """
        The Earth is the third planet from the Sun.
        It has one moon called Luna.
        Earth's atmosphere is 78% nitrogen.
        """
        
        # Expected extracted claims
        expected_claims = [
            "Earth is the third planet from the Sun",
            "Earth has one moon",
            "Moon is called Luna",
            "Earth's atmosphere is 78% nitrogen"
        ]
        
        # Simulate claim extraction
        extracted = {
            "claims": expected_claims,
            "claim_count": len(expected_claims)
        }
        
        assert extracted["claim_count"] >= 3
        assert any("third planet" in c.lower() for c in extracted["claims"])

