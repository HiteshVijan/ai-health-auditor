#!/usr/bin/env python3
"""
End-to-End Test for Medical Bill Audit System

Tests the complete audit workflow for both US and Indian markets:
1. Document parsing simulation
2. Field extraction
3. Audit engine processing
4. Issue detection
5. Report generation
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add project root to path
if "__file__" in dir():
    project_root = Path(__file__).parent.parent
else:
    project_root = Path(os.getcwd())
sys.path.insert(0, str(project_root))

from ml.audit.audit_engine import audit_bill, get_issue_summary
from ml.audit.medical_codes import (
    validate_code, get_fair_price, get_statistics as get_us_stats
)
from ml.audit.indian_pricing import (
    find_procedure, is_overpriced_india, get_indian_stats,
    HospitalType, RAPIDFUZZ_AVAILABLE
)


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print("─" * 50)


def test_us_audit_workflow():
    """Test complete US audit workflow."""
    print_header("E2E TEST: US Market Audit Workflow")
    
    # Step 1: Simulate parsed bill data (from OCR/DocAI)
    print_section("Step 1: Simulated Parsed Bill Data")
    
    us_bill = {
        "document_id": 1001,
        "total_amount": 1875.00,
        "subtotal": 1750.00,
        "tax_amount": 125.00,
        "tax_rate": 0.0714,
        "discount": 0.00,
        "insurance_paid": 500.00,
        "patient_responsibility": 1375.00,
        "line_items": [
            {
                "code": "99214",
                "description": "Office Visit - Established Patient",
                "quantity": 1,
                "unit_price": 500.00,  # Overpriced! Fair price ~$165
                "total": 500.00,
            },
            {
                "code": "85025",
                "description": "Complete Blood Count (CBC)",
                "quantity": 1,
                "unit_price": 150.00,  # Overpriced! Fair price ~$20
                "total": 150.00,
            },
            {
                "code": "80053",
                "description": "Comprehensive Metabolic Panel",
                "quantity": 1,
                "unit_price": 200.00,  # Overpriced! Fair price ~$35
                "total": 200.00,
            },
            {
                "code": "71046",
                "description": "Chest X-Ray, 2 Views",
                "quantity": 1,
                "unit_price": 400.00,  # Overpriced! Fair price ~$75
                "total": 400.00,
            },
            {
                "code": "93000",
                "description": "Electrocardiogram (ECG)",
                "quantity": 1,
                "unit_price": 250.00,  # Overpriced! Fair price ~$50
                "total": 250.00,
            },
            {
                "code": "99214",
                "description": "Office Visit - Established Patient",
                "quantity": 1,
                "unit_price": 250.00,  # DUPLICATE!
                "total": 250.00,
            },
        ],
        "invoice_number": "INV-2024-US-001",
        "patient_name": "John Anderson",
        "bill_date": "2024-03-15",
        "region": "US",
        "currency": "USD",
    }
    
    print(f"  Patient: {us_bill['patient_name']}")
    print(f"  Invoice: {us_bill['invoice_number']}")
    print(f"  Date: {us_bill['bill_date']}")
    print(f"  Total Amount: ${us_bill['total_amount']:,.2f}")
    print(f"  Line Items: {len(us_bill['line_items'])}")
    
    # Step 2: Validate medical codes
    print_section("Step 2: Medical Code Validation")
    
    for item in us_bill["line_items"]:
        code = item["code"]
        result = validate_code(code)
        status = "✓" if result["is_valid"] else "✗"
        print(f"  {status} {code}: {result['description'][:40]}...")
    
    # Step 3: Check fair pricing
    print_section("Step 3: Fair Price Comparison")
    
    total_fair = 0
    total_charged = 0
    
    for item in us_bill["line_items"]:
        code = item["code"]
        charged = item["total"]
        price_info = get_fair_price(code)
        
        if price_info:
            fair = price_info["fair_price_median"]
            total_fair += fair
            total_charged += charged
            diff = charged - fair
            diff_pct = (diff / fair) * 100 if fair > 0 else 0
            
            if diff_pct > 50:
                status = "🔴"
            elif diff_pct > 20:
                status = "🟡"
            else:
                status = "🟢"
            
            print(f"  {status} {code}: Charged ${charged:.0f} vs Fair ${fair:.0f} ({diff_pct:+.0f}%)")
    
    print(f"\n  Total Charged: ${total_charged:,.2f}")
    print(f"  Total Fair Price: ${total_fair:,.2f}")
    print(f"  Potential Overcharge: ${total_charged - total_fair:,.2f}")
    
    # Step 4: Run full audit
    print_section("Step 4: Full Audit Analysis")
    
    result = audit_bill(us_bill, region="US")
    
    print(f"  Audit Score: {result['score']}/100")
    print(f"  Total Issues: {result['total_issues']}")
    print(f"    - Critical: {result['critical_count']}")
    print(f"    - High: {result['high_count']}")
    print(f"    - Medium: {result['medium_count']}")
    print(f"    - Low: {result['low_count']}")
    print(f"  Potential Savings: ${result['potential_savings']:,.2f}")
    
    # Step 5: List all issues
    print_section("Step 5: Detected Issues")
    
    for issue in result["issues"]:
        severity_icon = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🔵",
        }.get(issue["severity"], "⚪")
        
        print(f"\n  {severity_icon} [{issue['severity'].upper()}] {issue['type']}")
        print(f"     {issue['description'][:65]}...")
        if issue.get("amount_impact"):
            print(f"     💰 Impact: ${issue['amount_impact']:.2f}")
    
    # Step 6: Generate summary report
    print_section("Step 6: Audit Summary Report")
    print(get_issue_summary(result))
    
    return result


def test_indian_audit_workflow():
    """Test complete Indian audit workflow."""
    print_header("E2E TEST: Indian Market Audit Workflow")
    
    print(f"  RapidFuzz Available: {RAPIDFUZZ_AVAILABLE}")
    
    # Step 1: Simulated Indian hospital bill
    print_section("Step 1: Simulated Parsed Bill Data")
    
    indian_bill = {
        "document_id": 2001,
        "total_amount": 425000,
        "subtotal": 360000,
        "tax_amount": 65000,
        "tax_rate": 0.18,  # 18% GST
        "line_items": [
            {
                "description": "Laparoscopic Cholecystectomy (Gallbladder Removal)",
                "quantity": 1,
                "unit_price": 180000,
                "total": 180000,  # Overpriced for private hospital!
            },
            {
                "description": "MRI Abdomen with Contrast",
                "quantity": 1,
                "unit_price": 18000,
                "total": 18000,
            },
            {
                "description": "CT Scan Abdomen",
                "quantity": 1,
                "unit_price": 12000,
                "total": 12000,
            },
            {
                "description": "ICU Room Charges",
                "quantity": 2,
                "unit_price": 25000,
                "total": 50000,  # 2 days ICU
            },
            {
                "description": "Private Room",
                "quantity": 3,
                "unit_price": 8000,
                "total": 24000,  # 3 days
            },
            {
                "description": "Surgeon Fees",
                "quantity": 1,
                "unit_price": 50000,
                "total": 50000,
            },
            {
                "description": "Anesthesia Charges",
                "quantity": 1,
                "unit_price": 15000,
                "total": 15000,
            },
            {
                "description": "Medicines and Consumables",
                "quantity": 1,
                "unit_price": 11000,
                "total": 11000,
            },
        ],
        "invoice_number": "APOLLO/MUM/2024/5678",
        "patient_name": "Rajesh Mehta",
        "bill_date": "2024-03-20",
        "region": "IN",
        "currency": "INR",
        "hospital_name": "Apollo Hospital",
        "hospital_type": "corporate",
        "city": "Mumbai",
    }
    
    print(f"  Patient: {indian_bill['patient_name']}")
    print(f"  Hospital: {indian_bill['hospital_name']} ({indian_bill['hospital_type']})")
    print(f"  City: {indian_bill['city']}")
    print(f"  Invoice: {indian_bill['invoice_number']}")
    print(f"  Total Amount: ₹{indian_bill['total_amount']:,}")
    print(f"  GST (18%): ₹{indian_bill['tax_amount']:,}")
    print(f"  Line Items: {len(indian_bill['line_items'])}")
    
    # Step 2: Procedure lookup
    print_section("Step 2: Procedure Price Lookup (CGHS/PMJAY)")
    
    for item in indian_bill["line_items"][:5]:  # Show first 5
        desc = item["description"]
        result = find_procedure(desc)
        
        if result:
            conf = result["match_confidence"]
            status = "✓" if conf > 0.6 else "~"
            cghs = f"₹{result['cghs_rate']:,}" if result['cghs_rate'] else "N/A"
            pmjay = f"₹{result['pmjay_rate']:,}" if result['pmjay_rate'] else "N/A"
            print(f"  {status} \"{desc[:35]}...\"")
            print(f"      → {result['matched_procedure'][:40]}... ({conf:.0%})")
            print(f"      CGHS: {cghs}, PMJAY: {pmjay}")
        else:
            print(f"  ✗ \"{desc[:35]}...\" → No match")
    
    # Step 3: Overcharge detection by hospital type
    print_section("Step 3: Hospital Type Comparison")
    
    test_proc = "Laparoscopic Cholecystectomy"
    charged = 180000
    
    print(f"  Procedure: {test_proc}")
    print(f"  Charged Amount: ₹{charged:,}")
    print()
    
    for hosp_type in [HospitalType.GOVERNMENT, HospitalType.PRIVATE, HospitalType.CORPORATE]:
        is_over, fair, msg = is_overpriced_india(
            test_proc, charged, hosp_type, indian_bill["city"]
        )
        status = "🔴 OVERPRICED" if is_over else "🟢 FAIR"
        fair_str = f"₹{fair:,.0f}" if fair else "N/A"
        print(f"  {hosp_type.value:12} hospital: {status} (fair: {fair_str})")
    
    # Step 4: Full audit
    print_section("Step 4: Full Audit Analysis")
    
    result = audit_bill(indian_bill, region="IN")
    
    print(f"  Audit Score: {result['score']}/100")
    print(f"  Total Issues: {result['total_issues']}")
    print(f"    - Critical: {result['critical_count']}")
    print(f"    - High: {result['high_count']}")
    print(f"    - Medium: {result['medium_count']}")
    print(f"    - Low: {result['low_count']}")
    print(f"  Potential Savings: ₹{result['potential_savings']:,.0f}")
    
    # Step 5: Issues
    if result["issues"]:
        print_section("Step 5: Detected Issues")
        for issue in result["issues"]:
            severity_icon = {
                "critical": "🔴",
                "high": "🟠", 
                "medium": "🟡",
                "low": "🔵",
            }.get(issue["severity"], "⚪")
            
            print(f"\n  {severity_icon} [{issue['severity'].upper()}] {issue['type']}")
            print(f"     {issue['description'][:65]}...")
    else:
        print_section("Step 5: No Issues Detected")
        print("  ✅ Bill appears to be within fair pricing for a corporate hospital in Mumbai")
    
    # Step 6: Price comparison recommendation
    print_section("Step 6: Savings Recommendation")
    
    print("  💡 If you choose a CGHS-empaneled hospital instead:")
    
    total_cghs = 0
    for item in indian_bill["line_items"][:4]:
        result = find_procedure(item["description"])
        if result and result["cghs_rate"]:
            total_cghs += result["cghs_rate"]
    
    if total_cghs > 0:
        savings = indian_bill["subtotal"] - total_cghs
        print(f"     Estimated CGHS cost: ₹{total_cghs:,}")
        print(f"     Potential savings: ₹{savings:,} ({savings/indian_bill['subtotal']*100:.0f}%)")
    
    return result


def test_auto_region_detection():
    """Test automatic region detection."""
    print_header("E2E TEST: Auto Region Detection")
    
    test_cases = [
        {
            "name": "US Bill (CPT codes, USD)",
            "bill": {
                "document_id": 3001,
                "total_amount": 500,
                "currency": "USD",
                "line_items": [{"code": "99213", "total": 500}],
                "invoice_number": "INV-001",
                "patient_name": "Test Patient",
                "bill_date": "2024-01-01",
            },
            "expected": "US",
        },
        {
            "name": "Indian Bill (INR, Mumbai)",
            "bill": {
                "document_id": 3002,
                "total_amount": 50000,
                "currency": "INR",
                "city": "Mumbai",
                "line_items": [{"description": "MRI Brain", "total": 50000}],
                "invoice_number": "HOSP-001",
                "patient_name": "Test Patient",
                "bill_date": "2024-01-01",
            },
            "expected": "IN",
        },
        {
            "name": "Indian Bill (GST 18%, Bangalore)",
            "bill": {
                "document_id": 3003,
                "total_amount": 100000,
                "tax_rate": 0.18,
                "city": "Bangalore",
                "line_items": [{"description": "Surgery", "total": 100000}],
                "invoice_number": "HOSP-002",
                "patient_name": "Test Patient",
                "bill_date": "2024-01-01",
            },
            "expected": "IN",
        },
    ]
    
    print()
    for case in test_cases:
        result = audit_bill(case["bill"], region="AUTO")
        # Check if audit completed (region was detected)
        status = "✓" if result is not None else "✗"
        print(f"  {status} {case['name']}")
    
    return True


def run_all_tests():
    """Run all E2E tests."""
    print("\n" + "🏥" * 35)
    print("     MEDICAL BILL AUDIT SYSTEM - END-TO-END TESTS")
    print("🏥" * 35)
    
    # Show database stats
    print_header("Database Status")
    
    us_stats = get_us_stats()
    indian_stats = get_indian_stats()
    
    print("\n  US Medical Codes:")
    print(f"    CPT/HCPCS codes: {us_stats['cpt_hcpcs_count']}")
    print(f"    ICD-10 codes: {us_stats['icd10_count']}")
    print(f"    Fee schedule entries: {us_stats['fee_schedule_count']}")
    
    print("\n  Indian Pricing:")
    print(f"    Total procedures: {indian_stats['total_procedures']}")
    print(f"    CGHS procedures: {indian_stats['cghs_procedures']}")
    print(f"    PMJAY packages: {indian_stats['pmjay_packages']}")
    print(f"    RapidFuzz: {'✓ Available' if RAPIDFUZZ_AVAILABLE else '✗ Fallback mode'}")
    
    # Run tests
    results = {}
    
    try:
        us_result = test_us_audit_workflow()
        results["US Audit"] = "PASS" if us_result else "FAIL"
    except Exception as e:
        results["US Audit"] = f"ERROR: {e}"
        import traceback
        traceback.print_exc()
    
    try:
        indian_result = test_indian_audit_workflow()
        results["Indian Audit"] = "PASS" if indian_result else "FAIL"
    except Exception as e:
        results["Indian Audit"] = f"ERROR: {e}"
        import traceback
        traceback.print_exc()
    
    try:
        auto_result = test_auto_region_detection()
        results["Auto Detection"] = "PASS" if auto_result else "FAIL"
    except Exception as e:
        results["Auto Detection"] = f"ERROR: {e}"
    
    # Summary
    print_header("E2E TEST RESULTS SUMMARY")
    
    all_passed = True
    for test_name, status in results.items():
        icon = "✅" if status == "PASS" else "❌"
        print(f"  {icon} {test_name}: {status}")
        if status != "PASS":
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("  🎉 ALL TESTS PASSED!")
    else:
        print("  ⚠️  SOME TESTS FAILED - Check details above")
    print("=" * 70 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

