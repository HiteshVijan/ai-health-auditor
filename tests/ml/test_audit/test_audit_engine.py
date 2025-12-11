"""
Unit tests for audit engine.

Tests billing issue detection with synthetic medical bills.
"""

import pytest
import sys
import os

# Add ml directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml"))

from audit.audit_engine import (
    audit_bill,
    _check_duplicate_charges,
    _check_arithmetic,
    _check_tax,
    _check_overcharges,
    _check_quantities,
    _calculate_score,
    _calculate_potential_savings,
    get_issue_summary,
    ParsedBill,
    LineItem,
    AuditResult,
    IssueType,
    IssueSeverity,
    OVERCHARGE_THRESHOLDS,
)


@pytest.fixture
def clean_bill() -> ParsedBill:
    """Create a clean bill with no issues."""
    return ParsedBill(
        document_id=1,
        total_amount=284.00,
        subtotal=284.00,
        tax_amount=0.0,
        tax_rate=0.0,
        discount=0.0,
        insurance_paid=0.0,
        patient_responsibility=284.00,
        line_items=[
            LineItem(
                code="99213",
                description="Office Visit - Established Patient",
                quantity=1,
                unit_price=150.00,
                total=150.00,
            ),
            LineItem(
                code="85025",
                description="Complete Blood Count (CBC)",
                quantity=1,
                unit_price=45.00,
                total=45.00,
            ),
            LineItem(
                code="80053",
                description="Comprehensive Metabolic Panel",
                quantity=1,
                unit_price=89.00,
                total=89.00,
            ),
        ],
        invoice_number="INV-2024-00123",
        patient_name="John Doe",
        bill_date="2024-01-15",
    )


@pytest.fixture
def bill_with_duplicates() -> ParsedBill:
    """Create a bill with duplicate charges."""
    return ParsedBill(
        document_id=2,
        total_amount=239.00,
        subtotal=239.00,
        tax_amount=0.0,
        tax_rate=None,
        discount=0.0,
        insurance_paid=0.0,
        patient_responsibility=239.00,
        line_items=[
            LineItem(
                code="99213",
                description="Office Visit",
                quantity=1,
                unit_price=150.00,
                total=150.00,
            ),
            LineItem(
                code="85025",
                description="CBC",
                quantity=1,
                unit_price=45.00,
                total=45.00,
            ),
            LineItem(
                code="85025",
                description="CBC",
                quantity=1,
                unit_price=45.00,
                total=45.00,
            ),  # Duplicate!
        ],
        invoice_number="INV-2024-00124",
        patient_name="Jane Smith",
        bill_date="2024-01-16",
    )


@pytest.fixture
def bill_with_arithmetic_errors() -> ParsedBill:
    """Create a bill with arithmetic mismatches."""
    return ParsedBill(
        document_id=3,
        total_amount=300.00,  # Should be 284.00
        subtotal=290.00,  # Should be 284.00
        tax_amount=0.0,
        tax_rate=0.0,
        discount=0.0,
        insurance_paid=0.0,
        patient_responsibility=300.00,
        line_items=[
            LineItem(
                code="99213",
                description="Office Visit",
                quantity=1,
                unit_price=150.00,
                total=150.00,
            ),
            LineItem(
                code="85025",
                description="CBC",
                quantity=2,
                unit_price=45.00,
                total=100.00,  # Should be 90.00
            ),
            LineItem(
                code="80053",
                description="Metabolic Panel",
                quantity=1,
                unit_price=89.00,
                total=89.00,
            ),
        ],
        invoice_number="INV-2024-00125",
        patient_name="Bob Johnson",
        bill_date="2024-01-17",
    )


@pytest.fixture
def bill_with_tax_issues() -> ParsedBill:
    """Create a bill with tax calculation issues."""
    return ParsedBill(
        document_id=4,
        total_amount=320.00,
        subtotal=284.00,
        tax_amount=36.00,  # ~12.7% - too high
        tax_rate=0.127,
        discount=0.0,
        insurance_paid=0.0,
        patient_responsibility=320.00,
        line_items=[
            LineItem(
                code="99213",
                description="Office Visit",
                quantity=1,
                unit_price=150.00,
                total=150.00,
            ),
            LineItem(
                code="85025",
                description="CBC",
                quantity=1,
                unit_price=45.00,
                total=45.00,
            ),
            LineItem(
                code="80053",
                description="Metabolic Panel",
                quantity=1,
                unit_price=89.00,
                total=89.00,
            ),
        ],
        invoice_number="INV-2024-00126",
        patient_name="Alice Brown",
        bill_date="2024-01-18",
    )


@pytest.fixture
def bill_with_overcharges() -> ParsedBill:
    """Create a bill with overcharged items."""
    return ParsedBill(
        document_id=5,
        total_amount=750.00,
        subtotal=750.00,
        tax_amount=0.0,
        tax_rate=0.0,
        discount=0.0,
        insurance_paid=0.0,
        patient_responsibility=750.00,
        line_items=[
            LineItem(
                code="99213",
                description="Office Visit",
                quantity=1,
                unit_price=400.00,  # Threshold is 175
                total=400.00,
            ),
            LineItem(
                code="85025",
                description="CBC",
                quantity=1,
                unit_price=200.00,  # Threshold is 75
                total=200.00,
            ),
            LineItem(
                code="80053",
                description="Metabolic Panel",
                quantity=1,
                unit_price=150.00,  # At threshold
                total=150.00,
            ),
        ],
        invoice_number="INV-2024-00127",
        patient_name="Charlie Davis",
        bill_date="2024-01-19",
    )


@pytest.fixture
def bill_with_missing_fields() -> ParsedBill:
    """Create a bill with missing required fields."""
    return ParsedBill(
        document_id=6,
        total_amount=150.00,
        subtotal=150.00,
        tax_amount=None,
        tax_rate=None,
        discount=None,
        insurance_paid=None,
        patient_responsibility=None,
        line_items=[
            LineItem(
                code="99213",
                description="Office Visit",
                quantity=1,
                unit_price=150.00,
                total=150.00,
            ),
        ],
        invoice_number=None,  # Missing
        patient_name="",  # Empty
        bill_date=None,  # Missing
    )


class TestAuditBill:
    """Test cases for main audit_bill function."""

    def test_clean_bill_high_score(self, clean_bill: ParsedBill):
        """Test that a clean bill gets a high score."""
        result = audit_bill(clean_bill)

        assert result["score"] >= 90
        assert result["total_issues"] == 0
        assert result["potential_savings"] == 0.0

    def test_returns_correct_structure(self, clean_bill: ParsedBill):
        """Test that result has correct structure."""
        result = audit_bill(clean_bill)

        assert "issues" in result
        assert "score" in result
        assert "total_issues" in result
        assert "critical_count" in result
        assert "high_count" in result
        assert "medium_count" in result
        assert "low_count" in result
        assert "potential_savings" in result

    def test_score_range(self, bill_with_duplicates: ParsedBill):
        """Test that score is within valid range."""
        result = audit_bill(bill_with_duplicates)

        assert 0 <= result["score"] <= 100

    def test_issue_structure(self, bill_with_duplicates: ParsedBill):
        """Test that issues have correct structure."""
        result = audit_bill(bill_with_duplicates)

        for issue in result["issues"]:
            assert "id" in issue
            assert "type" in issue
            assert "severity" in issue
            assert "description" in issue


class TestDuplicateDetection:
    """Test cases for duplicate charge detection."""

    def test_detects_duplicates(self, bill_with_duplicates: ParsedBill):
        """Test detection of duplicate charges."""
        result = audit_bill(bill_with_duplicates)

        duplicate_issues = [
            i for i in result["issues"]
            if i["type"] == IssueType.DUPLICATE_CHARGE.value
        ]

        assert len(duplicate_issues) >= 1
        assert "CBC" in duplicate_issues[0]["description"]

    def test_no_false_positives(self, clean_bill: ParsedBill):
        """Test that unique items don't trigger duplicates."""
        result = audit_bill(clean_bill)

        duplicate_issues = [
            i for i in result["issues"]
            if i["type"] == IssueType.DUPLICATE_CHARGE.value
        ]

        assert len(duplicate_issues) == 0

    def test_calculates_duplicate_impact(self, bill_with_duplicates: ParsedBill):
        """Test that duplicate impact amount is calculated."""
        result = audit_bill(bill_with_duplicates)

        duplicate_issues = [
            i for i in result["issues"]
            if i["type"] == IssueType.DUPLICATE_CHARGE.value
        ]

        assert duplicate_issues[0]["amount_impact"] == 45.00


class TestArithmeticChecks:
    """Test cases for arithmetic mismatch detection."""

    def test_detects_subtotal_mismatch(self, bill_with_arithmetic_errors: ParsedBill):
        """Test detection of subtotal mismatch."""
        result = audit_bill(bill_with_arithmetic_errors)

        arithmetic_issues = [
            i for i in result["issues"]
            if i["type"] == IssueType.ARITHMETIC_MISMATCH.value
        ]

        assert len(arithmetic_issues) >= 1

    def test_detects_line_item_calculation_error(
        self,
        bill_with_arithmetic_errors: ParsedBill,
    ):
        """Test detection of quantity × price ≠ total."""
        result = audit_bill(bill_with_arithmetic_errors)

        # Find line item arithmetic issue
        line_item_issues = [
            i for i in result["issues"]
            if i["type"] == IssueType.ARITHMETIC_MISMATCH.value
            and "line_items" in (i.get("field") or "")
        ]

        assert len(line_item_issues) >= 1

    def test_tolerance_allows_small_differences(self):
        """Test that tiny rounding differences are allowed."""
        bill = ParsedBill(
            document_id=100,
            total_amount=100.01,  # Tiny difference
            subtotal=100.00,
            tax_amount=0.0,
            tax_rate=0.0,
            discount=0.0,
            insurance_paid=0.0,
            patient_responsibility=100.01,
            line_items=[
                LineItem(
                    code="99213",
                    description="Test",
                    quantity=1,
                    unit_price=100.00,
                    total=100.00,
                ),
            ],
            invoice_number="TEST-001",
            patient_name="Test User",
            bill_date="2024-01-01",
        )

        result = audit_bill(bill)

        arithmetic_issues = [
            i for i in result["issues"]
            if i["type"] == IssueType.ARITHMETIC_MISMATCH.value
        ]

        assert len(arithmetic_issues) == 0


class TestTaxChecks:
    """Test cases for tax mismatch detection."""

    def test_detects_excessive_tax_rate(self, bill_with_tax_issues: ParsedBill):
        """Test detection of unreasonably high tax rate."""
        result = audit_bill(bill_with_tax_issues)

        tax_issues = [
            i for i in result["issues"]
            if i["type"] == IssueType.TAX_MISMATCH.value
        ]

        assert len(tax_issues) >= 1

    def test_accepts_reasonable_tax(self):
        """Test that reasonable tax rates pass."""
        bill = ParsedBill(
            document_id=101,
            total_amount=108.00,
            subtotal=100.00,
            tax_amount=8.00,
            tax_rate=0.08,
            discount=0.0,
            insurance_paid=0.0,
            patient_responsibility=108.00,
            line_items=[
                LineItem(
                    code="99213",
                    description="Test",
                    quantity=1,
                    unit_price=100.00,
                    total=100.00,
                ),
            ],
            invoice_number="TEST-002",
            patient_name="Test User",
            bill_date="2024-01-01",
        )

        result = audit_bill(bill)

        tax_issues = [
            i for i in result["issues"]
            if i["type"] == IssueType.TAX_MISMATCH.value
        ]

        assert len(tax_issues) == 0


class TestOverchargeDetection:
    """Test cases for overcharge detection."""

    def test_detects_overcharges(self, bill_with_overcharges: ParsedBill):
        """Test detection of prices exceeding thresholds."""
        result = audit_bill(bill_with_overcharges)

        overcharge_issues = [
            i for i in result["issues"]
            if i["type"] == IssueType.OVERCHARGE.value
        ]

        # Should detect office visit and CBC overcharges
        assert len(overcharge_issues) >= 2

    def test_calculates_overcharge_amount(self, bill_with_overcharges: ParsedBill):
        """Test that excess amount is calculated correctly."""
        result = audit_bill(bill_with_overcharges)

        overcharge_issues = [
            i for i in result["issues"]
            if i["type"] == IssueType.OVERCHARGE.value
        ]

        # Office visit: 400 - 175 = 225 excess
        office_visit_issue = next(
            (i for i in overcharge_issues if "Office Visit" in i["description"]),
            None,
        )
        assert office_visit_issue is not None
        assert office_visit_issue["amount_impact"] == 225.00

    def test_respects_quantity_multiplier(self):
        """Test that quantity is considered in threshold calculation."""
        bill = ParsedBill(
            document_id=102,
            total_amount=300.00,
            subtotal=300.00,
            tax_amount=0.0,
            tax_rate=0.0,
            discount=0.0,
            insurance_paid=0.0,
            patient_responsibility=300.00,
            line_items=[
                LineItem(
                    code="99213",
                    description="Office Visit",
                    quantity=2,  # 2 visits
                    unit_price=150.00,
                    total=300.00,  # Under 175 × 2 = 350
                ),
            ],
            invoice_number="TEST-003",
            patient_name="Test User",
            bill_date="2024-01-01",
        )

        result = audit_bill(bill)

        overcharge_issues = [
            i for i in result["issues"]
            if i["type"] == IssueType.OVERCHARGE.value
        ]

        assert len(overcharge_issues) == 0


class TestMissingFields:
    """Test cases for missing field detection."""

    def test_detects_missing_fields(self, bill_with_missing_fields: ParsedBill):
        """Test detection of missing required fields."""
        result = audit_bill(bill_with_missing_fields)

        missing_issues = [
            i for i in result["issues"]
            if i["type"] == IssueType.MISSING_FIELD.value
        ]

        # invoice_number, patient_name, bill_date
        assert len(missing_issues) >= 2


class TestQuantityChecks:
    """Test cases for quantity validation."""

    def test_detects_zero_quantity(self):
        """Test detection of zero quantity."""
        bill = ParsedBill(
            document_id=103,
            total_amount=0.0,
            subtotal=0.0,
            tax_amount=0.0,
            tax_rate=0.0,
            discount=0.0,
            insurance_paid=0.0,
            patient_responsibility=0.0,
            line_items=[
                LineItem(
                    code="99213",
                    description="Office Visit",
                    quantity=0,  # Invalid
                    unit_price=150.00,
                    total=0.00,
                ),
            ],
            invoice_number="TEST-004",
            patient_name="Test User",
            bill_date="2024-01-01",
        )

        result = audit_bill(bill)

        quantity_issues = [
            i for i in result["issues"]
            if i["type"] == IssueType.QUANTITY_ERROR.value
        ]

        assert len(quantity_issues) >= 1

    def test_flags_high_quantities(self):
        """Test flagging of unusually high quantities."""
        bill = ParsedBill(
            document_id=104,
            total_amount=1500.00,
            subtotal=1500.00,
            tax_amount=0.0,
            tax_rate=0.0,
            discount=0.0,
            insurance_paid=0.0,
            patient_responsibility=1500.00,
            line_items=[
                LineItem(
                    code="99213",
                    description="Office Visit",
                    quantity=15,  # Suspiciously high
                    unit_price=100.00,
                    total=1500.00,
                ),
            ],
            invoice_number="TEST-005",
            patient_name="Test User",
            bill_date="2024-01-01",
        )

        result = audit_bill(bill)

        quantity_issues = [
            i for i in result["issues"]
            if i["type"] == IssueType.QUANTITY_ERROR.value
        ]

        assert len(quantity_issues) >= 1
        assert quantity_issues[0]["severity"] == "low"


class TestScoreCalculation:
    """Test cases for score calculation."""

    def test_perfect_score_no_issues(self):
        """Test that no issues gives perfect score."""
        score = _calculate_score([])
        assert score == 100

    def test_critical_issues_major_deduction(self):
        """Test that critical issues cause major deduction."""
        issues = [
            {"severity": "critical", "type": "test", "description": "test"}
        ]
        score = _calculate_score(issues)
        assert score <= 75

    def test_score_floor_at_zero(self):
        """Test that score doesn't go below zero."""
        issues = [
            {"severity": "critical", "type": "test", "description": "test"}
            for _ in range(10)
        ]
        score = _calculate_score(issues)
        assert score == 0


class TestPotentialSavings:
    """Test cases for potential savings calculation."""

    def test_sums_impact_amounts(self):
        """Test that impact amounts are summed correctly."""
        issues = [
            {"amount_impact": 100.0},
            {"amount_impact": 50.0},
            {"amount_impact": 25.0},
        ]
        savings = _calculate_potential_savings(issues)
        assert savings == 175.0

    def test_handles_none_impacts(self):
        """Test handling of None impact amounts."""
        issues = [
            {"amount_impact": 100.0},
            {"amount_impact": None},
            {},
        ]
        savings = _calculate_potential_savings(issues)
        assert savings == 100.0


class TestIssueSummary:
    """Test cases for issue summary generation."""

    def test_generates_summary(self, bill_with_duplicates: ParsedBill):
        """Test summary generation."""
        result = audit_bill(bill_with_duplicates)
        summary = get_issue_summary(result)

        assert "Audit Score:" in summary
        assert "Total Issues:" in summary
        assert "Potential Savings:" in summary

    def test_includes_issue_details(self, bill_with_duplicates: ParsedBill):
        """Test that issue details are included."""
        result = audit_bill(bill_with_duplicates)
        summary = get_issue_summary(result)

        assert "Issue Details:" in summary
        assert "duplicate" in summary.lower()


class TestComplexScenarios:
    """Test cases for complex billing scenarios."""

    def test_multiple_issue_types(self):
        """Test bill with multiple types of issues."""
        bill = ParsedBill(
            document_id=200,
            total_amount=500.00,  # Arithmetic error
            subtotal=400.00,
            tax_amount=50.00,  # Tax mismatch
            tax_rate=0.10,
            discount=0.0,
            insurance_paid=0.0,
            patient_responsibility=500.00,
            line_items=[
                LineItem(
                    code="99213",
                    description="Office Visit",
                    quantity=1,
                    unit_price=300.00,  # Overcharge
                    total=300.00,
                ),
                LineItem(
                    code="85025",
                    description="CBC",
                    quantity=1,
                    unit_price=50.00,
                    total=50.00,
                ),
                LineItem(
                    code="85025",
                    description="CBC",
                    quantity=1,
                    unit_price=50.00,
                    total=50.00,
                ),  # Duplicate
            ],
            invoice_number=None,  # Missing
            patient_name="Test Patient",
            bill_date="2024-01-01",
        )

        result = audit_bill(bill)

        # Should detect multiple issue types
        issue_types = set(i["type"] for i in result["issues"])

        assert IssueType.DUPLICATE_CHARGE.value in issue_types
        assert IssueType.OVERCHARGE.value in issue_types
        assert IssueType.MISSING_FIELD.value in issue_types

        # Score should be low
        assert result["score"] < 50

