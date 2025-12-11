"""
Document Analysis Module

Provides complete transparency on what was scanned and extracted.
Shows raw data, structured breakdown, and analysis metrics.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re


@dataclass
class LineItem:
    """Extracted line item from bill."""
    description: str
    quantity: float
    amount: float
    code: Optional[str] = None
    category: Optional[str] = None
    cghs_rate: Optional[float] = None
    market_rate: Optional[float] = None
    overcharge_percent: Optional[float] = None


@dataclass
class DocumentScan:
    """Complete document scan results."""
    raw_text: str
    text_length: int
    ocr_confidence: str
    
    # Extracted entities
    hospital_name: Optional[str] = None
    hospital_type: Optional[str] = None
    bill_number: Optional[str] = None
    bill_date: Optional[str] = None
    patient_name: Optional[str] = None
    patient_id: Optional[str] = None
    
    # Financial summary
    subtotal: float = 0
    taxes: float = 0
    total: float = 0
    paid: float = 0
    outstanding: float = 0
    
    # Line items
    line_items: List[LineItem] = None
    
    # Categories breakdown
    categories: Dict[str, float] = None


def parse_indian_bill(ocr_text: str) -> Dict[str, Any]:
    """
    Parse Indian hospital bill from OCR text.
    Extracts all structured information.
    
    Returns complete breakdown for transparency.
    """
    result = {
        "scan_summary": {
            "text_length": len(ocr_text),
            "lines_detected": len(ocr_text.split('\n')),
            "ocr_confidence": "high" if len(ocr_text) > 500 else "medium",
        },
        "hospital": {},
        "patient": {},
        "billing": {},
        "line_items": [],
        "categories": {},
        "taxes": {},
        "payments": [],
    }
    
    lines = ocr_text.split('\n')
    text_lower = ocr_text.lower()
    
    # Hospital detection
    hospital_patterns = {
        "medanta": ("Medanta", "Super Specialty Corporate"),
        "apollo": ("Apollo Hospitals", "Corporate Chain"),
        "fortis": ("Fortis Healthcare", "Corporate Chain"),
        "max": ("Max Healthcare", "Corporate Chain"),
        "aiims": ("AIIMS", "Government"),
    }
    
    for key, (name, htype) in hospital_patterns.items():
        if key in text_lower:
            result["hospital"]["name"] = name
            result["hospital"]["type"] = htype
            break
    
    # Extract GSTIN
    gstin_match = re.search(r'GSTIN\s*[:\-]?\s*(\w{15})', ocr_text, re.IGNORECASE)
    if gstin_match:
        result["hospital"]["gstin"] = gstin_match.group(1)
    
    # Patient info
    patient_match = re.search(r'Patient\s*Name\s*[:\-]?\s*(.+?)(?:\n|$)', ocr_text, re.IGNORECASE)
    if patient_match:
        result["patient"]["name"] = patient_match.group(1).strip()[:50]
    
    patient_id_match = re.search(r'Patient\s*I[Dd]\s*[:\-]?\s*(\w+)', ocr_text, re.IGNORECASE)
    if patient_id_match:
        result["patient"]["id"] = patient_id_match.group(1)
    
    # Bill info
    bill_match = re.search(r'Bill\s*No\.?\s*[:\-]?\s*(\S+)', ocr_text, re.IGNORECASE)
    if bill_match:
        result["billing"]["bill_number"] = bill_match.group(1)
    
    bill_date_match = re.search(r'Bill\s*Date\s*[:\-]?\s*([\d/\-]+)', ocr_text, re.IGNORECASE)
    if bill_date_match:
        result["billing"]["bill_date"] = bill_date_match.group(1)
    
    # Extract amounts - look for number patterns with quantities
    amount_pattern = r'(\d+(?:\.\d{2})?)\s+(\d{1,}(?:,\d{3})*(?:\.\d{2})?)\s*$'
    
    # Common categories
    categories = {
        "kidney transplant": "Surgery",
        "transplant": "Surgery",
        "admin charges": "Administrative",
        "blood bank": "Blood Services",
        "lab charges": "Laboratory",
        "medical consumable": "Consumables",
        "medical procedures": "Procedures",
        "miscellaneous": "Miscellaneous",
        "other charges": "Other",
        "pharmacy": "Pharmacy",
        "physiotherapy": "Physiotherapy",
        "radiology": "Radiology",
        "room charges": "Room",
        "specialized medical": "Specialized",
        "visiting consultant": "Consultation",
        "icu": "ICU",
        "ot charges": "Operation Theatre",
    }
    
    for line in lines:
        line_lower = line.lower()
        
        # Try to extract line items
        for category_key, category_name in categories.items():
            if category_key in line_lower:
                # Find amounts in this line
                amounts = re.findall(r'(\d{1,}(?:,\d{3})*(?:\.\d{2})?)', line)
                if amounts:
                    # Last amount is usually the total
                    amount_str = amounts[-1].replace(',', '')
                    try:
                        amount = float(amount_str)
                        if amount > 0:
                            qty = 1.0
                            if len(amounts) >= 2:
                                try:
                                    qty = float(amounts[-2].replace(',', ''))
                                except:
                                    pass
                            
                            result["line_items"].append({
                                "description": line.strip()[:100],
                                "category": category_name,
                                "quantity": qty,
                                "amount": amount,
                            })
                            
                            if category_name not in result["categories"]:
                                result["categories"][category_name] = 0
                            result["categories"][category_name] += amount
                    except:
                        pass
    
    # Extract totals
    total_patterns = [
        (r'Total\s*Bill\s*Amount\s*[:\-]?\s*([\d,]+(?:\.\d{2})?)', "total_bill"),
        (r'Total\s*[:\-]?\s*([\d,]+(?:\.\d{2})?)', "subtotal"),
        (r'Net\s*Payable\s*[:\-]?\s*([\d,]+(?:\.\d{2})?)', "net_payable"),
        (r'CGST[^:]*[:\-]?\s*([\d,]+(?:\.\d{2})?)', "cgst"),
        (r'SGST[^:]*[:\-]?\s*([\d,]+(?:\.\d{2})?)', "sgst"),
    ]
    
    for pattern, key in total_patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            try:
                result["billing"][key] = float(match.group(1).replace(',', ''))
            except:
                pass
    
    # Extract payments - look for payment amounts at end of lines
    payment_lines = [line for line in lines if any(kw in line.lower() for kw in ['cheque', 'neft', 'rtgs', 'cash', 'payment'])]
    for line in payment_lines:
        # Find reasonable payment amounts (less than total bill)
        amounts = re.findall(r'(\d{1,6}(?:\.\d{2})?)\s*$', line)
        if amounts:
            try:
                amount = float(amounts[-1])
                if 1000 < amount < 10000000:  # Reasonable payment range
                    result["payments"].append({
                        "method": "Payment",
                        "amount": amount,
                    })
            except:
                pass
    
    return result


def get_key_metrics(bill_data: Dict, cghs_comparison: Dict) -> Dict[str, Any]:
    """
    Calculate key metrics for the bill.
    
    Returns dashboard-ready metrics.
    """
    total = bill_data.get("billing", {}).get("total_bill", 0) or \
            bill_data.get("billing", {}).get("subtotal", 0)
    
    categories = bill_data.get("categories", {})
    
    # Find largest category
    largest_category = max(categories.items(), key=lambda x: x[1]) if categories else ("N/A", 0)
    
    # Calculate potential overcharges
    total_overcharge = sum(
        item.get("amount", 0) - item.get("cghs_rate", item.get("amount", 0))
        for item in bill_data.get("line_items", [])
        if item.get("cghs_rate")
    )
    
    return {
        "total_bill": total,
        "categories_count": len(categories),
        "line_items_count": len(bill_data.get("line_items", [])),
        "largest_category": {
            "name": largest_category[0],
            "amount": largest_category[1],
            "percent_of_total": (largest_category[1] / total * 100) if total > 0 else 0,
        },
        "taxes": {
            "cgst": bill_data.get("billing", {}).get("cgst", 0),
            "sgst": bill_data.get("billing", {}).get("sgst", 0),
            "total": bill_data.get("billing", {}).get("cgst", 0) + 
                     bill_data.get("billing", {}).get("sgst", 0),
        },
        "estimated_overcharge": total_overcharge,
        "payments_made": sum(p.get("amount", 0) for p in bill_data.get("payments", [])),
    }


# CGHS Rates for major procedures (2024)
CGHS_PROCEDURE_RATES = {
    "kidney_transplant": {
        "package_rate": 250000,  # CGHS package rate
        "description": "Kidney Transplant (Living Related Donor)",
        "includes": ["Surgery", "ICU (5 days)", "Room (10 days)", "Basic medicines"],
    },
    "liver_transplant": {
        "package_rate": 1500000,
        "description": "Liver Transplant",
    },
    "cardiac_bypass": {
        "package_rate": 150000,
        "description": "CABG Surgery",
    },
    "angioplasty": {
        "package_rate": 80000,
        "description": "PTCA with Stent",
    },
    "knee_replacement": {
        "package_rate": 75000,
        "description": "Total Knee Replacement (Unilateral)",
    },
    "hip_replacement": {
        "package_rate": 80000,
        "description": "Total Hip Replacement",
    },
    "cataract": {
        "package_rate": 15000,
        "description": "Cataract Surgery with IOL",
    },
    "appendectomy": {
        "package_rate": 20000,
        "description": "Appendectomy (Laparoscopic)",
    },
    "cholecystectomy": {
        "package_rate": 25000,
        "description": "Cholecystectomy (Laparoscopic)",
    },
}


def get_cghs_comparison(procedure: str) -> Dict[str, Any]:
    """
    Get CGHS rate comparison for a procedure.
    """
    procedure_lower = procedure.lower()
    
    for key, data in CGHS_PROCEDURE_RATES.items():
        if key.replace("_", " ") in procedure_lower or \
           key.replace("_", "") in procedure_lower:
            return {
                "procedure": data["description"],
                "cghs_rate": data["package_rate"],
                "includes": data.get("includes", []),
                "source": "CGHS Rate List 2024",
            }
    
    return None

