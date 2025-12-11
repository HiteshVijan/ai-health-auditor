"""
📷 OCR Service for Medical Bill Text Extraction

Uses Tesseract (FREE, local) + AI enhancement for accurate bill reading.

Flow:
1. Tesseract extracts raw text from image
2. Groq AI cleans and structures the text
3. Returns structured bill data for analysis
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import io

logger = logging.getLogger(__name__)

# Check if pytesseract is available
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
    logger.info("✅ OCR (Tesseract) is available")
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("⚠️ OCR not available - install pytesseract and Pillow")


class OCRService:
    """
    Simple OCR service for extracting text from medical bill images.
    
    Uses Tesseract for text extraction and optionally enhances with AI.
    """
    
    def __init__(self):
        self.available = OCR_AVAILABLE
        if self.available:
            # Configure Tesseract
            # On macOS with Homebrew, it's usually auto-detected
            # On Linux: pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
            pass
    
    def extract_text(self, image_path: str) -> Optional[str]:
        """
        Extract text from an image file.
        
        Args:
            image_path: Path to the image file (JPEG, PNG, TIFF)
            
        Returns:
            Extracted text or None if failed
        """
        if not self.available:
            logger.error("OCR not available")
            return None
        
        try:
            # Open image
            image = Image.open(image_path)
            
            # Extract text using Tesseract
            # Use --psm 6 for uniform block of text (good for bills)
            text = pytesseract.image_to_string(
                image,
                config='--psm 6'  # Assume uniform block of text
            )
            
            logger.info(f"✅ Extracted {len(text)} characters from image")
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return None
    
    def extract_text_from_bytes(self, image_bytes: bytes) -> Optional[str]:
        """
        Extract text from image bytes.
        
        Args:
            image_bytes: Raw image data
            
        Returns:
            Extracted text or None if failed
        """
        if not self.available:
            return None
        
        try:
            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image, config='--psm 6')
            return text.strip()
        except Exception as e:
            logger.error(f"OCR from bytes failed: {e}")
            return None
    
    def extract_bill_data(self, image_path: str) -> Dict[str, Any]:
        """
        Extract structured bill data from an image.
        
        Uses OCR + pattern matching for common bill fields.
        
        Args:
            image_path: Path to bill image
            
        Returns:
            Dictionary with extracted bill data
        """
        text = self.extract_text(image_path)
        if not text:
            return {"error": "OCR failed", "raw_text": ""}
        
        # Parse the raw text to extract structured data
        return self._parse_bill_text(text)
    
    def _parse_bill_text(self, text: str) -> Dict[str, Any]:
        """
        Parse raw OCR text to extract bill fields.
        
        Uses simple pattern matching for common Indian bill formats.
        """
        import re
        
        result = {
            "raw_text": text,
            "provider": {},
            "patient": {},
            "line_items": [],
            "totals": {},
            "region": "IN",  # Default to India
            "confidence": "medium"
        }
        
        lines = text.split('\n')
        
        # Detect hospital name (usually in first few lines)
        hospital_keywords = [
            "hospital", "clinic", "medical", "healthcare", "health",
            "medanta", "apollo", "fortis", "max", "manipal", "aiims"
        ]
        for line in lines[:10]:
            line_lower = line.lower()
            if any(kw in line_lower for kw in hospital_keywords):
                result["provider"]["name"] = line.strip()
                break
        
        # Detect patient name
        patient_patterns = [
            r"patient\s*name\s*[:\-]?\s*(.+)",
            r"name\s*[:\-]?\s*(.+)",
            r"mr\.\s+(.+)",
            r"mrs\.\s+(.+)",
        ]
        for pattern in patient_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["patient"]["name"] = match.group(1).strip()[:50]
                break
        
        # Detect amounts (₹ or Rs patterns)
        amount_pattern = r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{2})?)"
        amounts = re.findall(amount_pattern, text)
        if amounts:
            # Convert to numbers
            amounts = [float(a.replace(',', '')) for a in amounts]
            result["totals"]["amounts_found"] = amounts
            if amounts:
                result["totals"]["likely_total"] = max(amounts)
        
        # Detect total specifically
        total_patterns = [
            r"total\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*([\d,]+(?:\.\d{2})?)",
            r"net\s*payable\s*[:\-]?\s*(?:₹|Rs\.?)?\s*([\d,]+(?:\.\d{2})?)",
            r"amount\s*due\s*[:\-]?\s*(?:₹|Rs\.?)?\s*([\d,]+(?:\.\d{2})?)",
        ]
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["totals"]["total"] = float(match.group(1).replace(',', ''))
                break
        
        # Detect line items (look for amounts at end of lines)
        line_item_pattern = r"(.{10,50}?)\s+([\d,]+(?:\.\d{2})?)\s*$"
        for line in lines:
            match = re.search(line_item_pattern, line)
            if match:
                desc = match.group(1).strip()
                amount = float(match.group(2).replace(',', ''))
                if amount > 0 and len(desc) > 5:
                    result["line_items"].append({
                        "description": desc,
                        "amount": amount
                    })
        
        # Detect GST
        gst_pattern = r"gst[in]?\s*[:\-]?\s*(\d{15})"
        gst_match = re.search(gst_pattern, text, re.IGNORECASE)
        if gst_match:
            result["provider"]["gstin"] = gst_match.group(1)
            result["region"] = "IN"
        
        # Confidence based on what we found
        found_count = sum([
            bool(result["provider"].get("name")),
            bool(result["patient"].get("name")),
            len(result["line_items"]) > 0,
            bool(result["totals"].get("total")),
        ])
        result["confidence"] = ["low", "low", "medium", "medium", "high"][found_count]
        
        return result


# Singleton instance
ocr_service = OCRService()


def test_ocr(image_path: str):
    """Quick test function."""
    print(f"Testing OCR on: {image_path}")
    print(f"OCR Available: {ocr_service.available}")
    
    if ocr_service.available:
        text = ocr_service.extract_text(image_path)
        if text:
            print(f"\n--- Extracted Text ({len(text)} chars) ---")
            print(text[:500])
            print("...")
        else:
            print("Failed to extract text")

