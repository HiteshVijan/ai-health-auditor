#!/usr/bin/env python3
"""
🏥 AI Health Bill Auditor - Demo Script for Pitch

This script demonstrates the full capabilities of the system
for both US and Indian healthcare markets.

Run this to show investors/stakeholders what the system can do!

Usage:
    python run_demo.py
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Colors
class C:
    G = '\033[92m'   # Green
    Y = '\033[93m'   # Yellow
    R = '\033[91m'   # Red
    B = '\033[94m'   # Blue
    M = '\033[95m'   # Magenta
    C = '\033[96m'   # Cyan
    W = '\033[97m'   # White
    BOLD = '\033[1m'
    END = '\033[0m'

def slow_print(text, delay=0.02):
    """Print text with typing effect."""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def pause(msg="Press Enter to continue..."):
    input(f"\n{C.Y}{msg}{C.END}")

def clear():
    print("\033[H\033[J", end="")

def demo_header():
    clear()
    print(f"""
{C.BOLD}{C.C}
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   🏥  AI HEALTH BILL AUDITOR                                        ║
║                                                                      ║
║   Detect Overcharges • Save Money • Both US & India Markets         ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
{C.END}
    """)

def demo_intro():
    demo_header()
    print(f"""
{C.BOLD}Welcome to the AI Health Bill Auditor Demo!{C.END}

This system helps patients identify:
  • {C.G}Overcharges{C.END} - Are you being charged more than fair market price?
  • {C.G}Duplicate charges{C.END} - Same service billed multiple times?
  • {C.G}Arithmetic errors{C.END} - Do the numbers add up correctly?
  • {C.G}Invalid codes{C.END} - Are the billing codes legitimate?

{C.BOLD}Markets Supported:{C.END}
  🇺🇸 United States - CPT/HCPCS codes with Medicare pricing benchmarks
  🇮🇳 India - CGHS/PMJAY rates with hospital type adjustments

{C.BOLD}Built with FREE resources:{C.END}
  • CMS medical codes (public domain)
  • CGHS rates (Government of India, public)
  • PMJAY package rates (Ayushman Bharat, public)
  • No paid APIs required!
    """)
    pause()

def demo_database():
    demo_header()
    print(f"{C.BOLD}{C.B}📊 MEDICAL CODE DATABASE{C.END}\n")
    
    from ml.audit.medical_codes import get_statistics
    from ml.audit.indian_pricing import get_indian_stats, RAPIDFUZZ_AVAILABLE
    
    us_stats = get_statistics()
    indian_stats = get_indian_stats()
    
    print(f"{C.BOLD}US Healthcare (Medicare/CMS):{C.END}")
    print(f"  • {C.G}{us_stats['cpt_hcpcs_count']}{C.END} CPT/HCPCS procedure codes")
    print(f"  • {C.G}{us_stats['icd10_count']}{C.END} ICD-10 diagnosis codes")
    print(f"  • {C.G}{us_stats['fee_schedule_count']}{C.END} pricing benchmarks")
    
    print(f"\n{C.BOLD}Indian Healthcare (CGHS/PMJAY):{C.END}")
    print(f"  • {C.G}{indian_stats['total_procedures']}{C.END} total procedures indexed")
    print(f"  • {C.G}{indian_stats['cghs_procedures']}{C.END} CGHS rate entries")
    print(f"  • {C.G}{indian_stats['pmjay_packages']}{C.END} Ayushman Bharat packages")
    print(f"  • Fuzzy matching: {C.G}{'RapidFuzz' if RAPIDFUZZ_AVAILABLE else 'Standard'}{C.END}")
    
    pause()

def demo_us_bill():
    demo_header()
    print(f"{C.BOLD}{C.B}🇺🇸 US BILL AUDIT DEMO{C.END}\n")
    
    from ml.audit.audit_engine import audit_bill
    from ml.audit.medical_codes import get_fair_price
    
    # Create a sample overpriced US bill
    us_bill = {
        'document_id': 1001,
        'total_amount': 2350.00,
        'subtotal': 2350.00,
        'line_items': [
            {'code': '99214', 'description': 'Office Visit - Established Patient', 
             'quantity': 1, 'unit_price': 450.00, 'total': 450.00},
            {'code': '85025', 'description': 'Complete Blood Count (CBC)', 
             'quantity': 1, 'unit_price': 150.00, 'total': 150.00},
            {'code': '80053', 'description': 'Comprehensive Metabolic Panel', 
             'quantity': 1, 'unit_price': 250.00, 'total': 250.00},
            {'code': '71046', 'description': 'Chest X-Ray, 2 Views', 
             'quantity': 1, 'unit_price': 500.00, 'total': 500.00},
            {'code': '70553', 'description': 'MRI Brain with/without Contrast', 
             'quantity': 1, 'unit_price': 4500.00, 'total': 4500.00},
        ],
        'invoice_number': 'INV-2024-0315',
        'patient_name': 'Sarah Johnson',
        'bill_date': '2024-03-15',
        'region': 'US',
    }
    
    print(f"{C.BOLD}Patient Bill:{C.END}")
    print(f"  Patient: {us_bill['patient_name']}")
    print(f"  Date: {us_bill['bill_date']}")
    print(f"  Total Billed: {C.R}${us_bill['total_amount']:,.2f}{C.END}")
    
    print(f"\n{C.BOLD}Line Items:{C.END}")
    print(f"  {'Code':<8} {'Description':<35} {'Charged':>12} {'Fair Price':>12} {'Status':>10}")
    print(f"  {'-'*85}")
    
    total_fair = 0
    for item in us_bill['line_items']:
        code = item['code']
        desc = item['description'][:33]
        charged = item['total']
        
        price_info = get_fair_price(code)
        if price_info:
            fair = price_info['fair_price_median']
            total_fair += fair
            diff_pct = ((charged - fair) / fair) * 100
            
            if diff_pct > 100:
                status = f"{C.R}⚠️ +{diff_pct:.0f}%{C.END}"
            elif diff_pct > 50:
                status = f"{C.Y}⚠️ +{diff_pct:.0f}%{C.END}"
            else:
                status = f"{C.G}✓{C.END}"
            
            print(f"  {code:<8} {desc:<35} ${charged:>10,.2f} ${fair:>10,.2f} {status}")
        else:
            print(f"  {code:<8} {desc:<35} ${charged:>10,.2f} {'N/A':>12}")
    
    pause("Press Enter to run full audit...")
    
    # Run audit
    print(f"\n{C.BOLD}Running AI Audit...{C.END}")
    time.sleep(1)
    
    result = audit_bill(us_bill, region='US')
    
    print(f"\n{C.BOLD}📋 AUDIT RESULTS:{C.END}")
    print(f"  Audit Score: {C.R if result['score'] < 50 else C.Y if result['score'] < 80 else C.G}{result['score']}/100{C.END}")
    print(f"  Issues Found: {result['total_issues']}")
    print(f"    • Critical: {C.R}{result['critical_count']}{C.END}")
    print(f"    • High: {C.Y}{result['high_count']}{C.END}")
    print(f"    • Medium: {result['medium_count']}")
    print(f"    • Low: {result['low_count']}")
    
    print(f"\n  {C.BOLD}{C.G}💰 POTENTIAL SAVINGS: ${result['potential_savings']:,.2f}{C.END}")
    
    if result['issues']:
        print(f"\n{C.BOLD}Issues Detected:{C.END}")
        for issue in result['issues'][:5]:
            icon = '🔴' if issue['severity'] == 'critical' else '🟡' if issue['severity'] in ['high', 'medium'] else '🔵'
            print(f"  {icon} {issue['description'][:70]}...")
    
    pause()

def demo_indian_bill():
    demo_header()
    print(f"{C.BOLD}{C.B}🇮🇳 INDIAN BILL AUDIT DEMO{C.END}\n")
    
    from ml.audit.audit_engine import audit_bill
    from ml.audit.indian_pricing import find_procedure, is_overpriced_india, HospitalType
    
    # Create a sample Indian hospital bill
    indian_bill = {
        'document_id': 2001,
        'total_amount': 425000,
        'subtotal': 360000,
        'tax_amount': 65000,
        'tax_rate': 0.18,
        'line_items': [
            {'description': 'Laparoscopic Cholecystectomy (Gallbladder Surgery)', 
             'quantity': 1, 'total': 180000},
            {'description': 'MRI Abdomen with Contrast', 
             'quantity': 1, 'total': 18000},
            {'description': 'CT Scan Abdomen', 
             'quantity': 1, 'total': 15000},
            {'description': 'ICU Room Charges', 
             'quantity': 2, 'total': 50000},
            {'description': 'Private Room', 
             'quantity': 3, 'total': 30000},
            {'description': 'Surgeon Fees', 
             'quantity': 1, 'total': 45000},
            {'description': 'Medicines & Consumables', 
             'quantity': 1, 'total': 22000},
        ],
        'invoice_number': 'APOLLO/MUM/2024/5678',
        'patient_name': 'Rajesh Sharma',
        'bill_date': '2024-03-20',
        'region': 'IN',
        'hospital_name': 'Apollo Hospital',
        'hospital_type': 'corporate',
        'city': 'Mumbai',
    }
    
    print(f"{C.BOLD}Patient Bill:{C.END}")
    print(f"  Patient: {indian_bill['patient_name']}")
    print(f"  Hospital: {indian_bill['hospital_name']} ({indian_bill['hospital_type'].capitalize()})")
    print(f"  City: {indian_bill['city']}")
    print(f"  Total Billed: {C.Y}₹{indian_bill['total_amount']:,}{C.END}")
    print(f"  GST (18%): ₹{indian_bill['tax_amount']:,}")
    
    print(f"\n{C.BOLD}Line Items with CGHS/PMJAY Comparison:{C.END}")
    print(f"  {'Procedure':<40} {'Charged':>12} {'CGHS Rate':>12} {'PMJAY':>12}")
    print(f"  {'-'*80}")
    
    for item in indian_bill['line_items'][:5]:
        desc = item['description'][:38]
        charged = item['total']
        
        price_info = find_procedure(item['description'])
        if price_info:
            cghs = f"₹{price_info['cghs_rate']:,}" if price_info['cghs_rate'] else "N/A"
            pmjay = f"₹{price_info['pmjay_rate']:,}" if price_info['pmjay_rate'] else "N/A"
        else:
            cghs = "N/A"
            pmjay = "N/A"
        
        print(f"  {desc:<40} ₹{charged:>10,} {cghs:>12} {pmjay:>12}")
    
    # Show hospital type comparison
    print(f"\n{C.BOLD}💡 Same Surgery - Different Hospital Types:{C.END}")
    procedure = "Laparoscopic Cholecystectomy"
    charged = 180000
    
    for hosp_type, hosp_name in [
        (HospitalType.GOVERNMENT, "Government"),
        (HospitalType.CGHS_EMPANELED, "CGHS Empaneled"),
        (HospitalType.PRIVATE, "Private"),
        (HospitalType.CORPORATE, "Corporate"),
    ]:
        is_over, fair, msg = is_overpriced_india(procedure, charged, hosp_type, "Mumbai")
        if fair:
            if is_over:
                status = f"{C.R}Overpriced by ₹{charged - fair:,.0f}{C.END}"
            else:
                status = f"{C.G}Within fair range{C.END}"
            print(f"  {hosp_name:<18}: Fair price ₹{fair:,.0f} → {status}")
    
    pause("Press Enter to run full audit...")
    
    # Run audit
    print(f"\n{C.BOLD}Running AI Audit...{C.END}")
    time.sleep(1)
    
    result = audit_bill(indian_bill, region='IN')
    
    print(f"\n{C.BOLD}📋 AUDIT RESULTS:{C.END}")
    print(f"  Audit Score: {C.G if result['score'] >= 80 else C.Y}{result['score']}/100{C.END}")
    print(f"  Issues Found: {result['total_issues']}")
    
    if result['total_issues'] == 0:
        print(f"\n  {C.G}✓ Bill is within expected range for a {indian_bill['hospital_type']} hospital in {indian_bill['city']}{C.END}")
    
    # Show savings recommendation
    print(f"\n{C.BOLD}💰 SAVINGS RECOMMENDATION:{C.END}")
    print(f"  If you choose a CGHS-empaneled hospital instead:")
    print(f"  • Estimated savings: {C.G}₹50,000 - ₹1,00,000{C.END}")
    print(f"  • Ayushman Bharat (if eligible): Surgery could be {C.G}FREE{C.END}")
    
    pause()

def demo_comparison():
    demo_header()
    print(f"{C.BOLD}{C.B}🌍 MARKET COMPARISON{C.END}\n")
    
    print(f"""
{C.BOLD}US Market Features:{C.END}
  ✓ CPT/HCPCS code validation
  ✓ Medicare fee schedule benchmarks
  ✓ ICD-10 diagnosis code support
  ✓ Fair pricing from CMS data

{C.BOLD}Indian Market Features:{C.END}
  ✓ CGHS (Central Govt) rate comparison
  ✓ PMJAY (Ayushman Bharat) package rates
  ✓ Hospital type pricing adjustments
  ✓ City tier pricing (Metro/Tier 1/2/3)
  ✓ Fuzzy procedure name matching

{C.BOLD}Common Features:{C.END}
  ✓ Duplicate charge detection
  ✓ Arithmetic error detection
  ✓ Auto region detection
  ✓ Potential savings calculation
  ✓ Issue severity classification

{C.BOLD}Business Model Options:{C.END}
  • B2C: Direct to patients (freemium)
  • B2B: Insurance companies
  • B2B: TPAs (Third Party Administrators)
  • B2B: Employers (employee benefit)
  • B2G: Government health schemes
    """)
    
    pause()

def demo_summary():
    demo_header()
    print(f"""
{C.BOLD}{C.G}
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║   🎉 DEMO COMPLETE!                                                 ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
{C.END}

{C.BOLD}What We Demonstrated:{C.END}
  ✓ Real-time medical bill auditing
  ✓ Overcharge detection with fair pricing data
  ✓ Support for both US and Indian markets
  ✓ Hospital type and location-based pricing
  ✓ Potential savings calculation

{C.BOLD}Technology Stack:{C.END}
  • Backend: Python/FastAPI
  • Frontend: React/TypeScript/Vite
  • ML: Custom audit engine with fuzzy matching
  • Database: SQLite (dev) / PostgreSQL (prod)
  
{C.BOLD}Free Resources Used:{C.END}
  • CMS ICD-10/CPT codes (Public Domain)
  • Medicare Fee Schedule (Public Domain)
  • CGHS Rates (Govt of India, Public)
  • PMJAY Packages (Ayushman Bharat, Public)

{C.BOLD}Ready for:{C.END}
  • MVP launch
  • Pilot with insurance partners
  • Integration with hospital systems
  • Mobile app development

{C.Y}Contact: [Your Email/LinkedIn]{C.END}
    """)

def main():
    try:
        demo_intro()
        demo_database()
        demo_us_bill()
        demo_indian_bill()
        demo_comparison()
        demo_summary()
    except KeyboardInterrupt:
        print(f"\n\n{C.Y}Demo interrupted. Thanks for watching!{C.END}\n")
    except Exception as e:
        print(f"\n{C.R}Error: {e}{C.END}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

