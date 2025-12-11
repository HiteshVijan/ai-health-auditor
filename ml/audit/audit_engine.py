"""
Audit engine for detecting billing issues in medical bills.

Analyzes parsed bill data to identify potential errors, overcharges,
and discrepancies that require attention.

Supports both US and Indian healthcare markets:
- US: Uses CPT/HCPCS codes with Medicare fee schedule benchmarks
- India: Uses CGHS/PMJAY rates with fuzzy procedure matching

Uses real medical coding databases (ICD-10, CPT, HCPCS) from CMS
and fair pricing benchmarks for accurate overcharge detection.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TypedDict, Literal
from collections import Counter
import re

from ml.audit.medical_codes import (
    validate_code,
    get_fair_price,
    get_indian_price,
    is_overpriced,
    get_code_description,
    CodeType,
    get_database,
)
from ml.audit.indian_pricing import (
    find_procedure as find_indian_procedure,
    is_overpriced_india,
    HospitalType,
    get_indian_stats,
)

logger = logging.getLogger(__name__)

# Supported regions
Region = Literal["US", "IN", "AUTO"]


class IssueSeverity(str, Enum):
    """Severity levels for audit issues."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(str, Enum):
    """Types of billing issues."""

    DUPLICATE_CHARGE = "duplicate_charge"
    ARITHMETIC_MISMATCH = "arithmetic_mismatch"
    TAX_MISMATCH = "tax_mismatch"
    OVERCHARGE = "overcharge"
    MISSING_FIELD = "missing_field"
    INVALID_CODE = "invalid_code"
    UNKNOWN_CODE = "unknown_code"
    QUANTITY_ERROR = "quantity_error"
    UPCODING = "upcoding"  # Billing for more expensive service than provided


class AuditIssue(TypedDict):
    """Type definition for an audit issue."""

    id: int
    type: str
    severity: str
    description: str
    field: Optional[str]
    expected: Optional[str]
    actual: Optional[str]
    amount_impact: Optional[float]


class AuditResult(TypedDict):
    """Type definition for audit result."""

    issues: list[AuditIssue]
    score: int
    total_issues: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    potential_savings: float


class LineItem(TypedDict):
    """Type definition for a bill line item."""

    code: Optional[str]
    description: str
    quantity: int
    unit_price: float
    total: float


class ParsedBill(TypedDict):
    """Type definition for parsed bill data."""

    document_id: int
    total_amount: Optional[float]
    subtotal: Optional[float]
    tax_amount: Optional[float]
    tax_rate: Optional[float]
    discount: Optional[float]
    insurance_paid: Optional[float]
    patient_responsibility: Optional[float]
    line_items: list[LineItem]
    invoice_number: Optional[str]
    patient_name: Optional[str]
    bill_date: Optional[str]
    # Region-specific fields
    region: Optional[str]           # "US", "IN", or auto-detect
    currency: Optional[str]         # "USD", "INR"
    # India-specific fields
    hospital_name: Optional[str]
    hospital_type: Optional[str]    # "government", "private", "corporate"
    city: Optional[str]             # For city-tier pricing adjustment


# Legacy overcharge thresholds (fallback if database not loaded)
# These are used only when the medical code database is unavailable
LEGACY_OVERCHARGE_THRESHOLDS = {
    # Office visits
    "99211": 50.0,
    "99212": 100.0,
    "99213": 175.0,
    "99214": 250.0,
    "99215": 350.0,
    # Lab tests
    "85025": 75.0,   # CBC
    "80053": 150.0,  # Comprehensive metabolic panel
    "80061": 100.0,  # Lipid panel
    "81001": 50.0,   # Urinalysis
    # Imaging
    "71046": 300.0,  # Chest X-ray
    "70553": 2500.0, # Brain MRI
    "72148": 2000.0, # Lumbar MRI
    # Default threshold for unknown codes
    "default": 500.0,
}

# Overcharge threshold multiplier (charges above this multiple of fair price are flagged)
OVERCHARGE_MULTIPLIER = 1.5  # 150% of fair price

# Indian currency indicators
INDIAN_CURRENCY_SYMBOLS = {"₹", "Rs", "Rs.", "INR", "Rupees"}
INDIAN_GST_RATES = {0.05, 0.12, 0.18, 0.28}  # Common GST rates


def _detect_region(parsed_bill: ParsedBill, region_hint: Region) -> str:
    """
    Detect the market region for a bill.
    
    Args:
        parsed_bill: The parsed bill data
        region_hint: User-provided hint ("US", "IN", or "AUTO")
        
    Returns:
        str: Detected region ("US" or "IN")
    """
    # If explicitly specified, use that
    if region_hint in ("US", "IN"):
        return region_hint
    
    # Check explicit region field in bill
    bill_region = parsed_bill.get("region", "").upper()
    if bill_region in ("US", "IN", "INDIA", "USA"):
        return "IN" if bill_region in ("IN", "INDIA") else "US"
    
    # Check currency
    currency = parsed_bill.get("currency", "").upper()
    if currency == "INR":
        return "IN"
    if currency == "USD":
        return "US"
    
    # Check for Indian city names
    city = parsed_bill.get("city", "").lower()
    indian_cities = {
        "delhi", "mumbai", "bangalore", "bengaluru", "chennai", "kolkata",
        "hyderabad", "pune", "ahmedabad", "jaipur", "lucknow", "surat",
        "kanpur", "nagpur", "indore", "thane", "bhopal", "patna",
        "gurgaon", "gurugram", "noida", "ghaziabad", "chandigarh"
    }
    if city in indian_cities:
        return "IN"
    
    # Check for Indian hospital types
    hospital_type = parsed_bill.get("hospital_type", "").lower()
    if hospital_type in ("cghs", "government", "ayushman", "pmjay"):
        return "IN"
    
    # Check tax rate (GST vs US sales tax patterns)
    tax_rate = parsed_bill.get("tax_rate")
    if tax_rate is not None:
        if tax_rate in INDIAN_GST_RATES or tax_rate == 0.18:  # 18% is common GST
            return "IN"
    
    # Check if line items have CPT codes (US pattern)
    line_items = parsed_bill.get("line_items", [])
    for item in line_items:
        code = item.get("code", "")
        if code and code.isdigit() and len(code) == 5:
            return "US"  # Likely CPT code
    
    # Check amount ranges (heuristic: Indian bills often have larger numbers due to INR)
    total = parsed_bill.get("total_amount", 0)
    if total and total > 10000:  # Likely INR if over 10,000
        # Check if it's a reasonable US bill (under $50,000 typically)
        if total > 50000:
            return "IN"  # More likely to be INR
    
    # Default to US if unclear
    return "US"

# Tax rate bounds (reasonable range)
MIN_TAX_RATE = 0.0
MAX_TAX_RATE = 0.15  # 15%

# Tolerance for arithmetic comparisons
ARITHMETIC_TOLERANCE = 0.01


def audit_bill(
    parsed_bill: ParsedBill,
    region: Region = "AUTO",
) -> AuditResult:
    """
    Audit a parsed medical bill for issues.

    Performs comprehensive checks including duplicate detection,
    arithmetic validation, tax verification, and overcharge detection.
    
    Supports both US and Indian healthcare markets with appropriate
    pricing benchmarks for each region.

    Args:
        parsed_bill: Parsed bill data from docai_pipeline.
        region: Market region ("US", "IN", or "AUTO" for auto-detection).

    Returns:
        AuditResult: Dictionary containing:
            - issues: List of detected issues with details.
            - score: Overall bill health score (0-100).
            - total_issues: Count of all issues.
            - *_count: Counts by severity level.
            - potential_savings: Estimated savings if issues resolved.

    Example:
        >>> bill = {"total_amount": 500.0, "line_items": [...], "region": "IN"}
        >>> result = audit_bill(bill)
        >>> print(f"Score: {result['score']}, Issues: {result['total_issues']}")
    """
    # Detect region if AUTO
    detected_region = _detect_region(parsed_bill, region)
    currency = "INR" if detected_region == "IN" else "USD"
    
    logger.info(
        f"Starting audit for document_id={parsed_bill.get('document_id')}, "
        f"region={detected_region}, currency={currency}"
    )

    issues: list[AuditIssue] = []
    issue_id = 0

    # Run all checks
    def add_issue(
        issue_type: IssueType,
        severity: IssueSeverity,
        description: str,
        field: Optional[str] = None,
        expected: Optional[str] = None,
        actual: Optional[str] = None,
        amount_impact: Optional[float] = None,
    ) -> None:
        nonlocal issue_id
        issue_id += 1
        issues.append(
            AuditIssue(
                id=issue_id,
                type=issue_type.value,
                severity=severity.value,
                description=description,
                field=field,
                expected=expected,
                actual=actual,
                amount_impact=amount_impact,
            )
        )

    # Check for missing required fields
    _check_missing_fields(parsed_bill, add_issue)

    # Check for duplicate charges
    _check_duplicate_charges(parsed_bill.get("line_items", []), add_issue)

    # Validate medical codes (skip for India if using procedure names)
    if detected_region == "US":
        _check_medical_codes(parsed_bill.get("line_items", []), add_issue)

    # Check arithmetic (line items sum vs subtotal/total)
    _check_arithmetic(parsed_bill, add_issue)

    # Check tax calculations
    _check_tax(parsed_bill, add_issue)

    # Check for overcharges using real pricing data (region-aware)
    _check_overcharges(
        line_items=parsed_bill.get("line_items", []),
        add_issue=add_issue,
        region=detected_region,
        hospital_type=parsed_bill.get("hospital_type"),
        city=parsed_bill.get("city"),
    )

    # Check quantity errors
    _check_quantities(parsed_bill.get("line_items", []), add_issue)

    # Calculate score and summary
    score = _calculate_score(issues)
    potential_savings = _calculate_potential_savings(issues)

    # Count by severity
    severity_counts = Counter(issue["severity"] for issue in issues)

    result = AuditResult(
        issues=issues,
        score=score,
        total_issues=len(issues),
        critical_count=severity_counts.get("critical", 0),
        high_count=severity_counts.get("high", 0),
        medium_count=severity_counts.get("medium", 0),
        low_count=severity_counts.get("low", 0),
        potential_savings=round(potential_savings, 2),
    )

    logger.info(
        f"Audit complete: score={score}, issues={len(issues)}, "
        f"potential_savings=${potential_savings:.2f}"
    )

    return result


def _check_missing_fields(parsed_bill: ParsedBill, add_issue) -> None:
    """
    Check for missing required fields.

    Args:
        parsed_bill: Parsed bill data.
        add_issue: Function to add issues.
    """
    required_fields = ["total_amount", "invoice_number", "patient_name", "bill_date"]

    for field_name in required_fields:
        value = parsed_bill.get(field_name)
        if value is None or (isinstance(value, str) and not value.strip()):
            add_issue(
                issue_type=IssueType.MISSING_FIELD,
                severity=IssueSeverity.MEDIUM,
                description=f"Required field '{field_name}' is missing or empty",
                field=field_name,
            )


def _check_medical_codes(line_items: list[LineItem], add_issue) -> None:
    """
    Validate medical codes (ICD-10, CPT, HCPCS) against the database.

    Args:
        line_items: List of bill line items.
        add_issue: Function to add issues.
    """
    for i, item in enumerate(line_items):
        code = item.get("code", "")
        description = item.get("description", "")

        if not code:
            # No code provided - might be a problem
            if description:
                add_issue(
                    issue_type=IssueType.MISSING_FIELD,
                    severity=IssueSeverity.LOW,
                    description=f"No procedure code for line item: '{description}'",
                    field=f"line_items[{i}].code",
                )
            continue

        # Validate the code against our database
        code_info = validate_code(code)

        if not code_info["is_valid"]:
            # Code not found in database
            add_issue(
                issue_type=IssueType.UNKNOWN_CODE,
                severity=IssueSeverity.LOW,
                description=(
                    f"Code '{code}' not found in medical code database. "
                    f"This may be a custom/facility code or data entry error."
                ),
                field=f"line_items[{i}].code",
                actual=code,
            )
        else:
            # Code is valid - check if description matches
            db_description = code_info["description"].lower()
            item_description = description.lower()

            # Simple check for major mismatches
            if db_description and item_description:
                # If descriptions are very different, might be wrong code
                key_words = set(db_description.split()[:3])
                item_words = set(item_description.split()[:5])

                if len(key_words & item_words) == 0 and len(key_words) >= 2:
                    add_issue(
                        issue_type=IssueType.INVALID_CODE,
                        severity=IssueSeverity.MEDIUM,
                        description=(
                            f"Code '{code}' ({code_info['description']}) may not match "
                            f"the described service: '{description}'"
                        ),
                        field=f"line_items[{i}]",
                        expected=code_info["description"],
                        actual=description,
                    )


def _check_duplicate_charges(line_items: list[LineItem], add_issue) -> None:
    """
    Check for duplicate charges in line items.

    Args:
        line_items: List of bill line items.
        add_issue: Function to add issues.
    """
    if not line_items:
        return

    # Group by code + description
    item_keys = []
    for item in line_items:
        code = item.get("code", "")
        desc = item.get("description", "").lower().strip()
        key = f"{code}|{desc}"
        item_keys.append((key, item))

    # Count occurrences
    key_counts = Counter(key for key, _ in item_keys)

    # Find duplicates
    seen_duplicates = set()
    for key, item in item_keys:
        if key_counts[key] > 1 and key not in seen_duplicates:
            seen_duplicates.add(key)
            amount = item.get("total", 0) * (key_counts[key] - 1)

            add_issue(
                issue_type=IssueType.DUPLICATE_CHARGE,
                severity=IssueSeverity.HIGH,
                description=(
                    f"Duplicate charge detected: '{item.get('description')}' "
                    f"appears {key_counts[key]} times"
                ),
                field="line_items",
                expected="1",
                actual=str(key_counts[key]),
                amount_impact=amount,
            )


def _check_arithmetic(parsed_bill: ParsedBill, add_issue) -> None:
    """
    Check arithmetic consistency of bill totals.

    Args:
        parsed_bill: Parsed bill data.
        add_issue: Function to add issues.
    """
    line_items = parsed_bill.get("line_items", [])

    # Calculate sum of line items
    line_item_sum = sum(
        item.get("total", 0) for item in line_items
    )

    # Check subtotal matches line items
    subtotal = parsed_bill.get("subtotal")
    if subtotal is not None and line_items:
        diff = abs(line_item_sum - subtotal)
        if diff > ARITHMETIC_TOLERANCE:
            add_issue(
                issue_type=IssueType.ARITHMETIC_MISMATCH,
                severity=IssueSeverity.HIGH,
                description=(
                    f"Line items sum (${line_item_sum:.2f}) does not match "
                    f"subtotal (${subtotal:.2f})"
                ),
                field="subtotal",
                expected=f"${line_item_sum:.2f}",
                actual=f"${subtotal:.2f}",
                amount_impact=diff,
            )

    # Check total calculation
    total = parsed_bill.get("total_amount")
    if total is not None:
        # Calculate expected total
        expected_total = subtotal if subtotal else line_item_sum
        tax = parsed_bill.get("tax_amount", 0) or 0
        discount = parsed_bill.get("discount", 0) or 0
        insurance = parsed_bill.get("insurance_paid", 0) or 0

        calculated_total = expected_total + tax - discount - insurance

        if calculated_total > 0:
            diff = abs(calculated_total - total)
            if diff > ARITHMETIC_TOLERANCE:
                add_issue(
                    issue_type=IssueType.ARITHMETIC_MISMATCH,
                    severity=IssueSeverity.CRITICAL,
                    description=(
                        f"Calculated total (${calculated_total:.2f}) does not match "
                        f"stated total (${total:.2f})"
                    ),
                    field="total_amount",
                    expected=f"${calculated_total:.2f}",
                    actual=f"${total:.2f}",
                    amount_impact=diff,
                )

    # Check individual line item arithmetic (quantity * unit_price = total)
    for i, item in enumerate(line_items):
        quantity = item.get("quantity", 1)
        unit_price = item.get("unit_price", 0)
        item_total = item.get("total", 0)

        if quantity and unit_price:
            expected_item_total = quantity * unit_price
            diff = abs(expected_item_total - item_total)

            if diff > ARITHMETIC_TOLERANCE:
                add_issue(
                    issue_type=IssueType.ARITHMETIC_MISMATCH,
                    severity=IssueSeverity.MEDIUM,
                    description=(
                        f"Line item '{item.get('description')}': "
                        f"{quantity} × ${unit_price:.2f} ≠ ${item_total:.2f}"
                    ),
                    field=f"line_items[{i}]",
                    expected=f"${expected_item_total:.2f}",
                    actual=f"${item_total:.2f}",
                    amount_impact=diff,
                )


def _check_tax(parsed_bill: ParsedBill, add_issue) -> None:
    """
    Check tax calculations and reasonableness.

    Args:
        parsed_bill: Parsed bill data.
        add_issue: Function to add issues.
    """
    tax_amount = parsed_bill.get("tax_amount")
    tax_rate = parsed_bill.get("tax_rate")
    subtotal = parsed_bill.get("subtotal")

    # If we have both tax amount and rate, verify calculation
    if tax_amount is not None and tax_rate is not None and subtotal:
        expected_tax = subtotal * tax_rate
        diff = abs(expected_tax - tax_amount)

        if diff > ARITHMETIC_TOLERANCE:
            add_issue(
                issue_type=IssueType.TAX_MISMATCH,
                severity=IssueSeverity.HIGH,
                description=(
                    f"Tax calculation mismatch: ${subtotal:.2f} × {tax_rate*100:.1f}% "
                    f"= ${expected_tax:.2f}, but stated tax is ${tax_amount:.2f}"
                ),
                field="tax_amount",
                expected=f"${expected_tax:.2f}",
                actual=f"${tax_amount:.2f}",
                amount_impact=diff,
            )

    # Check if tax rate is reasonable
    if tax_rate is not None:
        if tax_rate < MIN_TAX_RATE or tax_rate > MAX_TAX_RATE:
            add_issue(
                issue_type=IssueType.TAX_MISMATCH,
                severity=IssueSeverity.MEDIUM,
                description=(
                    f"Tax rate {tax_rate*100:.1f}% is outside normal range "
                    f"({MIN_TAX_RATE*100:.0f}%-{MAX_TAX_RATE*100:.0f}%)"
                ),
                field="tax_rate",
                expected=f"{MIN_TAX_RATE*100:.0f}%-{MAX_TAX_RATE*100:.0f}%",
                actual=f"{tax_rate*100:.1f}%",
            )

    # Estimate tax rate if we only have amounts
    if tax_amount and subtotal and tax_rate is None:
        estimated_rate = tax_amount / subtotal
        if estimated_rate > MAX_TAX_RATE:
            add_issue(
                issue_type=IssueType.TAX_MISMATCH,
                severity=IssueSeverity.MEDIUM,
                description=(
                    f"Implied tax rate ({estimated_rate*100:.1f}%) seems high "
                    f"for medical billing"
                ),
                field="tax_amount",
            )


def _check_overcharges(
    line_items: list[LineItem],
    add_issue,
    region: str = "US",
    hospital_type: Optional[str] = None,
    city: Optional[str] = None,
) -> None:
    """
    Check for potential overcharges using real medical code database.

    Supports both US and Indian markets:
    - US: Uses CMS Medicare Fee Schedule with CPT/HCPCS codes
    - India: Uses CGHS/PMJAY rates with fuzzy procedure matching

    Args:
        line_items: List of bill line items.
        add_issue: Function to add issues.
        region: Market region ("US" or "IN").
        hospital_type: Type of hospital (for India pricing adjustment).
        city: City name (for India metro tier adjustment).
    """
    currency_symbol = "₹" if region == "IN" else "$"
    
    for i, item in enumerate(line_items):
        code = item.get("code", "")
        total = item.get("total", 0)
        quantity = item.get("quantity", 1) or 1
        description = item.get("description", "")

        if not total:
            continue

        # Use region-specific pricing check
        if region == "IN":
            # India: Use procedure name for fuzzy matching
            _check_overcharge_india(
                item_index=i,
                description=description,
                code=code,
                total=total,
                quantity=quantity,
                hospital_type=hospital_type,
                city=city,
                add_issue=add_issue,
            )
        else:
            # US: Use CPT/HCPCS codes
            _check_overcharge_us(
                item_index=i,
                code=code,
                description=description,
                total=total,
                quantity=quantity,
                add_issue=add_issue,
            )


def _check_overcharge_us(
    item_index: int,
    code: str,
    description: str,
    total: float,
    quantity: int,
    add_issue,
) -> None:
    """Check for overcharges in US market using CPT/HCPCS codes."""
    if not code and not description:
        return
    
    # Try to use real medical code database for pricing
    overpriced, fair_price, message = is_overpriced(
        code=code,
        charged_amount=total / quantity,  # Per-unit price
        threshold_multiplier=OVERCHARGE_MULTIPLIER,
    )

    if overpriced and fair_price:
        # Calculate excess based on actual fair pricing data
        adjusted_fair_price = fair_price * quantity
        excess = total - adjusted_fair_price
        excess_percent = (excess / adjusted_fair_price) * 100 if adjusted_fair_price > 0 else 0

        # Determine severity based on how much over fair price
        if excess_percent > 200:  # More than 3x fair price
            severity = IssueSeverity.CRITICAL
        elif excess_percent > 100:  # More than 2x fair price
            severity = IssueSeverity.HIGH
        elif excess_percent > 50:  # More than 1.5x fair price
            severity = IssueSeverity.MEDIUM
        else:
            severity = IssueSeverity.LOW

        # Get code description from database if available
        code_desc = get_code_description(code)
        item_desc = code_desc if code_desc else description

        add_issue(
            issue_type=IssueType.OVERCHARGE,
            severity=severity,
            description=(
                f"Potential overcharge for '{item_desc}' "
                f"(code: {code}): ${total:.2f} is {excess_percent:.0f}% above "
                f"fair price ${adjusted_fair_price:.2f}"
            ),
            field=f"line_items[{item_index}]",
            expected=f"≤${adjusted_fair_price:.2f}",
            actual=f"${total:.2f}",
            amount_impact=excess,
        )
    
    elif fair_price is None and code:
        # Fallback to legacy thresholds if no database pricing
        threshold = LEGACY_OVERCHARGE_THRESHOLDS.get(
            code,
            LEGACY_OVERCHARGE_THRESHOLDS["default"],
        )
        adjusted_threshold = threshold * quantity

        if total > adjusted_threshold:
            excess = total - adjusted_threshold
            severity = (
                IssueSeverity.CRITICAL if excess > adjusted_threshold
                else IssueSeverity.HIGH if excess > adjusted_threshold * 0.5
                else IssueSeverity.MEDIUM
            )

            add_issue(
                issue_type=IssueType.OVERCHARGE,
                severity=severity,
                description=(
                    f"Potential overcharge for '{description}' "
                    f"(code: {code}): ${total:.2f} exceeds threshold "
                    f"${adjusted_threshold:.2f}"
                ),
                field=f"line_items[{item_index}]",
                expected=f"≤${adjusted_threshold:.2f}",
                actual=f"${total:.2f}",
                amount_impact=excess,
            )


def _check_overcharge_india(
    item_index: int,
    description: str,
    code: str,
    total: float,
    quantity: int,
    hospital_type: Optional[str],
    city: Optional[str],
    add_issue,
) -> None:
    """
    Check for overcharges in Indian market using CGHS/PMJAY rates.
    
    Uses fuzzy matching on procedure descriptions since Indian hospitals
    often don't use standardized CPT codes.
    """
    if not description:
        return
    
    # Map hospital type string to enum
    hosp_type = HospitalType.PRIVATE
    if hospital_type:
        hospital_type_lower = hospital_type.lower()
        if hospital_type_lower in ("government", "govt", "cghs"):
            hosp_type = HospitalType.CGHS_EMPANELED
        elif hospital_type_lower in ("corporate", "chain"):
            hosp_type = HospitalType.CORPORATE
        elif hospital_type_lower in ("nabh", "accredited"):
            hosp_type = HospitalType.NABH_ACCREDITED
    
    # Check for overpricing using Indian database
    overpriced, fair_price, message = is_overpriced_india(
        procedure_name=description,
        charged_amount=total,
        hospital_type=hosp_type,
        city=city,
        threshold_multiplier=OVERCHARGE_MULTIPLIER,
    )
    
    if overpriced and fair_price:
        excess = total - fair_price
        excess_percent = (excess / fair_price) * 100 if fair_price > 0 else 0
        
        # Determine severity based on how much over fair price
        if excess_percent > 200:  # More than 3x fair price
            severity = IssueSeverity.CRITICAL
        elif excess_percent > 100:  # More than 2x fair price
            severity = IssueSeverity.HIGH
        elif excess_percent > 50:  # More than 1.5x fair price
            severity = IssueSeverity.MEDIUM
        else:
            severity = IssueSeverity.LOW
        
        add_issue(
            issue_type=IssueType.OVERCHARGE,
            severity=severity,
            description=(
                f"Potential overcharge for '{description}': "
                f"₹{total:,.0f} is {excess_percent:.0f}% above fair price ₹{fair_price:,.0f}"
            ),
            field=f"line_items[{item_index}]",
            expected=f"≤₹{fair_price:,.0f}",
            actual=f"₹{total:,.0f}",
            amount_impact=excess,
        )
    elif message and "No pricing data" not in message:
        # Log if there was a message but not a definitive overcharge
        logger.debug(f"Indian pricing note for '{description}': {message}")


def _check_quantities(line_items: list[LineItem], add_issue) -> None:
    """
    Check for suspicious quantities.

    Args:
        line_items: List of bill line items.
        add_issue: Function to add issues.
    """
    for i, item in enumerate(line_items):
        quantity = item.get("quantity", 1)

        # Check for zero or negative quantities
        if quantity is not None and quantity <= 0:
            add_issue(
                issue_type=IssueType.QUANTITY_ERROR,
                severity=IssueSeverity.HIGH,
                description=(
                    f"Invalid quantity ({quantity}) for '{item.get('description')}'"
                ),
                field=f"line_items[{i}].quantity",
                expected=">0",
                actual=str(quantity),
            )

        # Check for unusually high quantities
        if quantity is not None and quantity > 10:
            add_issue(
                issue_type=IssueType.QUANTITY_ERROR,
                severity=IssueSeverity.LOW,
                description=(
                    f"Unusually high quantity ({quantity}) for "
                    f"'{item.get('description')}' - verify this is correct"
                ),
                field=f"line_items[{i}].quantity",
                expected="1-10",
                actual=str(quantity),
            )


def _calculate_score(issues: list[AuditIssue]) -> int:
    """
    Calculate overall bill health score (0-100).

    Args:
        issues: List of detected issues.

    Returns:
        int: Score from 0 (many issues) to 100 (no issues).
    """
    if not issues:
        return 100

    # Deduction points per severity
    deductions = {
        "critical": 25,
        "high": 15,
        "medium": 8,
        "low": 3,
    }

    total_deduction = sum(
        deductions.get(issue["severity"], 5)
        for issue in issues
    )

    # Cap at 0
    score = max(0, 100 - total_deduction)

    return score


def _calculate_potential_savings(issues: list[AuditIssue]) -> float:
    """
    Calculate potential savings if issues are resolved.

    Args:
        issues: List of detected issues.

    Returns:
        float: Total potential savings amount.
    """
    return sum(
        issue.get("amount_impact", 0) or 0
        for issue in issues
    )


def get_issue_summary(result: AuditResult) -> str:
    """
    Generate a human-readable summary of audit results.

    Args:
        result: Audit result dictionary.

    Returns:
        str: Formatted summary string.
    """
    lines = [
        f"Audit Score: {result['score']}/100",
        f"Total Issues: {result['total_issues']}",
        "",
        "Issues by Severity:",
        f"  Critical: {result['critical_count']}",
        f"  High: {result['high_count']}",
        f"  Medium: {result['medium_count']}",
        f"  Low: {result['low_count']}",
        "",
        f"Potential Savings: ${result['potential_savings']:.2f}",
    ]

    if result["issues"]:
        lines.append("")
        lines.append("Issue Details:")
        for issue in result["issues"]:
            lines.append(
                f"  [{issue['severity'].upper()}] {issue['type']}: {issue['description']}"
            )

    return "\n".join(lines)

