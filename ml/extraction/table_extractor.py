"""
Table extraction utilities for PDF documents.

Provides functions for extracting tabular data from PDFs using
Camelot as the primary extractor with pdfplumber as fallback.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def extract_tables_from_pdf(
    file_path: str,
    pages: str = "all",
    flavor: str = "lattice",
) -> list[pd.DataFrame]:
    """
    Extract tables from a PDF file.

    Uses Camelot as the primary extraction method for high-quality
    table detection. Falls back to pdfplumber if Camelot fails or
    finds no tables.

    Args:
        file_path: Path to the PDF file.
        pages: Page numbers to process. Can be "all", "1", "1,2,3",
            or "1-3". Defaults to "all".
        flavor: Camelot extraction flavor - "lattice" for tables with
            borders, "stream" for borderless tables. Defaults to "lattice".

    Returns:
        list[pd.DataFrame]: List of DataFrames, one per extracted table.
            Returns empty list if no tables found.

    Raises:
        FileNotFoundError: If the PDF file does not exist.
        ValueError: If the file is not a valid PDF.

    Example:
        >>> tables = extract_tables_from_pdf("medical_bill.pdf")
        >>> for i, df in enumerate(tables):
        ...     print(f"Table {i+1}: {len(df)} rows")
    """
    # Validate file path
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Invalid file type. Expected PDF, got: {path.suffix}")

    logger.info(f"Extracting tables from: {file_path}")

    # Try Camelot first
    tables = _extract_with_camelot(file_path, pages, flavor)

    if tables:
        logger.info(f"Camelot extracted {len(tables)} table(s)")
        return tables

    # Fallback to pdfplumber
    logger.info("Camelot found no tables, falling back to pdfplumber")
    tables = _extract_with_pdfplumber(file_path, pages)

    logger.info(f"pdfplumber extracted {len(tables)} table(s)")
    return tables


def _extract_with_camelot(
    file_path: str,
    pages: str,
    flavor: str,
) -> list[pd.DataFrame]:
    """
    Extract tables using Camelot library.

    Args:
        file_path: Path to the PDF file.
        pages: Page specification string.
        flavor: Extraction flavor ("lattice" or "stream").

    Returns:
        list[pd.DataFrame]: Extracted tables as DataFrames.
    """
    try:
        import camelot

        # Extract tables with specified flavor
        tables = camelot.read_pdf(
            file_path,
            pages=pages,
            flavor=flavor,
            suppress_stdout=True,
        )

        if len(tables) == 0 and flavor == "lattice":
            # Try stream flavor if lattice finds nothing
            logger.debug("Lattice found no tables, trying stream flavor")
            tables = camelot.read_pdf(
                file_path,
                pages=pages,
                flavor="stream",
                suppress_stdout=True,
            )

        # Convert Camelot TableList to list of DataFrames
        result = []
        for table in tables:
            df = table.df
            # Clean up the DataFrame
            df = _clean_dataframe(df)
            if not df.empty:
                result.append(df)

        return result

    except Exception as e:
        logger.warning(f"Camelot extraction failed: {e}")
        return []


def _extract_with_pdfplumber(
    file_path: str,
    pages: str,
) -> list[pd.DataFrame]:
    """
    Extract tables using pdfplumber library.

    Args:
        file_path: Path to the PDF file.
        pages: Page specification string.

    Returns:
        list[pd.DataFrame]: Extracted tables as DataFrames.
    """
    try:
        import pdfplumber

        result = []

        with pdfplumber.open(file_path) as pdf:
            # Parse page specification
            page_indices = _parse_page_spec(pages, len(pdf.pages))

            for page_idx in page_indices:
                page = pdf.pages[page_idx]
                tables = page.extract_tables()

                for table in tables:
                    if table and len(table) > 0:
                        # Convert to DataFrame
                        df = pd.DataFrame(table[1:], columns=table[0])
                        df = _clean_dataframe(df)
                        if not df.empty:
                            result.append(df)

        return result

    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}")
        return []


def _parse_page_spec(pages: str, total_pages: int) -> list[int]:
    """
    Parse page specification string to list of page indices.

    Args:
        pages: Page spec like "all", "1", "1,2,3", or "1-3".
        total_pages: Total number of pages in the PDF.

    Returns:
        list[int]: Zero-indexed page numbers.
    """
    if pages.lower() == "all":
        return list(range(total_pages))

    indices = []
    for part in pages.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            start_idx = int(start) - 1
            end_idx = int(end)
            indices.extend(range(start_idx, min(end_idx, total_pages)))
        else:
            idx = int(part) - 1
            if 0 <= idx < total_pages:
                indices.append(idx)

    return sorted(set(indices))


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and normalize an extracted DataFrame.

    Args:
        df: Raw DataFrame from table extraction.

    Returns:
        pd.DataFrame: Cleaned DataFrame.
    """
    # Drop completely empty rows and columns
    df = df.dropna(how="all")
    df = df.dropna(axis=1, how="all")

    # Replace None with empty string
    df = df.fillna("")

    # Strip whitespace from string columns
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()

    # Remove rows that are all empty strings
    df = df[~(df == "").all(axis=1)]

    # Reset index
    df = df.reset_index(drop=True)

    return df


def get_table_summary(tables: list[pd.DataFrame]) -> dict:
    """
    Generate a summary of extracted tables.

    Args:
        tables: List of extracted DataFrames.

    Returns:
        dict: Summary with table count, row/column counts, and previews.
    """
    summary = {
        "table_count": len(tables),
        "tables": [],
    }

    for i, df in enumerate(tables):
        table_info = {
            "index": i,
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "preview": df.head(3).to_dict(orient="records"),
        }
        summary["tables"].append(table_info)

    return summary

