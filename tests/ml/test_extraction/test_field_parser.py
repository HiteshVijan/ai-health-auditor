"""
Unit tests for field parsing utilities.

Tests the parse_fields function with synthetic medical bill text.
"""

import pytest
import pandas as pd
import sys
import os

# Add ml directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml"))

from extraction.field_parser import (
    parse_fields,
    _extract_total_amount,
    _extract_invoice_number,
    _extract_patient_name,
    _extract_bill_date,
    _fuzzy_extract_value,
    _normalize_name,
    _normalize_date,
    _search_tables_for_amount,
    ParsedFields,
    FieldResult,
    FIELD_LABELS,
)


@pytest.fixture
def sample_bill_text() -> list[str]:
    """Create sample medical bill text."""
    return [
        """
        CITYVIEW MEDICAL CENTER
        123 Healthcare Blvd, Suite 100
        Medical City, ST 12345

        Statement Date: 01/15/2024
        Invoice #: INV-2024-00123

        Patient Name: John Michael Smith
        Account Number: ACC-789456

        BILLING SUMMARY
        ===============
        Office Visit (99213).............$150.00
        Laboratory - CBC (85025)..........$45.00
        Laboratory - Metabolic (80053)....$89.00

        Subtotal:         $284.00
        Insurance Paid:   -$200.00
        Adjustments:      -$34.00

        TOTAL AMOUNT DUE: $50.00

        Please remit payment within 30 days.
        Thank you for choosing Cityview Medical Center.
        """
    ]


@pytest.fixture
def sample_table() -> pd.DataFrame:
    """Create a sample billing table DataFrame."""
    return pd.DataFrame({
        "Description": ["Office Visit", "CBC", "Metabolic Panel", "Total Due"],
        "Code": ["99213", "85025", "80053", ""],
        "Amount": ["$150.00", "$45.00", "$89.00", "$284.00"],
    })


@pytest.fixture
def minimal_bill_text() -> list[str]:
    """Create minimal bill text for edge case testing."""
    return [
        """
        Invoice: 12345
        Date: 2024-01-15
        Patient: Jane Doe
        Total: $100.00
        """
    ]


class TestParseFields:
    """Test cases for main parse_fields function."""

    def test_extracts_all_fields(self, sample_bill_text: list[str]):
        """Test extraction of all required fields."""
        result = parse_fields(sample_bill_text, [])

        assert "total_amount" in result
        assert "invoice_number" in result
        assert "patient_name" in result
        assert "bill_date" in result

    def test_field_structure(self, sample_bill_text: list[str]):
        """Test that each field has correct structure."""
        result = parse_fields(sample_bill_text, [])

        for field_name, field_data in result.items():
            assert "value" in field_data
            assert "confidence" in field_data
            assert "source" in field_data
            assert isinstance(field_data["confidence"], float)
            assert 0.0 <= field_data["confidence"] <= 1.0

    def test_extracts_total_amount(self, sample_bill_text: list[str]):
        """Test total amount extraction."""
        result = parse_fields(sample_bill_text, [])

        assert result["total_amount"]["value"] == "50.00"
        assert result["total_amount"]["confidence"] >= 0.7
        assert result["total_amount"]["source"] in ["regex", "fuzzy", "table"]

    def test_extracts_invoice_number(self, sample_bill_text: list[str]):
        """Test invoice number extraction."""
        result = parse_fields(sample_bill_text, [])

        assert result["invoice_number"]["value"] is not None
        assert "INV" in result["invoice_number"]["value"] or "2024" in result["invoice_number"]["value"]
        assert result["invoice_number"]["confidence"] >= 0.6

    def test_extracts_patient_name(self, sample_bill_text: list[str]):
        """Test patient name extraction."""
        result = parse_fields(sample_bill_text, [])

        assert result["patient_name"]["value"] is not None
        assert "John" in result["patient_name"]["value"] or "Smith" in result["patient_name"]["value"]
        assert result["patient_name"]["confidence"] >= 0.6

    def test_extracts_bill_date(self, sample_bill_text: list[str]):
        """Test bill date extraction."""
        result = parse_fields(sample_bill_text, [])

        assert result["bill_date"]["value"] is not None
        assert result["bill_date"]["value"] == "2024-01-15"
        assert result["bill_date"]["confidence"] >= 0.7

    def test_handles_empty_input(self):
        """Test handling of empty input."""
        result = parse_fields([], [])

        for field_data in result.values():
            assert field_data["source"] == "not_found"
            assert field_data["confidence"] == 0.0

    def test_uses_tables_for_extraction(self, sample_table: pd.DataFrame):
        """Test that tables are used when text extraction fails."""
        # Minimal text without amount
        text = ["Invoice #12345\nPatient: John Doe"]

        result = parse_fields(text, [sample_table])

        # Should find amount from table
        assert result["total_amount"]["value"] is not None


class TestExtractTotalAmount:
    """Test cases for total amount extraction."""

    def test_regex_extraction(self):
        """Test regex pattern matching for amounts."""
        text = "Total Amount Due: $1,234.56"
        result = _extract_total_amount(text, [])

        assert result["value"] == "1234.56"
        assert result["source"] == "regex"
        assert result["confidence"] >= 0.8

    def test_various_formats(self):
        """Test various amount formats."""
        test_cases = [
            ("Total: $100.00", "100.00"),
            ("Amount Due: $1,500.00", "1500.00"),
            ("Balance Due $250.00", "250.00"),
            ("Grand Total: $99.99", "99.99"),
        ]

        for text, expected in test_cases:
            result = _extract_total_amount(text, [])
            assert result["value"] == expected, f"Failed for: {text}"

    def test_table_extraction(self, sample_table: pd.DataFrame):
        """Test extraction from table."""
        result = _extract_total_amount("no amount here", [sample_table])

        assert result["value"] is not None
        assert result["source"] == "table"


class TestExtractInvoiceNumber:
    """Test cases for invoice number extraction."""

    def test_regex_extraction(self):
        """Test regex pattern matching for invoice numbers."""
        text = "Invoice Number: INV-2024-00123"
        result = _extract_invoice_number(text, [])

        assert result["value"] is not None
        assert result["source"] == "regex"

    def test_various_formats(self):
        """Test various invoice number formats."""
        test_cases = [
            "Invoice #: 12345678",
            "Bill Number: BILL-001",
            "Account #: ACC-789456",
            "Claim Number: CLM2024001",
        ]

        for text in test_cases:
            result = _extract_invoice_number(text, [])
            assert result["value"] is not None, f"Failed for: {text}"

    def test_minimum_length_validation(self):
        """Test that short invoice numbers are rejected."""
        text = "Invoice #: 123"  # Too short
        result = _extract_invoice_number(text, [])

        # Should not match due to minimum length
        assert result["confidence"] < 0.8 or result["value"] is None or len(result["value"]) >= 4


class TestExtractPatientName:
    """Test cases for patient name extraction."""

    def test_regex_extraction(self):
        """Test regex pattern matching for patient names."""
        text = "Patient Name: John Michael Smith"
        result = _extract_patient_name(text, [])

        assert result["value"] is not None
        assert "John" in result["value"]
        assert result["source"] == "regex"

    def test_name_normalization(self):
        """Test that names are properly normalized."""
        text = "Patient: JANE DOE"
        result = _extract_patient_name(text, [])

        if result["value"]:
            assert result["value"] == "Jane Doe"

    def test_requires_multiple_words(self):
        """Test that single-word names are rejected."""
        text = "Patient: John"
        result = _extract_patient_name(text, [])

        # Should have low confidence for single word
        assert result["confidence"] < 0.8


class TestExtractBillDate:
    """Test cases for bill date extraction."""

    def test_regex_extraction(self):
        """Test regex pattern matching for dates."""
        text = "Statement Date: 01/15/2024"
        result = _extract_bill_date(text, [])

        assert result["value"] == "2024-01-15"
        assert result["source"] == "regex"

    def test_various_date_formats(self):
        """Test various date formats."""
        test_cases = [
            ("Date: 01/15/2024", "2024-01-15"),
            ("Bill Date: 2024-01-15", "2024-01-15"),
            ("Invoice Date: January 15, 2024", "2024-01-15"),
            ("Date: 01-15-2024", "2024-01-15"),
        ]

        for text, expected in test_cases:
            result = _extract_bill_date(text, [])
            assert result["value"] == expected, f"Failed for: {text}"


class TestFuzzyExtractValue:
    """Test cases for fuzzy matching."""

    def test_exact_match(self):
        """Test exact label matching."""
        text = "Total Amount: $100.00\nOther info"
        result = _fuzzy_extract_value(text, ["total amount"])

        assert result is not None
        assert "100.00" in result

    def test_fuzzy_match(self):
        """Test fuzzy label matching."""
        text = "Totl Amnt Due: $100.00"  # Typos
        result = _fuzzy_extract_value(text, ["total amount"], threshold=70)

        assert result is not None

    def test_no_match(self):
        """Test when no match is found."""
        text = "Random unrelated text"
        result = _fuzzy_extract_value(text, ["total amount"], threshold=90)

        assert result is None


class TestNormalizeName:
    """Test cases for name normalization."""

    def test_title_case(self):
        """Test conversion to title case."""
        assert _normalize_name("john doe") == "John Doe"
        assert _normalize_name("JANE SMITH") == "Jane Smith"
        assert _normalize_name("John Michael Smith") == "John Michael Smith"

    def test_whitespace_handling(self):
        """Test whitespace normalization."""
        assert _normalize_name("John   Doe") == "John Doe"
        assert _normalize_name("  Jane Smith  ") == "Jane Smith"


class TestNormalizeDate:
    """Test cases for date normalization."""

    def test_us_format(self):
        """Test US date format (MM/DD/YYYY)."""
        assert _normalize_date("01/15/2024") == "2024-01-15"
        assert _normalize_date("12/31/2023") == "2023-12-31"

    def test_iso_format(self):
        """Test ISO date format (YYYY-MM-DD)."""
        assert _normalize_date("2024-01-15") == "2024-01-15"

    def test_text_format(self):
        """Test text date formats."""
        assert _normalize_date("January 15, 2024") == "2024-01-15"
        assert _normalize_date("Jan 15, 2024") == "2024-01-15"

    def test_invalid_date(self):
        """Test handling of invalid dates."""
        assert _normalize_date("not a date") is None
        assert _normalize_date("") is None


class TestSearchTablesForAmount:
    """Test cases for table amount search."""

    def test_finds_amount_in_column(self):
        """Test finding amount in table column."""
        df = pd.DataFrame({
            "Item": ["Service 1", "Service 2"],
            "Total": ["$100.00", "$200.00"],
        })

        result = _search_tables_for_amount([df])

        assert result is not None
        assert result["value"] == "200.00"  # Last value
        assert result["source"] == "table"

    def test_finds_amount_in_row(self):
        """Test finding amount in table row."""
        df = pd.DataFrame({
            "Label": ["Subtotal", "Tax", "Total Due"],
            "Amount": ["$100.00", "$10.00", "$110.00"],
        })

        result = _search_tables_for_amount([df])

        assert result is not None
        assert result["source"] == "table"

    def test_empty_tables(self):
        """Test with empty table list."""
        result = _search_tables_for_amount([])
        assert result is None


class TestIntegration:
    """Integration tests with realistic scenarios."""

    def test_complex_bill(self):
        """Test extraction from complex multi-page bill."""
        pages = [
            """
            HEALTHCARE BILLING SERVICES
            Page 1 of 2

            Account Number: HBS-2024-78901
            Patient: Sarah Jane Connor
            Date of Service: 02/28/2024
            """,
            """
            Page 2 of 2

            SUMMARY OF CHARGES

            Total Charges:     $2,500.00
            Insurance Payment: -$2,000.00
            Patient Co-pay:    -$50.00

            BALANCE DUE: $450.00

            Please pay by: 03/28/2024
            """,
        ]

        result = parse_fields(pages, [])

        assert result["total_amount"]["value"] == "450.00"
        assert result["patient_name"]["value"] is not None
        assert "Connor" in result["patient_name"]["value"] or "Sarah" in result["patient_name"]["value"]

    def test_mixed_sources(self):
        """Test extraction using both text and tables."""
        text = ["Patient Name: Robert Johnson"]
        tables = [
            pd.DataFrame({
                "Description": ["Office Visit", "Total"],
                "Amount": ["$100.00", "$100.00"],
            })
        ]

        result = parse_fields(text, tables)

        # Patient from text
        assert result["patient_name"]["value"] is not None
        # Amount from table
        assert result["total_amount"]["value"] is not None

