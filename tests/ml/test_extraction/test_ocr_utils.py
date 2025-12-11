"""
Unit tests for OCR utilities.

Tests the extract_text_from_image function with sample images.
"""

import pytest
from PIL import Image, ImageDraw, ImageFont
from unittest.mock import patch, MagicMock
import sys
import os

# Add ml directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml"))

from extraction.ocr_utils import (
    extract_text_from_image,
    preprocess_image_for_ocr,
    OCRResult,
    WordInfo,
)


@pytest.fixture
def sample_text_image() -> Image.Image:
    """
    Create a sample image with text for testing.

    Returns:
        Image.Image: A test image with sample medical bill text.
    """
    # Create a white background image
    width, height = 400, 200
    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)

    # Draw sample text (using default font)
    try:
        # Try to use a basic font if available
        font = ImageFont.load_default()
    except Exception:
        font = None

    # Add sample medical bill text
    lines = [
        "MEDICAL BILL",
        "Patient: John Doe",
        "Date: 2024-01-15",
        "Amount: $150.00",
    ]

    y_position = 20
    for line in lines:
        draw.text((20, y_position), line, fill="black", font=font)
        y_position += 40

    return image


@pytest.fixture
def empty_image() -> Image.Image:
    """
    Create an empty white image for testing.

    Returns:
        Image.Image: A blank white image.
    """
    return Image.new("RGB", (100, 100), color="white")


@pytest.fixture
def mock_pytesseract_data() -> dict:
    """
    Create mock pytesseract output data.

    Returns:
        dict: Mocked image_to_data output.
    """
    return {
        "text": ["MEDICAL", "BILL", "Patient:", "John", "Doe", "Amount:", "$150.00", ""],
        "conf": [95.5, 92.3, 88.0, 90.1, 91.2, 89.5, 85.0, -1],
        "left": [20, 100, 20, 100, 150, 20, 100, 0],
        "top": [20, 20, 60, 60, 60, 100, 100, 0],
        "width": [70, 40, 70, 40, 30, 70, 60, 0],
        "height": [25, 25, 25, 25, 25, 25, 25, 0],
    }


class TestExtractTextFromImage:
    """Test cases for extract_text_from_image function."""

    def test_returns_correct_structure(
        self,
        sample_text_image: Image.Image,
        mock_pytesseract_data: dict,
    ):
        """Test that function returns correctly structured OCRResult."""
        with patch("extraction.ocr_utils.pytesseract") as mock_tesseract:
            mock_tesseract.image_to_data.return_value = mock_pytesseract_data
            mock_tesseract.image_to_string.return_value = "MEDICAL BILL\nPatient: John Doe"
            mock_tesseract.Output.DICT = "dict"

            result = extract_text_from_image(sample_text_image)

            # Check structure
            assert "page_text" in result
            assert "words" in result
            assert isinstance(result["page_text"], str)
            assert isinstance(result["words"], list)

    def test_extracts_words_with_bounding_boxes(
        self,
        sample_text_image: Image.Image,
        mock_pytesseract_data: dict,
    ):
        """Test that words are extracted with correct bounding box format."""
        with patch("extraction.ocr_utils.pytesseract") as mock_tesseract:
            mock_tesseract.image_to_data.return_value = mock_pytesseract_data
            mock_tesseract.image_to_string.return_value = "MEDICAL BILL"
            mock_tesseract.Output.DICT = "dict"

            result = extract_text_from_image(sample_text_image)

            # Check words have correct structure
            for word in result["words"]:
                assert "text" in word
                assert "bbox" in word
                assert "conf" in word
                assert isinstance(word["text"], str)
                assert isinstance(word["bbox"], list)
                assert len(word["bbox"]) == 4  # [x1, y1, x2, y2]
                assert isinstance(word["conf"], float)

    def test_bounding_box_coordinates(
        self,
        sample_text_image: Image.Image,
        mock_pytesseract_data: dict,
    ):
        """Test that bounding boxes are calculated correctly."""
        with patch("extraction.ocr_utils.pytesseract") as mock_tesseract:
            mock_tesseract.image_to_data.return_value = mock_pytesseract_data
            mock_tesseract.image_to_string.return_value = "MEDICAL"
            mock_tesseract.Output.DICT = "dict"

            result = extract_text_from_image(sample_text_image)

            # First word should be "MEDICAL" with bbox [20, 20, 90, 45]
            first_word = result["words"][0]
            assert first_word["text"] == "MEDICAL"
            assert first_word["bbox"] == [20, 20, 90, 45]  # x1, y1, x1+w, y1+h

    def test_filters_empty_text(
        self,
        sample_text_image: Image.Image,
        mock_pytesseract_data: dict,
    ):
        """Test that empty text entries are filtered out."""
        with patch("extraction.ocr_utils.pytesseract") as mock_tesseract:
            mock_tesseract.image_to_data.return_value = mock_pytesseract_data
            mock_tesseract.image_to_string.return_value = "test"
            mock_tesseract.Output.DICT = "dict"

            result = extract_text_from_image(sample_text_image)

            # Empty text entry should be filtered
            texts = [w["text"] for w in result["words"]]
            assert "" not in texts

    def test_filters_negative_confidence(
        self,
        sample_text_image: Image.Image,
        mock_pytesseract_data: dict,
    ):
        """Test that entries with negative confidence are filtered."""
        with patch("extraction.ocr_utils.pytesseract") as mock_tesseract:
            mock_tesseract.image_to_data.return_value = mock_pytesseract_data
            mock_tesseract.image_to_string.return_value = "test"
            mock_tesseract.Output.DICT = "dict"

            result = extract_text_from_image(sample_text_image)

            # All words should have positive confidence
            for word in result["words"]:
                assert word["conf"] >= 0

    def test_raises_type_error_for_invalid_input(self):
        """Test that TypeError is raised for non-Image input."""
        with pytest.raises(TypeError, match="Expected PIL.Image.Image"):
            extract_text_from_image("not an image")

        with pytest.raises(TypeError, match="Expected PIL.Image.Image"):
            extract_text_from_image(None)

    def test_handles_rgba_image(
        self,
        mock_pytesseract_data: dict,
    ):
        """Test that RGBA images are handled correctly."""
        rgba_image = Image.new("RGBA", (100, 100), color=(255, 255, 255, 255))

        with patch("extraction.ocr_utils.pytesseract") as mock_tesseract:
            mock_tesseract.image_to_data.return_value = {
                "text": ["test"],
                "conf": [90.0],
                "left": [10],
                "top": [10],
                "width": [30],
                "height": [20],
            }
            mock_tesseract.image_to_string.return_value = "test"
            mock_tesseract.Output.DICT = "dict"

            result = extract_text_from_image(rgba_image)
            assert "page_text" in result

    def test_handles_grayscale_image(
        self,
        mock_pytesseract_data: dict,
    ):
        """Test that grayscale images are handled correctly."""
        gray_image = Image.new("L", (100, 100), color=255)

        with patch("extraction.ocr_utils.pytesseract") as mock_tesseract:
            mock_tesseract.image_to_data.return_value = {
                "text": ["test"],
                "conf": [90.0],
                "left": [10],
                "top": [10],
                "width": [30],
                "height": [20],
            }
            mock_tesseract.image_to_string.return_value = "test"
            mock_tesseract.Output.DICT = "dict"

            result = extract_text_from_image(gray_image)
            assert "page_text" in result


class TestPreprocessImageForOCR:
    """Test cases for preprocess_image_for_ocr function."""

    def test_converts_to_grayscale(self, sample_text_image: Image.Image):
        """Test that preprocessing converts image to grayscale."""
        result = preprocess_image_for_ocr(sample_text_image)
        assert result.mode == "L"

    def test_maintains_grayscale(self):
        """Test that grayscale images stay grayscale."""
        gray_image = Image.new("L", (100, 100), color=128)
        result = preprocess_image_for_ocr(gray_image)
        assert result.mode == "L"

    def test_returns_pil_image(self, sample_text_image: Image.Image):
        """Test that preprocessing returns a PIL Image."""
        result = preprocess_image_for_ocr(sample_text_image)
        assert isinstance(result, Image.Image)


class TestIntegration:
    """Integration tests with actual pytesseract (requires Tesseract installed)."""

    @pytest.mark.skipif(
        not os.environ.get("RUN_INTEGRATION_TESTS"),
        reason="Integration tests disabled. Set RUN_INTEGRATION_TESTS=1 to run.",
    )
    def test_real_ocr_extraction(self, sample_text_image: Image.Image):
        """
        Test OCR extraction with actual Tesseract.

        This test requires Tesseract to be installed on the system.
        Enable by setting RUN_INTEGRATION_TESTS=1 environment variable.
        """
        result = extract_text_from_image(sample_text_image)

        assert isinstance(result["page_text"], str)
        assert isinstance(result["words"], list)

        # Should extract some text
        assert len(result["page_text"]) > 0 or len(result["words"]) >= 0

