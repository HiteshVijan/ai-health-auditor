"""
Unit tests for LLM wrapper module.

Tests audit summarization with sample audit JSON.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
import sys
import os

# Add ml directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml"))

from llm.llm_wrapper import (
    summarize_audit,
    OpenAIProvider,
    HuggingFaceProvider,
    MockProvider,
    AuditSummary,
    KeyIssue,
    _format_audit_for_prompt,
    _parse_llm_response,
    _validate_and_fill_summary,
    _generate_fallback_summary,
    _get_recommendation_for_type,
    _get_default_provider,
)


@pytest.fixture
def sample_audit_json() -> dict:
    """Create sample audit JSON with various issues."""
    return {
        "score": 65,
        "total_issues": 4,
        "critical_count": 1,
        "high_count": 2,
        "medium_count": 1,
        "low_count": 0,
        "potential_savings": 275.50,
        "issues": [
            {
                "id": 1,
                "type": "arithmetic_mismatch",
                "severity": "critical",
                "description": "Calculated total ($500.00) does not match stated total ($550.00)",
                "field": "total_amount",
                "expected": "$500.00",
                "actual": "$550.00",
                "amount_impact": 50.00,
            },
            {
                "id": 2,
                "type": "duplicate_charge",
                "severity": "high",
                "description": "Duplicate charge detected: 'CBC' appears 2 times",
                "field": "line_items",
                "expected": "1",
                "actual": "2",
                "amount_impact": 45.00,
            },
            {
                "id": 3,
                "type": "overcharge",
                "severity": "high",
                "description": "Potential overcharge for 'Office Visit': $350.00 exceeds expected $175.00",
                "field": "line_items[0]",
                "expected": "≤$175.00",
                "actual": "$350.00",
                "amount_impact": 175.00,
            },
            {
                "id": 4,
                "type": "tax_mismatch",
                "severity": "medium",
                "description": "Tax rate 18.0% is outside normal range (0%-15%)",
                "field": "tax_rate",
                "expected": "0%-15%",
                "actual": "18.0%",
                "amount_impact": None,
            },
        ],
    }


@pytest.fixture
def clean_audit_json() -> dict:
    """Create sample audit JSON with no issues."""
    return {
        "score": 100,
        "total_issues": 0,
        "critical_count": 0,
        "high_count": 0,
        "medium_count": 0,
        "low_count": 0,
        "potential_savings": 0.0,
        "issues": [],
    }


@pytest.fixture
def valid_llm_response() -> str:
    """Create a valid LLM response."""
    return json.dumps({
        "summary_bullets": [
            "Bill audit identified 4 issues with a score of 65/100",
            "Critical arithmetic mismatch found in total calculation",
            "Potential savings of $275.50 identified",
        ],
        "key_issues": [
            {
                "id": 1,
                "description": "Total amount mismatch of $50.00",
                "recommendation": "Request corrected invoice with accurate total",
            },
            {
                "id": 2,
                "description": "Duplicate CBC charge detected",
                "recommendation": "Request removal of duplicate charge",
            },
        ],
    })


@pytest.fixture
def mock_provider(valid_llm_response: str) -> MockProvider:
    """Create mock provider with valid response."""
    return MockProvider(response=valid_llm_response)


class TestSummarizeAudit:
    """Test cases for summarize_audit function."""

    def test_returns_correct_structure(
        self,
        sample_audit_json: dict,
        mock_provider: MockProvider,
    ):
        """Test that summary has correct structure."""
        summary = summarize_audit(sample_audit_json, provider=mock_provider)

        assert "summary_bullets" in summary
        assert "key_issues" in summary
        assert isinstance(summary["summary_bullets"], list)
        assert isinstance(summary["key_issues"], list)

    def test_summary_bullets_not_empty(
        self,
        sample_audit_json: dict,
        mock_provider: MockProvider,
    ):
        """Test that summary bullets are not empty."""
        summary = summarize_audit(sample_audit_json, provider=mock_provider)

        assert len(summary["summary_bullets"]) > 0
        assert all(isinstance(b, str) for b in summary["summary_bullets"])

    def test_key_issues_structure(
        self,
        sample_audit_json: dict,
        mock_provider: MockProvider,
    ):
        """Test that key issues have correct structure."""
        summary = summarize_audit(sample_audit_json, provider=mock_provider)

        for issue in summary["key_issues"]:
            assert "id" in issue
            assert "description" in issue
            assert "recommendation" in issue

    def test_uses_fallback_on_error(self, sample_audit_json: dict):
        """Test that fallback is used when LLM fails."""
        # Create a provider that raises an error
        failing_provider = MockProvider()
        failing_provider.generate = MagicMock(
            side_effect=RuntimeError("API Error")
        )

        summary = summarize_audit(sample_audit_json, provider=failing_provider)

        # Should still return valid summary
        assert "summary_bullets" in summary
        assert len(summary["summary_bullets"]) > 0

    def test_clean_audit_summary(
        self,
        clean_audit_json: dict,
        mock_provider: MockProvider,
    ):
        """Test summary for clean audit with no issues."""
        summary = summarize_audit(clean_audit_json, provider=mock_provider)

        assert "summary_bullets" in summary


class TestMockProvider:
    """Test cases for MockProvider."""

    def test_is_always_available(self):
        """Test that mock provider is always available."""
        provider = MockProvider()
        assert provider.is_available() is True

    def test_returns_custom_response(self):
        """Test that custom response is returned."""
        custom_response = '{"test": "value"}'
        provider = MockProvider(response=custom_response)

        result = provider.generate("any prompt")
        assert result == custom_response

    def test_returns_default_response(self):
        """Test that default response is valid JSON."""
        provider = MockProvider()
        result = provider.generate("any prompt")

        parsed = json.loads(result)
        assert "summary_bullets" in parsed
        assert "key_issues" in parsed


class TestOpenAIProvider:
    """Test cases for OpenAI provider."""

    def test_not_available_without_api_key(self):
        """Test that provider is not available without API key."""
        # Temporarily clear env var
        original = os.environ.get("OPENAI_API_KEY")
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]

        try:
            provider = OpenAIProvider(api_key=None)
            assert provider.is_available() is False
        finally:
            if original:
                os.environ["OPENAI_API_KEY"] = original

    def test_available_with_api_key(self):
        """Test availability check with API key."""
        provider = OpenAIProvider(api_key="test-key")

        # Will be True only if openai is installed
        try:
            import openai
            assert provider.is_available() is True
        except ImportError:
            assert provider.is_available() is False

    @patch("llm.llm_wrapper.OpenAI")
    def test_generate_calls_api(self, mock_openai_class):
        """Test that generate calls OpenAI API correctly."""
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"test": "response"}'))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        provider = OpenAIProvider(api_key="test-key")
        result = provider.generate("test prompt")

        assert result == '{"test": "response"}'
        mock_client.chat.completions.create.assert_called_once()


class TestHuggingFaceProvider:
    """Test cases for HuggingFace provider."""

    def test_availability_check(self):
        """Test availability check."""
        provider = HuggingFaceProvider()

        try:
            import transformers
            import torch
            assert provider.is_available() is True
        except ImportError:
            assert provider.is_available() is False


class TestFormatAuditForPrompt:
    """Test cases for prompt formatting."""

    def test_formats_audit_json(self, sample_audit_json: dict):
        """Test that audit is formatted correctly."""
        formatted = _format_audit_for_prompt(sample_audit_json)

        parsed = json.loads(formatted)
        assert parsed["score"] == 65
        assert parsed["total_issues"] == 4
        assert len(parsed["issues"]) == 4

    def test_limits_issues_to_10(self):
        """Test that issues are limited to 10."""
        audit = {
            "score": 50,
            "issues": [{"id": i, "type": "test"} for i in range(20)],
        }

        formatted = _format_audit_for_prompt(audit)
        parsed = json.loads(formatted)

        assert len(parsed["issues"]) == 10

    def test_handles_missing_fields(self):
        """Test handling of missing fields."""
        audit = {"score": 80}

        formatted = _format_audit_for_prompt(audit)
        parsed = json.loads(formatted)

        assert parsed["total_issues"] == 0
        assert parsed["issues"] == []


class TestParseLLMResponse:
    """Test cases for LLM response parsing."""

    def test_parses_valid_json(self):
        """Test parsing of valid JSON."""
        response = '{"summary_bullets": ["test"], "key_issues": []}'
        result = _parse_llm_response(response)

        assert result["summary_bullets"] == ["test"]

    def test_parses_json_in_markdown(self):
        """Test parsing JSON from markdown code block."""
        response = """Here's the summary:
```json
{"summary_bullets": ["test"], "key_issues": []}
```"""
        result = _parse_llm_response(response)

        assert result["summary_bullets"] == ["test"]

    def test_parses_json_with_extra_text(self):
        """Test parsing JSON with surrounding text."""
        response = 'Based on my analysis: {"summary_bullets": ["test"]} Thank you.'
        result = _parse_llm_response(response)

        assert result["summary_bullets"] == ["test"]

    def test_raises_on_invalid_response(self):
        """Test that ValueError is raised for invalid response."""
        with pytest.raises(ValueError):
            _parse_llm_response("This is not JSON at all")


class TestValidateAndFillSummary:
    """Test cases for summary validation."""

    def test_fills_missing_bullets(self, sample_audit_json: dict):
        """Test that missing bullets are filled."""
        summary = {"key_issues": []}

        result = _validate_and_fill_summary(summary, sample_audit_json)

        assert len(result["summary_bullets"]) > 0

    def test_fills_missing_issues(self, sample_audit_json: dict):
        """Test that missing issues key is filled."""
        summary = {"summary_bullets": ["test"]}

        result = _validate_and_fill_summary(summary, sample_audit_json)

        assert "key_issues" in result
        assert isinstance(result["key_issues"], list)

    def test_validates_issue_structure(self, sample_audit_json: dict):
        """Test that issue structure is validated."""
        summary = {
            "summary_bullets": ["test"],
            "key_issues": [
                {"description": "test"},  # Missing id and recommendation
            ],
        }

        result = _validate_and_fill_summary(summary, sample_audit_json)

        assert result["key_issues"][0]["id"] == 1
        assert "recommendation" in result["key_issues"][0]

    def test_handles_non_list_bullets(self, sample_audit_json: dict):
        """Test handling of non-list bullets."""
        summary = {"summary_bullets": "single string", "key_issues": []}

        result = _validate_and_fill_summary(summary, sample_audit_json)

        assert isinstance(result["summary_bullets"], list)


class TestGenerateFallbackSummary:
    """Test cases for fallback summary generation."""

    def test_generates_summary_for_clean_audit(self, clean_audit_json: dict):
        """Test fallback for clean audit."""
        summary = _generate_fallback_summary(clean_audit_json)

        assert len(summary["summary_bullets"]) > 0
        assert "100/100" in summary["summary_bullets"][0]

    def test_generates_summary_for_problematic_audit(
        self,
        sample_audit_json: dict,
    ):
        """Test fallback for audit with issues."""
        summary = _generate_fallback_summary(sample_audit_json)

        assert len(summary["summary_bullets"]) > 0
        assert len(summary["key_issues"]) > 0

    def test_includes_savings_in_summary(self, sample_audit_json: dict):
        """Test that savings are mentioned in summary."""
        summary = _generate_fallback_summary(sample_audit_json)

        bullets_text = " ".join(summary["summary_bullets"])
        assert "$275.50" in bullets_text or "275" in bullets_text

    def test_creates_key_issues_for_high_severity(
        self,
        sample_audit_json: dict,
    ):
        """Test that key issues are created for high severity."""
        summary = _generate_fallback_summary(sample_audit_json)

        # Should have key issues for critical and high severity
        assert len(summary["key_issues"]) >= 2

    def test_score_categories(self):
        """Test different score category messages."""
        # Excellent (90+)
        audit_90 = {"score": 95, "issues": []}
        summary = _generate_fallback_summary(audit_90)
        assert "Excellent" in summary["summary_bullets"][0]

        # Good (70-89)
        audit_75 = {"score": 75, "issues": []}
        summary = _generate_fallback_summary(audit_75)
        assert "Good" in summary["summary_bullets"][0]

        # Moderate (50-69)
        audit_55 = {"score": 55, "issues": []}
        summary = _generate_fallback_summary(audit_55)
        assert "Moderate" in summary["summary_bullets"][0]

        # Poor (<50)
        audit_30 = {"score": 30, "issues": []}
        summary = _generate_fallback_summary(audit_30)
        assert "Significant" in summary["summary_bullets"][0]


class TestGetRecommendationForType:
    """Test cases for type-specific recommendations."""

    def test_duplicate_charge_recommendation(self):
        """Test recommendation for duplicate charges."""
        rec = _get_recommendation_for_type("duplicate_charge")
        assert "duplicate" in rec.lower()

    def test_arithmetic_mismatch_recommendation(self):
        """Test recommendation for arithmetic mismatch."""
        rec = _get_recommendation_for_type("arithmetic_mismatch")
        assert "calculation" in rec.lower() or "itemized" in rec.lower()

    def test_overcharge_recommendation(self):
        """Test recommendation for overcharge."""
        rec = _get_recommendation_for_type("overcharge")
        assert "rate" in rec.lower() or "charge" in rec.lower()

    def test_unknown_type_recommendation(self):
        """Test default recommendation for unknown type."""
        rec = _get_recommendation_for_type("unknown_type")
        assert "review" in rec.lower()


class TestGetDefaultProvider:
    """Test cases for default provider selection."""

    def test_returns_provider(self):
        """Test that a provider is always returned."""
        provider = _get_default_provider()
        assert provider is not None
        assert provider.is_available() is True


class TestIntegration:
    """Integration tests for complete summarization flow."""

    def test_full_summarization_flow(self, sample_audit_json: dict):
        """Test complete summarization with mock provider."""
        provider = MockProvider()
        summary = summarize_audit(sample_audit_json, provider=provider)

        # Verify complete output
        assert isinstance(summary, dict)
        assert "summary_bullets" in summary
        assert "key_issues" in summary
        assert len(summary["summary_bullets"]) > 0

        # Verify key issues have all fields
        for issue in summary["key_issues"]:
            assert isinstance(issue["id"], int)
            assert isinstance(issue["description"], str)
            assert isinstance(issue["recommendation"], str)

    def test_fallback_integration(self, sample_audit_json: dict):
        """Test fallback path integration."""
        # Provider that always fails
        failing_provider = MockProvider()
        failing_provider.generate = MagicMock(
            side_effect=Exception("Connection error")
        )

        summary = summarize_audit(sample_audit_json, provider=failing_provider)

        # Should still produce valid output
        assert len(summary["summary_bullets"]) > 0
        assert len(summary["key_issues"]) > 0

