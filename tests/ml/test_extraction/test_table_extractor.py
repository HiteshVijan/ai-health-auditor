"""
Unit tests for table extraction utilities.

Tests the extract_tables_from_pdf function with mocked PDF libraries.
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import os
import sys

# Add ml directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml"))

from extraction.table_extractor import (
    extract_tables_from_pdf,
    _extract_with_camelot,
    _extract_with_pdfplumber,
    _parse_page_spec,
    _clean_dataframe,
    get_table_summary,
)


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Create a sample medical bill table DataFrame."""
    return pd.DataFrame({
        "Code": ["99213", "85025", "80053"],
        "Description": ["Office Visit", "CBC", "Metabolic Panel"],
        "Quantity": ["1", "1", "1"],
        "Amount": ["$150.00", "$45.00", "$89.00"],
    })


@pytest.fixture
def sample_pdf_path(tmp_path) -> str:
    """Create a temporary PDF file path."""
    pdf_path = tmp_path / "sample_bill.pdf"
    # Create an empty file to pass existence check
    pdf_path.write_bytes(b"%PDF-1.4 fake pdf")
    return str(pdf_path)


@pytest.fixture
def mock_camelot_table(sample_dataframe):
    """Create a mock Camelot table object."""
    mock_table = MagicMock()
    mock_table.df = sample_dataframe
    return mock_table


@pytest.fixture
def mock_camelot_tables(mock_camelot_table):
    """Create a mock Camelot TableList."""
    mock_table_list = MagicMock()
    mock_table_list.__len__ = MagicMock(return_value=1)
    mock_table_list.__iter__ = MagicMock(return_value=iter([mock_camelot_table]))
    return mock_table_list


class TestExtractTablesFromPdf:
    """Test cases for extract_tables_from_pdf function."""

    def test_raises_file_not_found(self):
        """Test that FileNotFoundError is raised for missing files."""
        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            extract_tables_from_pdf("/nonexistent/path/file.pdf")

    def test_raises_value_error_for_non_pdf(self, tmp_path):
        """Test that ValueError is raised for non-PDF files."""
        txt_file = tmp_path / "document.txt"
        txt_file.write_text("not a pdf")

        with pytest.raises(ValueError, match="Invalid file type"):
            extract_tables_from_pdf(str(txt_file))

    def test_uses_camelot_first(
        self,
        sample_pdf_path: str,
        mock_camelot_tables,
        sample_dataframe: pd.DataFrame,
    ):
        """Test that Camelot is used as primary extractor."""
        with patch("extraction.table_extractor.camelot") as mock_camelot:
            mock_camelot.read_pdf.return_value = mock_camelot_tables

            tables = extract_tables_from_pdf(sample_pdf_path)

            mock_camelot.read_pdf.assert_called()
            assert len(tables) == 1
            assert tables[0].equals(sample_dataframe)

    def test_falls_back_to_pdfplumber(
        self,
        sample_pdf_path: str,
        sample_dataframe: pd.DataFrame,
    ):
        """Test fallback to pdfplumber when Camelot finds no tables."""
        empty_table_list = MagicMock()
        empty_table_list.__len__ = MagicMock(return_value=0)
        empty_table_list.__iter__ = MagicMock(return_value=iter([]))

        with patch("extraction.table_extractor.camelot") as mock_camelot, \
             patch("extraction.table_extractor.pdfplumber") as mock_pdfplumber:

            mock_camelot.read_pdf.return_value = empty_table_list

            # Setup pdfplumber mock
            mock_page = MagicMock()
            mock_page.extract_tables.return_value = [
                [
                    ["Code", "Description", "Amount"],
                    ["99213", "Office Visit", "$150.00"],
                ]
            ]

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)

            mock_pdfplumber.open.return_value = mock_pdf

            tables = extract_tables_from_pdf(sample_pdf_path)

            # Verify pdfplumber was used
            mock_pdfplumber.open.assert_called_once_with(sample_pdf_path)
            assert len(tables) == 1

    def test_returns_empty_list_when_no_tables(
        self,
        sample_pdf_path: str,
    ):
        """Test that empty list is returned when no tables found."""
        empty_table_list = MagicMock()
        empty_table_list.__len__ = MagicMock(return_value=0)
        empty_table_list.__iter__ = MagicMock(return_value=iter([]))

        with patch("extraction.table_extractor.camelot") as mock_camelot, \
             patch("extraction.table_extractor.pdfplumber") as mock_pdfplumber:

            mock_camelot.read_pdf.return_value = empty_table_list

            mock_page = MagicMock()
            mock_page.extract_tables.return_value = []

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)

            mock_pdfplumber.open.return_value = mock_pdf

            tables = extract_tables_from_pdf(sample_pdf_path)

            assert tables == []

    def test_logs_table_count(
        self,
        sample_pdf_path: str,
        mock_camelot_tables,
        caplog,
    ):
        """Test that number of tables is logged."""
        import logging

        with patch("extraction.table_extractor.camelot") as mock_camelot:
            mock_camelot.read_pdf.return_value = mock_camelot_tables

            with caplog.at_level(logging.INFO):
                extract_tables_from_pdf(sample_pdf_path)

            assert "1 table(s)" in caplog.text


class TestExtractWithCamelot:
    """Test cases for Camelot extraction."""

    def test_tries_stream_if_lattice_fails(
        self,
        sample_pdf_path: str,
        mock_camelot_table,
    ):
        """Test that stream flavor is tried if lattice finds nothing."""
        empty_list = MagicMock()
        empty_list.__len__ = MagicMock(return_value=0)
        empty_list.__iter__ = MagicMock(return_value=iter([]))

        stream_list = MagicMock()
        stream_list.__len__ = MagicMock(return_value=1)
        stream_list.__iter__ = MagicMock(return_value=iter([mock_camelot_table]))

        with patch("extraction.table_extractor.camelot") as mock_camelot:
            mock_camelot.read_pdf.side_effect = [empty_list, stream_list]

            tables = _extract_with_camelot(sample_pdf_path, "all", "lattice")

            assert mock_camelot.read_pdf.call_count == 2
            assert len(tables) == 1

    def test_returns_empty_on_exception(self, sample_pdf_path: str):
        """Test that empty list is returned on Camelot exception."""
        with patch("extraction.table_extractor.camelot") as mock_camelot:
            mock_camelot.read_pdf.side_effect = Exception("Camelot error")

            tables = _extract_with_camelot(sample_pdf_path, "all", "lattice")

            assert tables == []


class TestExtractWithPdfplumber:
    """Test cases for pdfplumber extraction."""

    def test_extracts_tables_from_multiple_pages(self, sample_pdf_path: str):
        """Test extraction from multiple pages."""
        with patch("extraction.table_extractor.pdfplumber") as mock_pdfplumber:
            mock_page1 = MagicMock()
            mock_page1.extract_tables.return_value = [
                [["Header1"], ["Value1"]]
            ]

            mock_page2 = MagicMock()
            mock_page2.extract_tables.return_value = [
                [["Header2"], ["Value2"]]
            ]

            mock_pdf = MagicMock()
            mock_pdf.pages = [mock_page1, mock_page2]
            mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
            mock_pdf.__exit__ = MagicMock(return_value=False)

            mock_pdfplumber.open.return_value = mock_pdf

            tables = _extract_with_pdfplumber(sample_pdf_path, "all")

            assert len(tables) == 2

    def test_returns_empty_on_exception(self, sample_pdf_path: str):
        """Test that empty list is returned on pdfplumber exception."""
        with patch("extraction.table_extractor.pdfplumber") as mock_pdfplumber:
            mock_pdfplumber.open.side_effect = Exception("pdfplumber error")

            tables = _extract_with_pdfplumber(sample_pdf_path, "all")

            assert tables == []


class TestParsePageSpec:
    """Test cases for page specification parsing."""

    def test_parse_all_pages(self):
        """Test parsing 'all' page specification."""
        result = _parse_page_spec("all", 5)
        assert result == [0, 1, 2, 3, 4]

    def test_parse_single_page(self):
        """Test parsing single page number."""
        result = _parse_page_spec("2", 5)
        assert result == [1]

    def test_parse_comma_separated(self):
        """Test parsing comma-separated pages."""
        result = _parse_page_spec("1,3,5", 5)
        assert result == [0, 2, 4]

    def test_parse_range(self):
        """Test parsing page range."""
        result = _parse_page_spec("2-4", 5)
        assert result == [1, 2, 3]

    def test_parse_mixed(self):
        """Test parsing mixed specification."""
        result = _parse_page_spec("1,3-5", 6)
        assert result == [0, 2, 3, 4]

    def test_ignores_out_of_range(self):
        """Test that out-of-range pages are ignored."""
        result = _parse_page_spec("10", 5)
        assert result == []


class TestCleanDataframe:
    """Test cases for DataFrame cleaning."""

    def test_removes_empty_rows(self):
        """Test that empty rows are removed."""
        df = pd.DataFrame({
            "A": ["value", None, "value2"],
            "B": ["data", None, "data2"],
        })
        result = _clean_dataframe(df)
        assert len(result) == 2

    def test_removes_empty_columns(self):
        """Test that empty columns are removed."""
        df = pd.DataFrame({
            "A": ["value", "value2"],
            "B": [None, None],
        })
        result = _clean_dataframe(df)
        assert "B" not in result.columns

    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        df = pd.DataFrame({
            "A": ["  value  ", "value2"],
        })
        result = _clean_dataframe(df)
        assert result["A"].iloc[0] == "value"


class TestGetTableSummary:
    """Test cases for table summary generation."""

    def test_generates_summary(self, sample_dataframe: pd.DataFrame):
        """Test summary generation."""
        tables = [sample_dataframe]
        summary = get_table_summary(tables)

        assert summary["table_count"] == 1
        assert len(summary["tables"]) == 1
        assert summary["tables"][0]["rows"] == 3
        assert summary["tables"][0]["columns"] == 4

    def test_empty_tables_list(self):
        """Test summary for empty tables list."""
        summary = get_table_summary([])
        assert summary["table_count"] == 0
        assert summary["tables"] == []


class TestIntegration:
    """Integration tests with sample PDF (requires actual PDF)."""

    @pytest.fixture
    def create_sample_pdf(self, tmp_path) -> str:
        """
        Create a sample PDF with a table for integration testing.

        Requires reportlab to be installed.
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
            from reportlab.lib import colors

            pdf_path = tmp_path / "test_table.pdf"

            doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
            elements = []

            # Create a sample table
            data = [
                ["CPT Code", "Description", "Amount"],
                ["99213", "Office Visit", "$150.00"],
                ["85025", "CBC", "$45.00"],
                ["80053", "Metabolic Panel", "$89.00"],
            ]

            table = Table(data)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(table)

            doc.build(elements)
            return str(pdf_path)

        except ImportError:
            pytest.skip("reportlab not installed")

    @pytest.mark.skipif(
        not os.environ.get("RUN_INTEGRATION_TESTS"),
        reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=1 to run.",
    )
    def test_extract_from_real_pdf(self, create_sample_pdf):
        """
        Test extraction from an actual PDF file.

        Enable by setting RUN_INTEGRATION_TESTS=1 environment variable.
        """
        tables = extract_tables_from_pdf(create_sample_pdf)

        assert len(tables) >= 1
        assert isinstance(tables[0], pd.DataFrame)

