"""
OCR utilities for extracting text from images.

Provides functions for word-level text extraction with bounding boxes
using Tesseract OCR via pytesseract.
"""

from typing import TypedDict
from PIL import Image
import pytesseract


class WordInfo(TypedDict):
    """Type definition for word extraction result."""

    text: str
    bbox: list[int]  # [x1, y1, x2, y2]
    conf: float


class OCRResult(TypedDict):
    """Type definition for OCR extraction result."""

    page_text: str
    words: list[WordInfo]


def extract_text_from_image(image: Image.Image) -> OCRResult:
    """
    Extract text from an image with word-level bounding boxes.

    Uses Tesseract OCR to perform word-level text extraction,
    returning both the full page text and individual word data
    including positions and confidence scores.

    Args:
        image: PIL Image object to extract text from.
            Supports RGB, RGBA, L (grayscale) modes.

    Returns:
        OCRResult: Dictionary containing:
            - page_text: Full extracted text as a single string.
            - words: List of word dictionaries with:
                - text: The recognized word.
                - bbox: Bounding box as [x1, y1, x2, y2].
                - conf: Confidence score (0.0 to 100.0).

    Raises:
        pytesseract.TesseractNotFoundError: If Tesseract is not installed.
        TypeError: If image is not a valid PIL Image.

    Example:
        >>> from PIL import Image
        >>> img = Image.open("medical_bill.png")
        >>> result = extract_text_from_image(img)
        >>> print(result["page_text"])
        "Patient: John Doe..."
        >>> for word in result["words"]:
        ...     print(f"{word['text']} at {word['bbox']}")
    """
    if not isinstance(image, Image.Image):
        raise TypeError(f"Expected PIL.Image.Image, got {type(image).__name__}")

    # Convert to RGB if necessary (Tesseract works best with RGB)
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    # Get word-level data using pytesseract
    # Output type 'data.frame' returns detailed word information
    ocr_data = pytesseract.image_to_data(
        image,
        output_type=pytesseract.Output.DICT,
        config="--oem 3 --psm 6",  # LSTM engine, assume uniform block of text
    )

    # Extract full page text
    page_text = pytesseract.image_to_string(
        image,
        config="--oem 3 --psm 6",
    ).strip()

    # Process word-level results
    words: list[WordInfo] = []
    n_boxes = len(ocr_data["text"])

    for i in range(n_boxes):
        # Skip empty text entries
        text = ocr_data["text"][i].strip()
        if not text:
            continue

        # Get confidence (pytesseract returns -1 for non-text elements)
        conf = float(ocr_data["conf"][i])
        if conf < 0:
            continue

        # Calculate bounding box coordinates
        x = ocr_data["left"][i]
        y = ocr_data["top"][i]
        w = ocr_data["width"][i]
        h = ocr_data["height"][i]

        # Convert to [x1, y1, x2, y2] format
        bbox = [x, y, x + w, y + h]

        words.append(
            WordInfo(
                text=text,
                bbox=bbox,
                conf=conf,
            )
        )

    return OCRResult(
        page_text=page_text,
        words=words,
    )


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Preprocess an image to improve OCR accuracy.

    Applies common preprocessing techniques including:
    - Grayscale conversion
    - Contrast enhancement
    - Noise reduction

    Args:
        image: PIL Image object to preprocess.

    Returns:
        Image.Image: Preprocessed image optimized for OCR.
    """
    from PIL import ImageEnhance, ImageFilter

    # Convert to grayscale
    if image.mode != "L":
        image = image.convert("L")

    # Enhance contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)

    # Apply slight sharpening
    image = image.filter(ImageFilter.SHARPEN)

    return image

