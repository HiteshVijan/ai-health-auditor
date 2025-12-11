"""
Field extraction and parsing utilities for medical bills.

Provides functions for extracting structured fields from OCR text
and tables using regex patterns and fuzzy matching.
"""

import re
import logging
from datetime import datetime
from typing import Optional, TypedDict
from dataclasses import dataclass

import pandas as pd
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)


class FieldResult(TypedDict):
    """Type definition for a single extracted field."""

    value: Optional[str]
    confidence: float
    source: str  # "regex", "fuzzy", "table", or "not_found"


class ParsedFields(TypedDict):
    """Type definition for all parsed fields."""

    total_amount: FieldResult
    invoice_number: FieldResult
    patient_name: FieldResult
    bill_date: FieldResult


# Field label variations for fuzzy matching
FIELD_LABELS = {
    "total_amount": [
        "total amount",
        "total due",
        "amount due",
        "total charges",
        "balance due",
        "total",
        "grand total",
        "amount owed",
        "total balance",
        "patient responsibility",
    ],
    "invoice_number": [
        "invoice number",
        "invoice #",
        "invoice no",
        "bill number",
        "bill #",
        "account number",
        "account #",
        "statement number",
        "reference number",
        "claim number",
    ],
    "patient_name": [
        "patient name",
        "patient",
        "name",
        "patient:",
        "member name",
        "subscriber name",
        "insured name",
        "guarantor",
    ],
    "bill_date": [
        "date",
        "bill date",
        "statement date",
        "invoice date",
        "date of service",
        "service date",
        "dos",
        "date issued",
    ],
}

# Regex patterns for field extraction
PATTERNS = {
    "total_amount": [
        r"(?:total|amount\s*due|balance\s*due|grand\s*total)[:\s]*\$?\s*([\d,]+\.?\d{0,2})",
        r"\$\s*([\d,]+\.\d{2})\s*(?:total|due|owed)",
        r"(?:total|due)[:\s]*\$\s*([\d,]+\.\d{2})",
        r"\$\s*([\d,]+\.\d{2})(?:\s*$|\s+(?:USD|usd))",
    ],
    "invoice_number": [
        r"(?:invoice|bill|account|statement|claim|ref)[\s#:]*(?:number|no|#)?[:\s#]*([A-Z0-9\-]{4,20})",
        r"(?:inv|acct|stmt)[#:\s]*([A-Z0-9\-]{4,20})",
        r"#\s*([A-Z0-9\-]{6,20})",
    ],
    "patient_name": [
        r"(?:patient|member|subscriber|insured)[\s:]*name[:\s]*([A-Za-z]+(?:\s+[A-Za-z]+){1,3})",
        r"(?:patient|name)[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:dear|mr\.?|mrs\.?|ms\.?)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
    ],
    "bill_date": [
        r"(?:date|statement\s*date|bill\s*date|invoice\s*date)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        r"(?:date|statement\s*date|bill\s*date)[:\s]*([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})",
        r"(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})",
    ],
}


def parse_fields(
    page_texts: list[str],
    tables: list[pd.DataFrame],
) -> ParsedFields:
    """
    Extract structured fields from page texts and tables.

    Combines regex pattern matching and fuzzy matching to extract
    key billing fields with confidence scores.

    Args:
        page_texts: List of OCR-extracted text strings, one per page.
        tables: List of DataFrames extracted from the document.

    Returns:
        ParsedFields: Dictionary containing extracted fields with:
            - value: The extracted value or None if not found.
            - confidence: Confidence score (0.0 to 1.0).
            - source: Extraction method used.

    Example:
        >>> texts = ["Invoice #12345\\nPatient: John Doe\\nTotal: $150.00"]
        >>> tables = []
        >>> result = parse_fields(texts, tables)
        >>> print(result["total_amount"]["value"])
        "150.00"
    """
    # Combine all page texts
    full_text = "\n".join(page_texts)

    # Extract each field
    result: ParsedFields = {
        "total_amount": _extract_total_amount(full_text, tables),
        "invoice_number": _extract_invoice_number(full_text, tables),
        "patient_name": _extract_patient_name(full_text, tables),
        "bill_date": _extract_bill_date(full_text, tables),
    }

    # Log extraction results
    for field, data in result.items():
        if data["value"]:
            logger.info(
                f"Extracted {field}: {data['value']} "
                f"(confidence: {data['confidence']:.2f}, source: {data['source']})"
            )
        else:
            logger.warning(f"Could not extract {field}")

    return result


def _extract_total_amount(
    text: str,
    tables: list[pd.DataFrame],
) -> FieldResult:
    """
    Extract total amount from text and tables.

    Args:
        text: Combined page text.
        tables: Extracted tables.

    Returns:
        FieldResult: Extracted amount with confidence.
    """
    # Try regex first
    for pattern in PATTERNS["total_amount"]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).replace(",", "")
            return FieldResult(
                value=value,
                confidence=0.9,
                source="regex",
            )

    # Try fuzzy matching in text
    result = _fuzzy_extract_value(text, FIELD_LABELS["total_amount"])
    if result:
        # Look for dollar amount near the matched label
        amount_match = re.search(r"\$?\s*([\d,]+\.\d{2})", result)
        if amount_match:
            return FieldResult(
                value=amount_match.group(1).replace(",", ""),
                confidence=0.7,
                source="fuzzy",
            )

    # Try tables
    table_result = _search_tables_for_amount(tables)
    if table_result:
        return table_result

    return FieldResult(value=None, confidence=0.0, source="not_found")


def _extract_invoice_number(
    text: str,
    tables: list[pd.DataFrame],
) -> FieldResult:
    """
    Extract invoice/bill number from text and tables.

    Args:
        text: Combined page text.
        tables: Extracted tables.

    Returns:
        FieldResult: Extracted invoice number with confidence.
    """
    # Try regex patterns
    for pattern in PATTERNS["invoice_number"]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if len(value) >= 4:  # Minimum length validation
                return FieldResult(
                    value=value,
                    confidence=0.85,
                    source="regex",
                )

    # Try fuzzy matching
    result = _fuzzy_extract_value(text, FIELD_LABELS["invoice_number"])
    if result:
        # Look for alphanumeric ID near the label
        id_match = re.search(r"[:\s#]*([A-Z0-9\-]{4,20})", result, re.IGNORECASE)
        if id_match:
            return FieldResult(
                value=id_match.group(1).upper(),
                confidence=0.65,
                source="fuzzy",
            )

    return FieldResult(value=None, confidence=0.0, source="not_found")


def _extract_patient_name(
    text: str,
    tables: list[pd.DataFrame],
) -> FieldResult:
    """
    Extract patient name from text and tables.

    Args:
        text: Combined page text.
        tables: Extracted tables.

    Returns:
        FieldResult: Extracted patient name with confidence.
    """
    # Try regex patterns
    for pattern in PATTERNS["patient_name"]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Validate name format (at least 2 words)
            if len(name.split()) >= 2:
                return FieldResult(
                    value=_normalize_name(name),
                    confidence=0.85,
                    source="regex",
                )

    # Try fuzzy matching
    result = _fuzzy_extract_value(text, FIELD_LABELS["patient_name"])
    if result:
        # Extract name after label
        name_match = re.search(
            r"[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            result,
            re.IGNORECASE,
        )
        if name_match:
            return FieldResult(
                value=_normalize_name(name_match.group(1)),
                confidence=0.6,
                source="fuzzy",
            )

    # Try tables for patient info
    table_result = _search_tables_for_patient(tables)
    if table_result:
        return table_result

    return FieldResult(value=None, confidence=0.0, source="not_found")


def _extract_bill_date(
    text: str,
    tables: list[pd.DataFrame],
) -> FieldResult:
    """
    Extract bill/statement date from text and tables.

    Args:
        text: Combined page text.
        tables: Extracted tables.

    Returns:
        FieldResult: Extracted date with confidence.
    """
    # Try regex patterns
    for pattern in PATTERNS["bill_date"]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            normalized = _normalize_date(date_str)
            if normalized:
                return FieldResult(
                    value=normalized,
                    confidence=0.9,
                    source="regex",
                )

    # Try fuzzy matching
    result = _fuzzy_extract_value(text, FIELD_LABELS["bill_date"])
    if result:
        # Look for date pattern near label
        date_match = re.search(
            r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            result,
        )
        if date_match:
            normalized = _normalize_date(date_match.group(1))
            if normalized:
                return FieldResult(
                    value=normalized,
                    confidence=0.7,
                    source="fuzzy",
                )

    return FieldResult(value=None, confidence=0.0, source="not_found")


def _fuzzy_extract_value(
    text: str,
    labels: list[str],
    threshold: int = 80,
) -> Optional[str]:
    """
    Use fuzzy matching to find field labels and extract surrounding text.

    Args:
        text: Text to search in.
        labels: List of possible field labels.
        threshold: Minimum fuzzy match score (0-100).

    Returns:
        Optional[str]: Text surrounding the matched label, or None.
    """
    lines = text.split("\n")

    for line in lines:
        line_lower = line.lower().strip()
        if not line_lower:
            continue

        # Check each label
        for label in labels:
            # Use partial ratio for substring matching
            score = fuzz.partial_ratio(label.lower(), line_lower)
            if score >= threshold:
                return line

    # Try process.extractOne for best match across all lines
    all_lines = [l.strip() for l in lines if l.strip()]
    if all_lines:
        for label in labels:
            result = process.extractOne(
                label,
                all_lines,
                scorer=fuzz.partial_ratio,
                score_cutoff=threshold,
            )
            if result:
                return result[0]

    return None


def _search_tables_for_amount(tables: list[pd.DataFrame]) -> Optional[FieldResult]:
    """
    Search tables for total amount.

    Args:
        tables: List of extracted tables.

    Returns:
        Optional[FieldResult]: Extracted amount or None.
    """
    amount_labels = ["total", "amount", "due", "balance", "grand total"]

    for df in tables:
        # Search in column headers
        for col in df.columns:
            col_lower = str(col).lower()
            if any(label in col_lower for label in amount_labels):
                # Get the last non-empty value (usually the total)
                values = df[col].dropna()
                if len(values) > 0:
                    value = str(values.iloc[-1])
                    amount_match = re.search(r"[\$]?([\d,]+\.?\d{0,2})", value)
                    if amount_match:
                        return FieldResult(
                            value=amount_match.group(1).replace(",", ""),
                            confidence=0.8,
                            source="table",
                        )

        # Search in first column for label, second for value
        if len(df.columns) >= 2:
            for idx, row in df.iterrows():
                cell = str(row.iloc[0]).lower()
                if any(label in cell for label in amount_labels):
                    value = str(row.iloc[-1])
                    amount_match = re.search(r"[\$]?([\d,]+\.?\d{0,2})", value)
                    if amount_match:
                        return FieldResult(
                            value=amount_match.group(1).replace(",", ""),
                            confidence=0.75,
                            source="table",
                        )

    return None


def _search_tables_for_patient(tables: list[pd.DataFrame]) -> Optional[FieldResult]:
    """
    Search tables for patient name.

    Args:
        tables: List of extracted tables.

    Returns:
        Optional[FieldResult]: Extracted patient name or None.
    """
    patient_labels = ["patient", "name", "member", "subscriber"]

    for df in tables:
        if len(df.columns) >= 2:
            for idx, row in df.iterrows():
                cell = str(row.iloc[0]).lower()
                if any(label in cell for label in patient_labels):
                    value = str(row.iloc[1]).strip()
                    if len(value.split()) >= 2:
                        return FieldResult(
                            value=_normalize_name(value),
                            confidence=0.75,
                            source="table",
                        )

    return None


def _normalize_name(name: str) -> str:
    """
    Normalize a person's name to title case.

    Args:
        name: Raw name string.

    Returns:
        str: Normalized name.
    """
    # Remove extra whitespace
    name = " ".join(name.split())
    # Title case
    return name.title()


def _normalize_date(date_str: str) -> Optional[str]:
    """
    Normalize date string to ISO format (YYYY-MM-DD).

    Args:
        date_str: Raw date string.

    Returns:
        Optional[str]: ISO formatted date or None if parsing fails.
    """
    date_formats = [
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%Y-%m-%d",
        "%m/%d/%y",
        "%m-%d-%y",
        "%B %d, %Y",
        "%B %d %Y",
        "%b %d, %Y",
        "%b %d %Y",
    ]

    for fmt in date_formats:
        try:
            parsed = datetime.strptime(date_str.strip(), fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None

