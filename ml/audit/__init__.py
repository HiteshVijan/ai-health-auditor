"""
Audit module for medical bill analysis.

Provides engines for detecting billing issues and anomalies.
Supports both US and Indian healthcare markets:
- US: CPT/HCPCS codes with CMS Medicare pricing
- India: CGHS/PMJAY rates with fuzzy procedure matching
"""

from ml.audit.audit_engine import audit_bill, get_issue_summary, AuditResult
from ml.audit.medical_codes import (
    validate_code,
    get_fair_price,
    is_overpriced,
    get_statistics as get_code_db_statistics,
)
from ml.audit.indian_pricing import (
    find_procedure as find_indian_procedure,
    is_overpriced_india,
    get_procedure_comparison,
    search_procedures as search_indian_procedures,
    get_indian_stats,
    HospitalType,
    CityTier,
)

__all__ = [
    # Core audit functions
    "audit_bill",
    "get_issue_summary",
    "AuditResult",
    # US/CPT code functions
    "validate_code",
    "get_fair_price",
    "is_overpriced",
    "get_code_db_statistics",
    # Indian pricing functions
    "find_indian_procedure",
    "is_overpriced_india",
    "get_procedure_comparison",
    "search_indian_procedures",
    "get_indian_stats",
    "HospitalType",
    "CityTier",
]
