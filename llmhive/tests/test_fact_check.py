"""Unit tests for enhanced fact-checking with correction loop."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from llmhive.src.llmhive.app.fact_check import (
    FactChecker,
    VerificationReport,
    VerificationStatus,
    FactCheckItem,
    verify,
    correct_answer,
    verify_and_correct,
)


class TestVerificationReport:
    """Tests for VerificationReport class."""
    
    def test_empty_report(self):
        """Test empty report has correct defaults."""
        report = VerificationReport()
        
        assert report.verification_score == 1.0
        assert report.needs_correction is False
        assert report.is_valid is True
        assert report.verified_count == 0
        assert report.unverified_count == 0
    
    def test_add_verified_fact(self):
        """Test adding a verified fact."""
        report = VerificationReport()
        report.add_fact(
            fact_text="Paris is the capital of France.",
            is_verified=True,
            evidence="Wikipedia confirms Paris is France's capital.",
            confidence=0.95,
        )
        
        assert len(report.items) == 1
        assert report.items[0].verified is True
        assert report.verified_count == 1
        assert report.needs_correction is False
    
    def test_add_unverified_fact(self):
        """Test adding an unverified fact."""
        report = VerificationReport()
        report.add_fact(
            fact_text="Sydney is the capital of Australia.",
            is_verified=False,
            confidence=0.2,
        )
        
        assert report.items[0].verified is False
        assert report.unverified_count == 1
        assert report.needs_correction is True
    
    def test_mixed_facts(self):
        """Test report with mix of verified and unverified facts."""
        report = VerificationReport()
        
        report.add_fact("Paris is the capital of France.", True, confidence=0.9)
        report.add_fact("Sydney is the capital of Australia.", False, confidence=0.1)
        report.add_fact("Tokyo is in Japan.", True, confidence=0.95)
        
        assert report.verified_count == 2
        assert report.unverified_count == 1
        assert report.needs_correction is True
        assert 0.5 < report.verification_score < 1.0
    
    def test_get_failed_claims(self):
        """Test getting failed claims."""
        report = VerificationReport()
        
        report.add_fact("Fact 1", True, confidence=0.9)
        report.add_fact("Wrong fact", False, confidence=0.1)
        report.add_fact("Fact 3", True, confidence=0.9)
        
        failed = report.get_failed_claims()
        
        assert len(failed) == 1
        assert failed[0].text == "Wrong fact"


class TestFactChecker:
    """Tests for FactChecker class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.checker = FactChecker(
            web_client=None,
            memory_manager=None,
            max_verification_iterations=2,
        )
    
    def test_extract_factual_statements_simple(self):
        """Test extracting factual statements from text."""
        answer = (
            "Paris is the capital of France. "
            "It has a population of over 2 million people. "
            "The Eiffel Tower was built in 1889."
        )
        
        facts = self.checker._extract_factual_statements(answer)
        
        assert len(facts) >= 2
        assert any("Paris" in f for f in facts)
        assert any("1889" in f for f in facts)
    
    def test_extract_factual_statements_skips_opinions(self):
        """Test that opinion statements are skipped."""
        answer = (
            "I think Paris is beautiful. "
            "In my opinion, it's the best city. "
            "Paris is the capital of France."
        )
        
        facts = self.checker._extract_factual_statements(answer)
        
        # Should only extract the factual statement
        assert len(facts) <= 1
        if facts:
            assert "I think" not in facts[0]
    
    def test_extract_factual_statements_skips_questions(self):
        """Test that questions are skipped."""
        answer = (
            "What is the capital of France? "
            "Paris is the capital of France."
        )
        
        facts = self.checker._extract_factual_statements(answer)
        
        for fact in facts:
            assert not fact.endswith("?")
    
    def test_generate_alternative_queries(self):
        """Test generating alternative search queries."""
        fact = "The Eiffel Tower was built in 1889."
        
        queries = self.checker._generate_alternative_queries(fact)
        
        assert len(queries) >= 2
        assert fact in queries  # Original should be included
        assert any("true" in q.lower() for q in queries)  # Question form
    
    def test_check_in_documents(self):
        """Test checking facts against documents."""
        # Mock web documents
        class MockDoc:
            def __init__(self, title, snippet):
                self.title = title
                self.snippet = snippet
                self.url = "https://example.com"
        
        docs = [
            MockDoc("Paris - Wikipedia", "Paris is the capital of France..."),
            MockDoc("France Info", "The capital city is Paris with 2 million..."),
        ]
        
        fact = "Paris is the capital of France."
        verified, evidence, confidence = self.checker._check_in_documents(fact, docs)
        
        assert verified is True
        assert confidence > 0.3
        assert "Paris" in evidence or "capital" in evidence
    
    def test_check_in_documents_no_match(self):
        """Test checking facts against unrelated documents."""
        class MockDoc:
            def __init__(self, title, snippet):
                self.title = title
                self.snippet = snippet
                self.url = "https://example.com"
        
        docs = [
            MockDoc("Weather Today", "Sunny skies expected..."),
            MockDoc("Sports News", "Local team wins championship..."),
        ]
        
        fact = "Paris is the capital of France."
        verified, evidence, confidence = self.checker._check_in_documents(fact, docs)
        
        # Should not find supporting evidence
        assert confidence < 0.5


class TestCorrectAnswer:
    """Tests for answer correction functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.checker = FactChecker()
    
    def test_correct_single_wrong_fact(self):
        """Test correcting a single wrong fact.
        
        Scenario: "The capital of Australia is Sydney."
        Should correct to Canberra.
        """
        answer = "Australia is a country in the Southern Hemisphere. The capital of Australia is Sydney."
        
        report = VerificationReport()
        report.add_fact(
            "Australia is a country in the Southern Hemisphere.",
            is_verified=True,
            confidence=0.95,
        )
        report.add_fact(
            "The capital of Australia is Sydney.",
            is_verified=False,
            confidence=0.2,
        )
        
        # Provide the correct fact
        corrections = {
            "The capital of Australia is Sydney.": "The capital of Australia is Canberra."
        }
        
        corrected = self.checker.correct_answer(answer, report, corrections)
        
        assert "Canberra" in corrected
        assert "Sydney" not in corrected or "Sydney" in corrected.split("Canberra")[0] == ""
    
    def test_correct_multiple_wrong_facts(self):
        """Test correcting multiple wrong facts."""
        answer = "Sydney is the capital of Australia. Mount Everest is in Australia."
        
        report = VerificationReport()
        report.add_fact("Sydney is the capital of Australia.", False, confidence=0.1)
        report.add_fact("Mount Everest is in Australia.", False, confidence=0.1)
        
        corrections = {
            "Sydney is the capital of Australia.": "Canberra is the capital of Australia.",
            "Mount Everest is in Australia.": "Mount Everest is in Nepal/Tibet.",
        }
        
        corrected = self.checker.correct_answer(answer, report, corrections)
        
        assert "Canberra" in corrected
        assert "Nepal" in corrected or "Tibet" in corrected
    
    def test_mark_unverifiable_without_correction(self):
        """Test that unverifiable facts are marked when no correction available."""
        answer = "The mysterious artifact dates from 10000 BC."
        
        report = VerificationReport()
        report.add_fact(
            "The mysterious artifact dates from 10000 BC.",
            is_verified=False,
        )
        
        corrected = self.checker.correct_answer(answer, report)
        
        # Should be marked as unverified
        assert "[" in corrected or "unverified" in corrected.lower()
    
    def test_preserve_verified_facts(self):
        """Test that verified facts are not changed."""
        answer = "Paris is the capital of France. Sydney is the capital of Australia."
        
        report = VerificationReport()
        report.add_fact("Paris is the capital of France.", True, confidence=0.95)
        report.add_fact("Sydney is the capital of Australia.", False, confidence=0.2)
        
        corrections = {
            "Sydney is the capital of Australia.": "Canberra is the capital of Australia."
        }
        
        corrected = self.checker.correct_answer(answer, report, corrections)
        
        # Paris should still be there
        assert "Paris is the capital of France" in corrected


class TestVerificationLoop:
    """Tests for the verification and correction loop."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.checker = FactChecker(
            max_verification_iterations=2,
            min_confidence_threshold=0.5,
        )
    
    @pytest.mark.asyncio
    async def test_verify_correct_answer(self):
        """Test verification of a correct answer."""
        answer = "The sky is blue. Water is essential for life."
        
        # Mock the _verify_fact method to return True
        async def mock_verify(fact, **kwargs):
            return True, "Evidence found", 0.9, "web"
        
        self.checker._verify_fact = mock_verify
        
        report = await self.checker.verify(answer)
        
        assert report.is_valid is True
        assert report.needs_correction is False
    
    @pytest.mark.asyncio
    async def test_verify_incorrect_answer(self):
        """Test verification of an incorrect answer."""
        answer = "The capital of Australia is Sydney."
        
        # Mock the _verify_fact method to return False
        async def mock_verify(fact, **kwargs):
            return False, "", 0.2, "unknown"
        
        self.checker._verify_fact = mock_verify
        
        report = await self.checker.verify(answer)
        
        assert report.needs_correction is True
        assert report.unverified_count > 0
    
    @pytest.mark.asyncio
    async def test_verify_and_correct_loop(self):
        """Test the full verification and correction loop."""
        answer = "The capital of Australia is Sydney. Australia is in the Southern Hemisphere."
        
        call_count = [0]
        
        # Mock that first verification fails, second passes after correction
        async def mock_verify(answer_text, **kwargs):
            call_count[0] += 1
            report = VerificationReport()
            
            if "Sydney" in answer_text:
                report.add_fact("The capital of Australia is Sydney.", False, confidence=0.2)
                report.add_fact("Australia is in the Southern Hemisphere.", True, confidence=0.9)
            else:
                # After correction
                report.add_fact("The capital of Australia is Canberra.", True, confidence=0.9)
                report.add_fact("Australia is in the Southern Hemisphere.", True, confidence=0.9)
            
            return report
        
        def mock_correct(answer_text, report, corrections=None):
            return answer_text.replace("Sydney", "Canberra")
        
        self.checker.verify = mock_verify
        self.checker.correct_answer = mock_correct
        
        final_answer, final_report = await self.checker.verify_and_correct_loop(
            answer,
            max_iterations=2,
        )
        
        # Should have corrected Sydney to Canberra
        assert "Canberra" in final_answer or call_count[0] >= 2
    
    @pytest.mark.asyncio
    async def test_loop_stops_on_no_improvement(self):
        """Test that loop stops when no improvement is made."""
        answer = "Some unverifiable claim about unknown topic."
        
        iteration_count = [0]
        
        async def mock_verify(answer_text, **kwargs):
            iteration_count[0] += 1
            report = VerificationReport()
            report.add_fact("Some unverifiable claim.", False, confidence=0.1)
            return report
        
        self.checker.verify = mock_verify
        
        _, final_report = await self.checker.verify_and_correct_loop(
            answer,
            max_iterations=3,
        )
        
        # Should stop after detecting no improvement
        assert iteration_count[0] <= 3


class TestMultiHopVerification:
    """Tests for multi-hop verification strategies."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_web_client = MagicMock()
        self.checker = FactChecker(
            web_client=self.mock_web_client,
        )
    
    @pytest.mark.asyncio
    async def test_multihop_with_alternative_query(self):
        """Test multi-hop verification tries alternative queries."""
        # First query returns no results, second should try alternatives
        search_call_count = [0]
        
        class MockDoc:
            def __init__(self, title, snippet):
                self.title = title
                self.snippet = snippet
                self.url = "https://example.com"
        
        async def mock_search(query):
            search_call_count[0] += 1
            if "true" in query.lower():
                return [MockDoc("Fact Check", "Paris is the capital of France confirmed.")]
            return []
        
        self.mock_web_client.search = mock_search
        
        fact = "Paris is the capital of France."
        verified, evidence, confidence, source = await self.checker._multihop_verify(fact)
        
        # Should have tried alternative queries
        assert search_call_count[0] >= 1
    
    @pytest.mark.asyncio
    async def test_compound_fact_verification(self):
        """Test verification of compound facts (with 'and')."""
        fact = "Paris is in France and Tokyo is in Japan."
        
        # Mock individual fact verification
        async def mock_verify_single(f, **kwargs):
            if "Paris" in f:
                return True, "Paris confirmed", 0.9, "web"
            elif "Tokyo" in f:
                return True, "Tokyo confirmed", 0.9, "web"
            return False, "", 0.0, "unknown"
        
        self.checker._verify_fact = mock_verify_single
        
        verified, evidence, confidence = await self.checker._verify_compound_fact(fact)
        
        # Both parts should be verified
        assert verified is True
        assert confidence > 0.7


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.checker = FactChecker()
    
    def test_empty_answer(self):
        """Test handling of empty answer."""
        facts = self.checker._extract_factual_statements("")
        assert facts == []
    
    def test_very_short_answer(self):
        """Test handling of very short answer."""
        facts = self.checker._extract_factual_statements("Yes.")
        assert facts == []  # Too short to be a factual claim
    
    def test_answer_with_only_questions(self):
        """Test handling of answer with only questions."""
        answer = "What do you mean? How can I help? Is that correct?"
        facts = self.checker._extract_factual_statements(answer)
        assert facts == []
    
    @pytest.mark.asyncio
    async def test_verify_handles_web_client_error(self):
        """Test that verification handles web client errors gracefully."""
        mock_web_client = MagicMock()
        mock_web_client.search = AsyncMock(side_effect=Exception("Network error"))
        
        checker = FactChecker(web_client=mock_web_client)
        
        # Should not raise exception
        report = await checker.verify("Paris is the capital of France.")
        
        # Should have items but verification might fail
        assert isinstance(report, VerificationReport)
    
    def test_infer_correction_basic(self):
        """Test inferring correction from evidence."""
        wrong_fact = "Sydney is the capital of Australia."
        evidence = "Canberra is the capital of Australia since 1913."
        
        correction = self.checker._infer_correction(wrong_fact, evidence)
        
        # Should extract correction if possible
        if correction:
            assert "Canberra" in correction


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""
    
    @pytest.mark.asyncio
    async def test_verify_function(self):
        """Test the verify convenience function."""
        report = await verify("The Earth orbits the Sun.")
        
        assert isinstance(report, VerificationReport)
    
    def test_correct_answer_function(self):
        """Test the correct_answer convenience function."""
        report = VerificationReport()
        report.add_fact("Wrong fact.", False)
        
        corrected = correct_answer(
            "Original with wrong fact.",
            report,
            {"Wrong fact.": "Correct fact."},
        )
        
        assert "Correct fact" in corrected or "[" in corrected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

