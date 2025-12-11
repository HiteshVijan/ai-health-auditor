"""
Tests for the medical code database service.

Tests validation, lookup, and pricing functions using sample data.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from ml.audit.medical_codes import (
    detect_code_type,
    validate_code,
    get_fair_price,
    get_indian_price,
    is_overpriced,
    get_code_description,
    search_codes,
    get_statistics,
    reload_database,
    CodeType,
    MedicalCodeDatabase,
)


class TestCodeTypeDetection:
    """Tests for code type detection."""

    def test_detect_cpt_code(self):
        """Test detection of CPT codes (5-digit numeric)."""
        assert detect_code_type("99213") == CodeType.CPT
        assert detect_code_type("85025") == CodeType.CPT
        assert detect_code_type("70553") == CodeType.CPT

    def test_detect_hcpcs_code(self):
        """Test detection of HCPCS Level II codes (letter + 4 digits)."""
        assert detect_code_type("A0021") == CodeType.HCPCS
        assert detect_code_type("J1234") == CodeType.HCPCS
        assert detect_code_type("G0101") == CodeType.HCPCS

    def test_detect_icd10_code(self):
        """Test detection of ICD-10 codes."""
        assert detect_code_type("E11.9") == CodeType.ICD10
        assert detect_code_type("I10") == CodeType.ICD10
        assert detect_code_type("M54.5") == CodeType.ICD10

    def test_detect_unknown_code(self):
        """Test handling of unknown code formats."""
        assert detect_code_type("") == CodeType.UNKNOWN
        assert detect_code_type("XYZ") == CodeType.UNKNOWN
        assert detect_code_type("12") == CodeType.UNKNOWN


class TestCodeValidation:
    """Tests for code validation."""

    def test_validate_empty_code(self):
        """Test validation of empty code."""
        result = validate_code("")
        assert not result["is_valid"]
        assert result["code_type"] == CodeType.UNKNOWN.value

    def test_validate_code_structure(self):
        """Test that validation returns correct structure."""
        result = validate_code("99213")
        assert "code" in result
        assert "code_type" in result
        assert "description" in result
        assert "category" in result
        assert "is_valid" in result


class TestPriceLookup:
    """Tests for price lookup functions."""

    def test_get_fair_price_empty_code(self):
        """Test price lookup with empty code."""
        result = get_fair_price("")
        assert result is None

    def test_price_info_structure(self):
        """Test that price info has correct structure when returned."""
        # This will depend on whether the database is loaded
        result = get_fair_price("99213")
        if result is not None:
            assert "code" in result
            assert "fair_price_low" in result
            assert "fair_price_median" in result
            assert "fair_price_high" in result
            assert "currency" in result


class TestOverpriceDetection:
    """Tests for overcharge detection."""

    def test_is_overpriced_no_data(self):
        """Test overpriced check when no pricing data available."""
        # Unknown code with no pricing data
        overpriced, fair_price, message = is_overpriced("XXXXX", 1000.0)
        assert not overpriced
        assert fair_price is None

    def test_is_overpriced_function_structure(self):
        """Test that is_overpriced returns correct tuple structure."""
        overpriced, fair_price, message = is_overpriced("99213", 100.0)
        assert isinstance(overpriced, bool)
        assert fair_price is None or isinstance(fair_price, (int, float))
        assert message is None or isinstance(message, str)


class TestIndianPricing:
    """Tests for Indian healthcare pricing."""

    def test_get_indian_price_no_data(self):
        """Test Indian price lookup when no procedure matches."""
        result = get_indian_price("", "unknown_procedure_xyz")
        # May or may not return data depending on database state
        # Just ensure no exception is raised
        assert result is None or isinstance(result, dict)


class TestCodeSearch:
    """Tests for code search functionality."""

    def test_search_codes_empty_query(self):
        """Test search with empty query."""
        results = search_codes("")
        assert isinstance(results, list)

    def test_search_codes_limit(self):
        """Test that search respects limit parameter."""
        results = search_codes("office", limit=5)
        assert len(results) <= 5


class TestDatabaseStatistics:
    """Tests for database statistics."""

    def test_get_statistics_structure(self):
        """Test that statistics returns correct structure."""
        stats = get_statistics()
        assert "loaded" in stats
        assert "icd10_count" in stats
        assert "cpt_hcpcs_count" in stats
        assert "fee_schedule_count" in stats
        assert "data_directory" in stats


class TestDatabaseLoading:
    """Tests for database loading."""

    def test_database_load_structure(self):
        """Test that database loads with correct structure."""
        db = MedicalCodeDatabase.load()
        assert hasattr(db, "icd10_codes")
        assert hasattr(db, "cpt_hcpcs_codes")
        assert hasattr(db, "fee_schedule")
        assert hasattr(db, "indian_rates")
        assert isinstance(db.icd10_codes, dict)
        assert isinstance(db.cpt_hcpcs_codes, dict)

    def test_reload_database(self):
        """Test that database can be reloaded."""
        db = reload_database()
        assert db is not None

