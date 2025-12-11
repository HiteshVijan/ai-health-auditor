"""
Unit tests for negotiation letter generation module.

Tests letter generation with sample audit JSON.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import sys
import os

# Add ml directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml"))

from llm.negotiation_letter import (
    generate_letter,
    LetterTone,
    TONE_INSTRUCTIONS,
    _build_letter_prompt,
    _format_issues_for_prompt,
    _clean_letter_response,
    _fill_patient_info,
    _generate_no_issues_letter,
    _generate_fallback_letter,
    get_letter_template,
    validate_tone,
    get_available_tones,
)
from llm.llm_wrapper import MockProvider


@pytest.fixture
def sample_audit_json() -> dict:
    """Create sample audit JSON with issues."""
    return {
        "score": 65,
        "total_issues": 3,
        "critical_count": 1,
        "high_count": 1,
        "medium_count": 1,
        "low_count": 0,
        "potential_savings": 275.50,
        "issues": [
            {
                "id": 1,
                "type": "arithmetic_mismatch",
                "severity": "critical",
                "description": "Calculated total ($500.00) does not match stated total ($550.00)",
                "amount_impact": 50.00,
            },
            {
                "id": 2,
                "type": "duplicate_charge",
                "severity": "high",
                "description": "Duplicate charge detected: 'CBC' appears 2 times",
                "amount_impact": 45.00,
            },
            {
                "id": 3,
                "type": "overcharge",
                "severity": "medium",
                "description": "Potential overcharge for 'Office Visit': $350.00 exceeds expected $175.00",
                "amount_impact": 175.00,
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
def sample_patient_info() -> dict:
    """Create sample patient information."""
    return {
        "patient_name": "John Michael Smith",
        "account_number": "ACC-123456789",
        "date_of_service": "January 15, 2024",
        "provider_name": "Cityview Medical Center",
        "patient_address": "123 Main Street, Anytown, ST 12345",
        "patient_phone": "(555) 123-4567",
        "patient_email": "john.smith@email.com",
    }


@pytest.fixture
def mock_letter_response() -> str:
    """Create a mock LLM letter response."""
    return """January 15, 2024

[PROVIDER NAME]
Billing Department
[PROVIDER ADDRESS]

Re: Billing Dispute - Account [ACCOUNT NUMBER]

Dear Sir/Madam,

I am writing to dispute charges on my recent medical bill. After careful review, I have identified the following issues:

1. Arithmetic mismatch in total calculation ($50.00 discrepancy)
2. Duplicate CBC charge ($45.00)
3. Potential overcharge for Office Visit ($175.00)

I request immediate correction of these charges.

Sincerely,

[PATIENT NAME]"""


@pytest.fixture
def mock_provider(mock_letter_response: str) -> MockProvider:
    """Create mock provider with letter response."""
    return MockProvider(response=mock_letter_response)


class TestGenerateLetter:
    """Test cases for generate_letter function."""

    def test_generates_letter_string(
        self,
        sample_audit_json: dict,
        mock_provider: MockProvider,
    ):
        """Test that function returns a string."""
        letter = generate_letter(
            sample_audit_json,
            tone="formal",
            provider=mock_provider,
        )

        assert isinstance(letter, str)
        assert len(letter) > 0

    def test_formal_tone(
        self,
        sample_audit_json: dict,
        mock_provider: MockProvider,
    ):
        """Test formal tone letter generation."""
        letter = generate_letter(
            sample_audit_json,
            tone="formal",
            provider=mock_provider,
        )

        assert isinstance(letter, str)

    def test_friendly_tone(
        self,
        sample_audit_json: dict,
        mock_provider: MockProvider,
    ):
        """Test friendly tone letter generation."""
        letter = generate_letter(
            sample_audit_json,
            tone="friendly",
            provider=mock_provider,
        )

        assert isinstance(letter, str)

    def test_assertive_tone(
        self,
        sample_audit_json: dict,
        mock_provider: MockProvider,
    ):
        """Test assertive tone letter generation."""
        letter = generate_letter(
            sample_audit_json,
            tone="assertive",
            provider=mock_provider,
        )

        assert isinstance(letter, str)

    def test_invalid_tone_raises_error(self, sample_audit_json: dict):
        """Test that invalid tone raises ValueError."""
        with pytest.raises(ValueError, match="Invalid tone"):
            generate_letter(sample_audit_json, tone="angry")

    def test_case_insensitive_tone(
        self,
        sample_audit_json: dict,
        mock_provider: MockProvider,
    ):
        """Test that tone is case-insensitive."""
        letter = generate_letter(
            sample_audit_json,
            tone="FORMAL",
            provider=mock_provider,
        )

        assert isinstance(letter, str)

    def test_fills_patient_info(
        self,
        sample_audit_json: dict,
        mock_provider: MockProvider,
        sample_patient_info: dict,
    ):
        """Test that patient info is filled in."""
        letter = generate_letter(
            sample_audit_json,
            tone="formal",
            provider=mock_provider,
            patient_info=sample_patient_info,
        )

        assert "John Michael Smith" in letter
        assert "ACC-123456789" in letter

    def test_no_issues_generates_acknowledgment(
        self,
        clean_audit_json: dict,
        mock_provider: MockProvider,
    ):
        """Test that clean audit generates acknowledgment letter."""
        letter = generate_letter(
            clean_audit_json,
            tone="formal",
            provider=mock_provider,
        )

        assert "accurate" in letter.lower() or "no" in letter.lower()

    def test_fallback_on_provider_error(self, sample_audit_json: dict):
        """Test fallback when provider fails."""
        failing_provider = MockProvider()
        failing_provider.generate = MagicMock(
            side_effect=Exception("API Error")
        )

        letter = generate_letter(
            sample_audit_json,
            tone="formal",
            provider=failing_provider,
        )

        # Should still return a valid letter
        assert isinstance(letter, str)
        assert len(letter) > 100


class TestLetterTone:
    """Test cases for LetterTone enum."""

    def test_all_tones_have_instructions(self):
        """Test that all tones have corresponding instructions."""
        for tone in LetterTone:
            assert tone in TONE_INSTRUCTIONS
            assert len(TONE_INSTRUCTIONS[tone]) > 0

    def test_tone_values(self):
        """Test tone enum values."""
        assert LetterTone.FORMAL.value == "formal"
        assert LetterTone.FRIENDLY.value == "friendly"
        assert LetterTone.ASSERTIVE.value == "assertive"


class TestBuildLetterPrompt:
    """Test cases for prompt building."""

    def test_includes_audit_data(self, sample_audit_json: dict):
        """Test that prompt includes audit data."""
        prompt = _build_letter_prompt(sample_audit_json, LetterTone.FORMAL)

        assert "65" in prompt  # score
        assert "3" in prompt  # total_issues
        assert "275.50" in prompt  # potential_savings

    def test_includes_tone_instructions(self, sample_audit_json: dict):
        """Test that prompt includes tone instructions."""
        prompt = _build_letter_prompt(sample_audit_json, LetterTone.FORMAL)

        assert "formal" in prompt.lower()

    def test_includes_issues(self, sample_audit_json: dict):
        """Test that prompt includes issue details."""
        prompt = _build_letter_prompt(sample_audit_json, LetterTone.FORMAL)

        assert "arithmetic" in prompt.lower()
        assert "duplicate" in prompt.lower()


class TestFormatIssuesForPrompt:
    """Test cases for issue formatting."""

    def test_formats_issues_list(self, sample_audit_json: dict):
        """Test issue list formatting."""
        issues = sample_audit_json["issues"]
        formatted = _format_issues_for_prompt(issues)

        assert "1." in formatted
        assert "2." in formatted
        assert "CRITICAL" in formatted
        assert "$50.00" in formatted

    def test_handles_empty_issues(self):
        """Test handling of empty issues list."""
        formatted = _format_issues_for_prompt([])

        assert "No specific issues" in formatted

    def test_handles_missing_fields(self):
        """Test handling of issues with missing fields."""
        issues = [{"type": "test"}]
        formatted = _format_issues_for_prompt(issues)

        assert "1." in formatted


class TestCleanLetterResponse:
    """Test cases for response cleaning."""

    def test_removes_prefix(self):
        """Test removal of common prefixes."""
        response = "Here's the letter:\n\nDear Sir..."
        cleaned = _clean_letter_response(response)

        assert not cleaned.startswith("Here's")
        assert cleaned.startswith("Dear")

    def test_removes_markdown(self):
        """Test removal of markdown formatting."""
        response = "```\nDear Sir,\n\nLetter content.\n```"
        cleaned = _clean_letter_response(response)

        assert "```" not in cleaned
        assert "Dear Sir" in cleaned

    def test_preserves_clean_response(self):
        """Test that clean responses are preserved."""
        response = "Dear Sir,\n\nThis is a letter."
        cleaned = _clean_letter_response(response)

        assert cleaned == response


class TestFillPatientInfo:
    """Test cases for patient info filling."""

    def test_fills_all_placeholders(self, sample_patient_info: dict):
        """Test that all placeholders are filled."""
        letter = "[PATIENT NAME] at [PATIENT ADDRESS]"
        filled = _fill_patient_info(letter, sample_patient_info)

        assert "John Michael Smith" in filled
        assert "123 Main Street" in filled
        assert "[PATIENT NAME]" not in filled

    def test_preserves_unfilled_placeholders(self):
        """Test that missing info leaves placeholders."""
        letter = "[PATIENT NAME] and [UNKNOWN FIELD]"
        filled = _fill_patient_info(letter, {"patient_name": "John"})

        assert "John" in filled
        assert "[UNKNOWN FIELD]" in filled


class TestGenerateNoIssuesLetter:
    """Test cases for no-issues letter generation."""

    def test_generates_for_all_tones(self, clean_audit_json: dict):
        """Test generation for all tones."""
        for tone in LetterTone:
            letter = _generate_no_issues_letter(clean_audit_json, tone)

            assert isinstance(letter, str)
            assert len(letter) > 100
            assert "accurate" in letter.lower()

    def test_includes_score(self, clean_audit_json: dict):
        """Test that score is included."""
        letter = _generate_no_issues_letter(clean_audit_json, LetterTone.FORMAL)

        assert "100" in letter

    def test_formal_tone_elements(self, clean_audit_json: dict):
        """Test formal tone specific elements."""
        letter = _generate_no_issues_letter(clean_audit_json, LetterTone.FORMAL)

        assert "Sincerely" in letter

    def test_friendly_tone_elements(self, clean_audit_json: dict):
        """Test friendly tone specific elements."""
        letter = _generate_no_issues_letter(clean_audit_json, LetterTone.FRIENDLY)

        assert "Hello" in letter or "Best regards" in letter


class TestGenerateFallbackLetter:
    """Test cases for fallback letter generation."""

    def test_generates_complete_letter(self, sample_audit_json: dict):
        """Test that fallback generates complete letter."""
        letter = _generate_fallback_letter(
            sample_audit_json,
            LetterTone.FORMAL,
        )

        assert "Re:" in letter
        assert "Dear" in letter or "To Whom" in letter
        assert "Sincerely" in letter or "Regards" in letter

    def test_includes_issues(self, sample_audit_json: dict):
        """Test that issues are listed."""
        letter = _generate_fallback_letter(
            sample_audit_json,
            LetterTone.FORMAL,
        )

        assert "arithmetic" in letter.lower() or "mismatch" in letter.lower()
        assert "$" in letter

    def test_includes_savings(self, sample_audit_json: dict):
        """Test that potential savings are mentioned."""
        letter = _generate_fallback_letter(
            sample_audit_json,
            LetterTone.FORMAL,
        )

        assert "275.50" in letter

    def test_assertive_includes_consequences(self, sample_audit_json: dict):
        """Test that assertive tone includes consequences."""
        letter = _generate_fallback_letter(
            sample_audit_json,
            LetterTone.ASSERTIVE,
        )

        assert "escalate" in letter.lower() or "authorities" in letter.lower()

    def test_includes_date(self, sample_audit_json: dict):
        """Test that current date is included."""
        letter = _generate_fallback_letter(
            sample_audit_json,
            LetterTone.FORMAL,
        )

        # Check for current year
        current_year = str(datetime.now().year)
        assert current_year in letter

    def test_fills_patient_info(
        self,
        sample_audit_json: dict,
        sample_patient_info: dict,
    ):
        """Test patient info filling in fallback."""
        letter = _generate_fallback_letter(
            sample_audit_json,
            LetterTone.FORMAL,
            patient_info=sample_patient_info,
        )

        assert "John Michael Smith" in letter


class TestGetLetterTemplate:
    """Test cases for template retrieval."""

    def test_returns_template_string(self):
        """Test that template is returned."""
        template = get_letter_template("formal")

        assert isinstance(template, str)
        assert len(template) > 100

    def test_all_tones_have_templates(self):
        """Test templates for all tones."""
        for tone in ["formal", "friendly", "assertive"]:
            template = get_letter_template(tone)
            assert isinstance(template, str)

    def test_invalid_tone_uses_formal(self):
        """Test that invalid tone defaults to formal."""
        template = get_letter_template("invalid")

        assert isinstance(template, str)


class TestValidateTone:
    """Test cases for tone validation."""

    def test_valid_tones(self):
        """Test validation of valid tones."""
        assert validate_tone("formal") is True
        assert validate_tone("friendly") is True
        assert validate_tone("assertive") is True

    def test_case_insensitive(self):
        """Test case-insensitive validation."""
        assert validate_tone("FORMAL") is True
        assert validate_tone("Friendly") is True

    def test_invalid_tones(self):
        """Test validation of invalid tones."""
        assert validate_tone("angry") is False
        assert validate_tone("polite") is False
        assert validate_tone("") is False


class TestGetAvailableTones:
    """Test cases for available tones list."""

    def test_returns_list(self):
        """Test that list is returned."""
        tones = get_available_tones()

        assert isinstance(tones, list)
        assert len(tones) == 3

    def test_contains_all_tones(self):
        """Test that all tones are included."""
        tones = get_available_tones()

        assert "formal" in tones
        assert "friendly" in tones
        assert "assertive" in tones


class TestIntegration:
    """Integration tests for complete letter generation."""

    def test_complete_formal_letter_flow(
        self,
        sample_audit_json: dict,
        sample_patient_info: dict,
    ):
        """Test complete formal letter generation."""
        # Use mock provider for predictable output
        mock_provider = MockProvider()

        letter = generate_letter(
            sample_audit_json,
            tone="formal",
            provider=mock_provider,
            patient_info=sample_patient_info,
        )

        # Verify it's a complete letter
        assert len(letter) > 200
        assert "John Michael Smith" in letter

    def test_complete_assertive_letter_flow(
        self,
        sample_audit_json: dict,
    ):
        """Test complete assertive letter generation."""
        # Use fallback path
        failing_provider = MockProvider()
        failing_provider.generate = MagicMock(
            side_effect=Exception("Error")
        )

        letter = generate_letter(
            sample_audit_json,
            tone="assertive",
            provider=failing_provider,
        )

        # Verify assertive elements
        assert "30 days" in letter
        assert len(letter) > 200

    def test_letter_suitable_for_sending(
        self,
        sample_audit_json: dict,
        sample_patient_info: dict,
    ):
        """Test that generated letter is suitable for sending."""
        letter = generate_letter(
            sample_audit_json,
            tone="formal",
            patient_info=sample_patient_info,
        )

        # Should have standard letter components
        has_date = any(
            month in letter
            for month in [
                "January", "February", "March", "April",
                "May", "June", "July", "August",
                "September", "October", "November", "December",
            ]
        )
        has_salutation = "Dear" in letter or "Hello" in letter or "To Whom" in letter
        has_closing = (
            "Sincerely" in letter or
            "Regards" in letter or
            "Thank you" in letter
        )

        assert has_date or "2024" in letter or "2025" in letter
        assert has_salutation
        assert has_closing

