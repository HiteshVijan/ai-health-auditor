"""
Indian healthcare pricing service.

Provides fair pricing benchmarks for Indian healthcare using:
- CGHS (Central Government Health Scheme) rates
- PMJAY (Ayushman Bharat) package rates
- NABH hospital typical rates
- Metro vs non-metro adjustments

Supports fuzzy matching for procedure names since Indian hospitals
often don't use standardized CPT codes.
"""

import json
import logging
from pathlib import Path
from typing import Optional, TypedDict
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from difflib import SequenceMatcher

# Try to import rapidfuzz, fall back to difflib if not available
try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    # Fallback using standard library
    class FuzzFallback:
        @staticmethod
        def token_sort_ratio(s1: str, s2: str) -> float:
            """Simple token sort ratio using difflib."""
            tokens1 = sorted(s1.lower().split())
            tokens2 = sorted(s2.lower().split())
            return SequenceMatcher(None, ' '.join(tokens1), ' '.join(tokens2)).ratio() * 100
    
    fuzz = FuzzFallback()

logger = logging.getLogger(__name__)

# Data directory
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "indian_rates"


class HospitalType(str, Enum):
    """Types of hospitals in India."""
    GOVERNMENT = "government"
    CGHS_EMPANELED = "cghs_empaneled"
    PRIVATE = "private"
    CORPORATE = "corporate"
    NABH_ACCREDITED = "nabh_accredited"


class CityTier(str, Enum):
    """City tiers for pricing adjustment."""
    METRO = "metro"           # Delhi, Mumbai, Bangalore, Chennai, Kolkata, Hyderabad
    TIER_1 = "tier_1"         # State capitals, major cities
    TIER_2 = "tier_2"         # Smaller cities
    TIER_3 = "tier_3"         # Towns


class IndianPriceResult(TypedDict):
    """Result of Indian price lookup."""
    procedure_name: str
    matched_procedure: str
    match_confidence: float
    cghs_rate: Optional[float]
    pmjay_rate: Optional[float]
    fair_price_low: float       # PMJAY/CGHS rate
    fair_price_median: float    # Typical private hospital
    fair_price_high: float      # Corporate hospital max
    currency: str
    source: str


# Pricing multipliers by hospital type
HOSPITAL_MULTIPLIERS = {
    HospitalType.GOVERNMENT: 1.0,
    HospitalType.CGHS_EMPANELED: 1.2,
    HospitalType.PRIVATE: 2.0,
    HospitalType.CORPORATE: 3.0,
    HospitalType.NABH_ACCREDITED: 2.5,
}

# City tier multipliers
CITY_MULTIPLIERS = {
    CityTier.METRO: 1.5,
    CityTier.TIER_1: 1.2,
    CityTier.TIER_2: 1.0,
    CityTier.TIER_3: 0.8,
}

# Metro cities in India
METRO_CITIES = {
    "delhi", "new delhi", "mumbai", "bombay", "bangalore", "bengaluru",
    "chennai", "madras", "kolkata", "calcutta", "hyderabad", "pune",
    "ahmedabad", "gurgaon", "gurugram", "noida", "ghaziabad"
}


@dataclass
class IndianPricingDatabase:
    """Database for Indian healthcare pricing."""
    cghs_rates: dict
    pmjay_packages: dict
    procedure_index: dict  # Flat index for fuzzy search
    _loaded: bool = False
    
    @classmethod
    def load(cls) -> "IndianPricingDatabase":
        """Load Indian pricing data from JSON files."""
        cghs_rates = cls._load_json("cghs_rates_2024.json")
        pmjay_packages = cls._load_json("pmjay_packages_2024.json")
        
        # Build flat procedure index for searching
        procedure_index = cls._build_procedure_index(cghs_rates, pmjay_packages)
        
        logger.info(f"Loaded Indian pricing: {len(procedure_index)} procedures indexed")
        
        return cls(
            cghs_rates=cghs_rates,
            pmjay_packages=pmjay_packages,
            procedure_index=procedure_index,
            _loaded=bool(procedure_index),
        )
    
    @staticmethod
    def _load_json(filename: str) -> dict:
        """Load a JSON file."""
        filepath = DATA_DIR / filename
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading {filename}: {e}")
        return {}
    
    @staticmethod
    def _build_procedure_index(cghs: dict, pmjay: dict) -> dict:
        """Build a flat searchable index of all procedures."""
        index = {}
        
        # Index CGHS procedures
        for category, subcategories in cghs.items():
            if category == "meta":
                continue
            if isinstance(subcategories, dict):
                for subcat, items in subcategories.items():
                    if isinstance(items, dict):
                        if "rate" in items:
                            # Direct item
                            key = f"{category}_{subcat}".lower()
                            index[key] = {
                                "name": subcat,
                                "description": items.get("description", subcat),
                                "cghs_rate": items.get("rate"),
                                "max_private": items.get("max_private"),
                                "source": "cghs",
                                "category": category,
                            }
                        else:
                            # Nested items
                            for item_key, item_data in items.items():
                                if isinstance(item_data, dict) and "rate" in item_data:
                                    key = f"{category}_{subcat}_{item_key}".lower()
                                    index[key] = {
                                        "name": item_key,
                                        "description": item_data.get("description", item_key),
                                        "cghs_rate": item_data.get("rate"),
                                        "max_private": item_data.get("max_private"),
                                        "source": "cghs",
                                        "category": f"{category}/{subcat}",
                                    }
        
        # Index PMJAY packages
        packages = pmjay.get("packages", {})
        for category, procedures in packages.items():
            if isinstance(procedures, dict):
                for proc_key, proc_data in procedures.items():
                    if isinstance(proc_data, dict) and "package_rate" in proc_data:
                        key = f"pmjay_{category}_{proc_key}".lower()
                        index[key] = {
                            "name": proc_key,
                            "description": proc_data.get("description", proc_key),
                            "pmjay_rate": proc_data.get("package_rate"),
                            "source": "pmjay",
                            "category": category,
                        }
        
        return index


# Singleton instance
_database: Optional[IndianPricingDatabase] = None


def get_indian_database() -> IndianPricingDatabase:
    """Get the Indian pricing database singleton."""
    global _database
    if _database is None:
        _database = IndianPricingDatabase.load()
    return _database


def find_procedure(
    procedure_name: str,
    threshold: int = 60,
) -> Optional[IndianPriceResult]:
    """
    Find a procedure by name using fuzzy matching.
    
    Args:
        procedure_name: Name of the procedure to find
        threshold: Minimum match score (0-100)
        
    Returns:
        IndianPriceResult if found, None otherwise
    """
    if not procedure_name:
        return None
    
    db = get_indian_database()
    if not db.procedure_index:
        return None
    
    # Build searchable list of descriptions
    search_items = [
        (key, data.get("description", data.get("name", key)))
        for key, data in db.procedure_index.items()
    ]
    
    # Find best match
    descriptions = [item[1] for item in search_items]
    
    if RAPIDFUZZ_AVAILABLE:
        result = process.extractOne(
            procedure_name.lower(),
            descriptions,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=threshold,
        )
        if result:
            matched_desc, score, index = result
        else:
            return None
    else:
        # Fallback to manual matching using difflib
        best_match = None
        best_score = 0
        best_index = 0
        proc_lower = procedure_name.lower()
        
        for idx, desc in enumerate(descriptions):
            score = fuzz.token_sort_ratio(proc_lower, desc.lower())
            if score > best_score and score >= threshold:
                best_score = score
                best_match = desc
                best_index = idx
        
        if not best_match:
            return None
        
        matched_desc = best_match
        score = best_score
        index = best_index
    
    matched_key = search_items[index][0]
    proc_data = db.procedure_index[matched_key]
    
    cghs_rate = proc_data.get("cghs_rate")
    pmjay_rate = proc_data.get("pmjay_rate")
    max_private = proc_data.get("max_private")
    
    # Calculate fair price ranges
    base_rate = pmjay_rate or cghs_rate or 0
    
    if max_private:
        fair_high = max_private
    elif cghs_rate:
        fair_high = cghs_rate * 3  # Corporate hospitals can charge 3x
    else:
        fair_high = base_rate * 3
    
    fair_median = (base_rate + fair_high) / 2 if base_rate else fair_high / 2
    
    return IndianPriceResult(
        procedure_name=procedure_name,
        matched_procedure=proc_data.get("description", proc_data.get("name", "")),
        match_confidence=score / 100.0,
        cghs_rate=cghs_rate,
        pmjay_rate=pmjay_rate,
        fair_price_low=float(base_rate) if base_rate else 0,
        fair_price_median=float(fair_median),
        fair_price_high=float(fair_high) if fair_high else 0,
        currency="INR",
        source=proc_data.get("source", "unknown"),
    )


def is_overpriced_india(
    procedure_name: str,
    charged_amount: float,
    hospital_type: HospitalType = HospitalType.PRIVATE,
    city: Optional[str] = None,
    threshold_multiplier: float = 1.5,
) -> tuple[bool, Optional[float], Optional[str]]:
    """
    Check if a procedure is overpriced for Indian healthcare.
    
    Args:
        procedure_name: Name/description of the procedure
        charged_amount: Amount charged in INR
        hospital_type: Type of hospital
        city: City name for tier adjustment
        threshold_multiplier: Multiplier above fair price to consider overpriced
        
    Returns:
        tuple: (is_overpriced, fair_price, message)
    """
    price_info = find_procedure(procedure_name)
    
    if not price_info:
        return False, None, f"No pricing data found for '{procedure_name}'"
    
    # Determine city tier
    city_tier = CityTier.TIER_2
    if city:
        city_lower = city.lower().strip()
        if city_lower in METRO_CITIES:
            city_tier = CityTier.METRO
    
    # Calculate expected price based on hospital type and city
    hospital_mult = HOSPITAL_MULTIPLIERS.get(hospital_type, 1.5)
    city_mult = CITY_MULTIPLIERS.get(city_tier, 1.0)
    
    base_rate = price_info["fair_price_low"] or price_info["fair_price_median"]
    expected_price = base_rate * hospital_mult * city_mult
    threshold = expected_price * threshold_multiplier
    
    if charged_amount > threshold:
        excess = charged_amount - expected_price
        excess_percent = (excess / expected_price) * 100 if expected_price > 0 else 0
        
        return (
            True,
            expected_price,
            f"Charged ₹{charged_amount:,.0f} is {excess_percent:.0f}% above fair price ₹{expected_price:,.0f} "
            f"(based on {hospital_type.value} hospital in {city_tier.value} city)"
        )
    
    return False, expected_price, None


def get_procedure_comparison(procedure_name: str) -> Optional[dict]:
    """
    Get a comparison of prices across different sources.
    
    Args:
        procedure_name: Name of the procedure
        
    Returns:
        dict with price comparison data
    """
    price_info = find_procedure(procedure_name)
    
    if not price_info:
        return None
    
    base_rate = price_info["fair_price_low"] or price_info["fair_price_median"]
    
    return {
        "procedure": price_info["matched_procedure"],
        "match_confidence": price_info["match_confidence"],
        "prices": {
            "cghs_rate": price_info["cghs_rate"],
            "pmjay_package": price_info["pmjay_rate"],
            "government_hospital": base_rate,
            "private_hospital": base_rate * 2,
            "corporate_hospital": base_rate * 3,
            "metro_adjustment": base_rate * 1.5,
        },
        "recommendations": {
            "budget_option": f"Government or CGHS-empaneled hospital: ₹{base_rate:,.0f}",
            "mid_range": f"Private hospital: ₹{base_rate * 2:,.0f}",
            "premium": f"Corporate hospital in metro: ₹{base_rate * 3 * 1.5:,.0f}",
        },
        "currency": "INR",
    }


def search_procedures(
    query: str,
    limit: int = 10,
) -> list[dict]:
    """
    Search for procedures matching a query.
    
    Args:
        query: Search query
        limit: Maximum results
        
    Returns:
        List of matching procedures
    """
    db = get_indian_database()
    if not db.procedure_index:
        return []
    
    results = []
    search_items = [
        (key, data.get("description", data.get("name", key)), data)
        for key, data in db.procedure_index.items()
    ]
    
    descriptions = [item[1] for item in search_items]
    
    if RAPIDFUZZ_AVAILABLE:
        matches = process.extract(
            query.lower(),
            descriptions,
            scorer=fuzz.token_sort_ratio,
            limit=limit,
        )
    else:
        # Fallback: compute all scores and sort
        query_lower = query.lower()
        scored_items = []
        for idx, desc in enumerate(descriptions):
            score = fuzz.token_sort_ratio(query_lower, desc.lower())
            scored_items.append((desc, score, idx))
        
        scored_items.sort(key=lambda x: x[1], reverse=True)
        matches = scored_items[:limit]
    
    for desc, score, idx in matches:
        key, _, data = search_items[idx]
        results.append({
            "name": data.get("description", data.get("name", "")),
            "category": data.get("category", ""),
            "cghs_rate": data.get("cghs_rate"),
            "pmjay_rate": data.get("pmjay_rate"),
            "max_private": data.get("max_private"),
            "source": data.get("source", ""),
            "match_score": score,
        })
    
    return results


def get_indian_stats() -> dict:
    """Get statistics about Indian pricing database."""
    db = get_indian_database()
    
    cghs_count = 0
    pmjay_count = 0
    
    for key, data in db.procedure_index.items():
        if data.get("source") == "cghs":
            cghs_count += 1
        elif data.get("source") == "pmjay":
            pmjay_count += 1
    
    return {
        "loaded": db._loaded,
        "total_procedures": len(db.procedure_index),
        "cghs_procedures": cghs_count,
        "pmjay_packages": pmjay_count,
        "data_directory": str(DATA_DIR),
    }

