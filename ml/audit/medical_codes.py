"""
Medical code database service for validating and looking up
ICD-10, CPT, and HCPCS codes.

Loads data from CMS (free public sources) and provides:
- Code validation
- Fair price lookups
- Description lookups
- Category classification
"""

import json
import logging
from pathlib import Path
from typing import Optional, TypedDict
from functools import lru_cache
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Path to processed data
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "processed"


class CodeType(str, Enum):
    """Types of medical codes."""
    ICD10 = "icd10"       # Diagnosis codes
    CPT = "cpt"           # Procedure codes (AMA)
    HCPCS = "hcpcs"       # Healthcare common procedure codes
    UNKNOWN = "unknown"


class CodeInfo(TypedDict):
    """Information about a medical code."""
    code: str
    code_type: str
    description: str
    category: str
    is_valid: bool


class PriceInfo(TypedDict):
    """Fair pricing information for a procedure code."""
    code: str
    fair_price_low: float      # 60th percentile
    fair_price_median: float   # Typical fair price
    fair_price_high: float     # 150th percentile
    medicare_rate: Optional[float]
    rvu: Optional[float]       # Relative Value Units
    currency: str


class IndianPriceInfo(TypedDict):
    """Indian healthcare pricing information."""
    code: str
    cghs_rate: Optional[float]
    pmjay_rate: Optional[float]
    nabh_rate: Optional[float]
    currency: str


@dataclass
class MedicalCodeDatabase:
    """
    Database for medical code lookups.
    
    Loads data from JSON files created by download_medical_codes.py
    """
    
    icd10_codes: dict
    cpt_hcpcs_codes: dict
    fee_schedule: dict
    indian_rates: dict
    _loaded: bool = False
    
    @classmethod
    def load(cls) -> "MedicalCodeDatabase":
        """
        Load the medical code database from processed files.
        
        Returns:
            MedicalCodeDatabase: Loaded database instance
        """
        combined_path = DATA_DIR / "combined_codes.json"
        
        if combined_path.exists():
            try:
                with open(combined_path, "r") as f:
                    data = json.load(f)
                
                db = cls(
                    icd10_codes=data.get("icd10", {}),
                    cpt_hcpcs_codes=data.get("cpt_hcpcs", {}),
                    fee_schedule=data.get("fee_schedule", {}),
                    indian_rates=data.get("indian_rates", {}),
                    _loaded=True,
                )
                logger.info(
                    f"Loaded medical code database: "
                    f"{len(db.icd10_codes)} ICD-10, "
                    f"{len(db.cpt_hcpcs_codes)} CPT/HCPCS codes"
                )
                return db
                
            except Exception as e:
                logger.error(f"Error loading combined database: {e}")
        
        # Try loading individual files
        return cls._load_individual_files()
    
    @classmethod
    def _load_individual_files(cls) -> "MedicalCodeDatabase":
        """Load from individual processed files."""
        icd10 = cls._load_json_file("icd10_codes.json")
        cpt_hcpcs = cls._load_json_file("hcpcs_codes.json")
        fees = cls._load_json_file("fee_schedule.json")
        indian = cls._load_json_file("indian_rates.json")
        
        return cls(
            icd10_codes=icd10,
            cpt_hcpcs_codes=cpt_hcpcs,
            fee_schedule=fees,
            indian_rates=indian,
            _loaded=bool(icd10 or cpt_hcpcs),
        )
    
    @staticmethod
    def _load_json_file(filename: str) -> dict:
        """Load a JSON file from the processed directory."""
        filepath = DATA_DIR / filename
        if filepath.exists():
            try:
                with open(filepath, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading {filename}: {e}")
        return {}


# Singleton instance
_database: Optional[MedicalCodeDatabase] = None


def get_database() -> MedicalCodeDatabase:
    """
    Get the medical code database singleton.
    
    Returns:
        MedicalCodeDatabase: The loaded database
    """
    global _database
    if _database is None:
        _database = MedicalCodeDatabase.load()
    return _database


def reload_database() -> MedicalCodeDatabase:
    """
    Force reload the database.
    
    Returns:
        MedicalCodeDatabase: Freshly loaded database
    """
    global _database
    _database = MedicalCodeDatabase.load()
    return _database


def detect_code_type(code: str) -> CodeType:
    """
    Detect the type of medical code.
    
    Args:
        code: The medical code to classify
        
    Returns:
        CodeType: The detected code type
    """
    if not code:
        return CodeType.UNKNOWN
    
    code = code.strip().upper()
    
    # ICD-10 codes: Letter followed by digits, optionally with decimal
    # Examples: A00.1, E11.9, M54.5
    if len(code) >= 3 and code[0].isalpha() and code[1].isdigit():
        # Check if it's not a HCPCS Level II code
        if code[0] not in "ABCDEGHJKLMPQRSTV":
            return CodeType.ICD10
        # ICD-10 codes typically have format X00.00
        if len(code) >= 3 and "." in code:
            return CodeType.ICD10
        # Check against known patterns
        if code[0] in "EFGHIJKLMNOPQRSTUYZ":
            return CodeType.ICD10
    
    # CPT codes: 5 digits (numeric only)
    # Examples: 99213, 70553, 85025
    if code.isdigit() and len(code) == 5:
        return CodeType.CPT
    
    # HCPCS Level II: Letter followed by 4 digits
    # Examples: A0021, J1234, G0101
    if len(code) == 5 and code[0].isalpha() and code[1:].isdigit():
        return CodeType.HCPCS
    
    return CodeType.UNKNOWN


def validate_code(code: str) -> CodeInfo:
    """
    Validate a medical code and return information about it.
    
    Args:
        code: The medical code to validate
        
    Returns:
        CodeInfo: Information about the code
    """
    if not code:
        return CodeInfo(
            code="",
            code_type=CodeType.UNKNOWN.value,
            description="Empty code",
            category="Unknown",
            is_valid=False,
        )
    
    code = code.strip().upper()
    code_type = detect_code_type(code)
    db = get_database()
    
    # Look up in appropriate database
    if code_type == CodeType.ICD10:
        # Try exact match and prefix match
        code_data = db.icd10_codes.get(code) or db.icd10_codes.get(code.replace(".", ""))
        if code_data:
            return CodeInfo(
                code=code,
                code_type=CodeType.ICD10.value,
                description=code_data.get("description", "Unknown"),
                category=code_data.get("category", "Unknown"),
                is_valid=True,
            )
    
    elif code_type in (CodeType.CPT, CodeType.HCPCS):
        code_data = db.cpt_hcpcs_codes.get(code)
        if code_data:
            return CodeInfo(
                code=code,
                code_type=code_type.value,
                description=code_data.get("description", "Unknown"),
                category=code_data.get("category", "Unknown"),
                is_valid=True,
            )
    
    # Code not found in database
    return CodeInfo(
        code=code,
        code_type=code_type.value,
        description="Code not found in database",
        category="Unknown",
        is_valid=False,
    )


def get_fair_price(code: str, region: str = "US") -> Optional[PriceInfo]:
    """
    Get fair pricing information for a procedure code.
    
    Args:
        code: CPT or HCPCS code
        region: Region for pricing (US or India)
        
    Returns:
        Optional[PriceInfo]: Pricing information if available
    """
    if not code:
        return None
    
    code = code.strip().upper()
    db = get_database()
    
    # Look up in fee schedule
    fee_data = db.fee_schedule.get(code)
    
    if fee_data:
        return PriceInfo(
            code=code,
            fair_price_low=fee_data.get("fair_price_low", 0),
            fair_price_median=fee_data.get("national_payment", fee_data.get("fair_price", 0)),
            fair_price_high=fee_data.get("fair_price_high", 0),
            medicare_rate=fee_data.get("national_payment"),
            rvu=fee_data.get("rvu"),
            currency="USD",
        )
    
    # Try to get from CPT/HCPCS database
    cpt_data = db.cpt_hcpcs_codes.get(code)
    if cpt_data and "fair_price" in cpt_data:
        fair_price = cpt_data["fair_price"]
        return PriceInfo(
            code=code,
            fair_price_low=fair_price * 0.6,
            fair_price_median=fair_price,
            fair_price_high=fair_price * 1.5,
            medicare_rate=None,
            rvu=cpt_data.get("rvu"),
            currency="USD",
        )
    
    return None


def get_indian_price(code: str, procedure_name: Optional[str] = None) -> Optional[IndianPriceInfo]:
    """
    Get Indian healthcare pricing (CGHS/PMJAY rates).
    
    Args:
        code: Procedure code (optional if procedure_name provided)
        procedure_name: Name of the procedure for fuzzy matching
        
    Returns:
        Optional[IndianPriceInfo]: Indian pricing information
    """
    db = get_database()
    indian_rates = db.indian_rates
    
    if not indian_rates:
        return None
    
    # Try to find matching rate
    cghs_rate = None
    pmjay_rate = None
    nabh_rate = None
    
    # Search in CGHS procedures
    cghs = indian_rates.get("cghs", {})
    for category, rates in cghs.items():
        if isinstance(rates, dict):
            for proc, rate in rates.items():
                if procedure_name and proc.lower() in procedure_name.lower():
                    cghs_rate = rate
                    break
    
    # Search in PMJAY packages
    pmjay = indian_rates.get("pmjay", {}).get("packages", {})
    for proc, rate in pmjay.items():
        if procedure_name and proc.lower().replace("_", " ") in procedure_name.lower():
            pmjay_rate = rate
            break
    
    # Search in NABH rates
    nabh = indian_rates.get("nabh_rates", {})
    for category, rates in nabh.items():
        if isinstance(rates, dict):
            for proc, rate in rates.items():
                if procedure_name and proc.lower() in procedure_name.lower():
                    nabh_rate = rate
                    break
    
    if cghs_rate or pmjay_rate or nabh_rate:
        return IndianPriceInfo(
            code=code,
            cghs_rate=cghs_rate,
            pmjay_rate=pmjay_rate,
            nabh_rate=nabh_rate,
            currency="INR",
        )
    
    return None


def is_overpriced(
    code: str,
    charged_amount: float,
    threshold_multiplier: float = 1.5,
) -> tuple[bool, Optional[float], Optional[str]]:
    """
    Check if a charge is overpriced compared to fair market rates.
    
    Args:
        code: Procedure code
        charged_amount: Amount charged
        threshold_multiplier: Multiplier above fair price to consider overpriced
        
    Returns:
        tuple: (is_overpriced, fair_price, message)
    """
    price_info = get_fair_price(code)
    
    if not price_info:
        return False, None, "No pricing data available for this code"
    
    fair_high = price_info["fair_price_high"]
    fair_median = price_info["fair_price_median"]
    threshold = fair_median * threshold_multiplier
    
    if charged_amount > threshold:
        excess = charged_amount - fair_median
        excess_percent = (excess / fair_median) * 100 if fair_median > 0 else 0
        
        return (
            True,
            fair_median,
            f"Charged ${charged_amount:.2f} is {excess_percent:.0f}% above fair price ${fair_median:.2f}",
        )
    
    return False, fair_median, None


def get_code_description(code: str) -> Optional[str]:
    """
    Get the description for a medical code.
    
    Args:
        code: Medical code (ICD-10, CPT, or HCPCS)
        
    Returns:
        Optional[str]: Description if found
    """
    info = validate_code(code)
    if info["is_valid"]:
        return info["description"]
    return None


def search_codes(
    query: str,
    code_type: Optional[CodeType] = None,
    limit: int = 10,
) -> list[CodeInfo]:
    """
    Search for codes by description.
    
    Args:
        query: Search query
        code_type: Optional filter by code type
        limit: Maximum number of results
        
    Returns:
        list[CodeInfo]: Matching codes
    """
    db = get_database()
    results = []
    query_lower = query.lower()
    
    # Search ICD-10 codes
    if code_type is None or code_type == CodeType.ICD10:
        for code, data in db.icd10_codes.items():
            desc = data.get("description", "").lower()
            if query_lower in desc or query_lower in code.lower():
                results.append(CodeInfo(
                    code=code,
                    code_type=CodeType.ICD10.value,
                    description=data.get("description", ""),
                    category=data.get("category", "Unknown"),
                    is_valid=True,
                ))
                if len(results) >= limit:
                    return results
    
    # Search CPT/HCPCS codes
    if code_type is None or code_type in (CodeType.CPT, CodeType.HCPCS):
        for code, data in db.cpt_hcpcs_codes.items():
            desc = data.get("description", "").lower()
            if query_lower in desc or query_lower in code.lower():
                results.append(CodeInfo(
                    code=code,
                    code_type=detect_code_type(code).value,
                    description=data.get("description", ""),
                    category=data.get("category", "Unknown"),
                    is_valid=True,
                ))
                if len(results) >= limit:
                    return results
    
    return results


def get_statistics() -> dict:
    """
    Get statistics about the loaded database.
    
    Returns:
        dict: Database statistics
    """
    db = get_database()
    
    return {
        "loaded": db._loaded,
        "icd10_count": len(db.icd10_codes),
        "cpt_hcpcs_count": len(db.cpt_hcpcs_codes),
        "fee_schedule_count": len(db.fee_schedule),
        "has_indian_rates": bool(db.indian_rates),
        "data_directory": str(DATA_DIR),
    }

