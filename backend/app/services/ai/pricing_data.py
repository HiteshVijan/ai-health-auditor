"""
Market Pricing Reference Data

Contains benchmark pricing for India and US healthcare.
Easy to update as rates change.
"""

# =============================================================================
# INDIAN HEALTHCARE PRICING
# =============================================================================

INDIA_PRICING = {
    # CGHS (Central Government Health Scheme) Rates - Government Benchmark
    "cghs_rates": {
        # Lab Tests
        "renal_function_test": 250,
        "kidney_function_test": 250,
        "kft": 250,
        "tacrolimus_level": 800,
        "cbc": 80,
        "complete_blood_count": 80,
        "lipid_profile": 150,
        "liver_function_test": 200,
        "lft": 200,
        "thyroid_profile": 300,
        "tsh": 150,
        "hba1c": 300,
        "vitamin_d": 500,
        "vitamin_b12": 400,
        "urine_routine": 50,
        "blood_sugar_fasting": 30,
        "blood_sugar_pp": 30,
        
        # Imaging
        "xray_chest": 100,
        "usg_abdomen": 500,
        "ct_scan_head": 2000,
        "ct_scan_abdomen": 3000,
        "mri_brain": 3000,
        "mri_spine": 4000,
        "ecg": 100,
        "echo": 800,
        "2d_echo": 800,
        
        # Consultations
        "opd_consultation": 300,
        "specialist_consultation": 500,
        "diagnostic_visit": 300,
    },
    
    # Competitor Lab Pricing (Dr. Lal, SRL, Thyrocare)
    "diagnostic_chains": {
        "dr_lal_pathlabs": {
            "renal_function_test": 450,
            "tacrolimus_level": 1500,
            "cbc": 180,
            "lipid_profile": 400,
            "thyroid_profile": 600,
        },
        "srl_diagnostics": {
            "renal_function_test": 400,
            "tacrolimus_level": 1400,
            "cbc": 160,
            "lipid_profile": 350,
            "thyroid_profile": 550,
        },
        "thyrocare": {
            "renal_function_test": 350,
            "tacrolimus_level": 1200,
            "cbc": 120,
            "lipid_profile": 300,
            "thyroid_profile": 450,
        },
    },
    
    # Hospital Type Multipliers (vs CGHS rates)
    "hospital_multipliers": {
        "government": 1.0,
        "cghs_empaneled": 1.2,
        "private_small": 1.5,
        "private_medium": 2.0,
        "corporate": 2.5,  # Apollo, Fortis, Max
        "super_specialty": 3.0,  # Medanta, AIIMS-private wings
    },
    
    # City Tier Adjustments
    "city_tiers": {
        "tier_1": ["mumbai", "delhi", "bangalore", "chennai", "hyderabad", "kolkata", "pune"],
        "tier_2": ["lucknow", "jaipur", "ahmedabad", "chandigarh", "kochi", "indore"],
        "tier_3": [],  # All other cities
    },
    "city_multipliers": {
        "tier_1": 1.3,
        "tier_2": 1.1,
        "tier_3": 1.0,
    },
}


# =============================================================================
# US HEALTHCARE PRICING  
# =============================================================================

US_PRICING = {
    # Medicare Fee Schedule (2024 rates)
    "medicare_rates": {
        # Office Visits (Evaluation & Management)
        "99213": 75,   # Established patient, low complexity
        "99214": 110,  # Established patient, moderate
        "99215": 150,  # Established patient, high
        "99203": 100,  # New patient, low
        "99204": 150,  # New patient, moderate
        "99205": 200,  # New patient, high
        
        # Lab Tests
        "85025": 11,   # CBC
        "80053": 14,   # Comprehensive metabolic panel
        "80061": 18,   # Lipid panel
        "84443": 23,   # TSH
        "82947": 8,    # Glucose
        
        # Imaging
        "71046": 30,   # Chest X-ray
        "70553": 350,  # MRI Brain with contrast
        "74177": 400,  # CT Abdomen with contrast
        "93000": 18,   # ECG
    },
    
    # Fair Health Consumer Estimates (uninsured)
    "fair_health": {
        "office_visit_primary": 150,
        "office_visit_specialist": 250,
        "emergency_room": 1500,
        "mri_brain": 1500,
        "ct_scan": 1200,
    },
}


def get_pricing_context(region: str) -> str:
    """
    Get pricing context for AI prompts based on region.
    
    Args:
        region: "IN" for India, "US" for United States
    
    Returns:
        Formatted pricing reference string for AI prompt
    """
    if region == "IN":
        return """
INDIAN HEALTHCARE PRICING REFERENCE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 BENCHMARK: CGHS (Central Government Health Scheme) Rates
These are the government-mandated fair prices.

Common Test CGHS Rates:
• Renal Function Test (KFT): ₹250
• Tacrolimus Level: ₹800  
• CBC: ₹80
• Lipid Profile: ₹150
• Thyroid Profile (T3/T4/TSH): ₹300
• HbA1c: ₹300
• Liver Function Test: ₹200

Imaging CGHS Rates:
• X-Ray Chest: ₹100
• USG Abdomen: ₹500
• CT Scan: ₹2,000-3,000
• MRI: ₹3,000-4,000
• ECG: ₹100
• 2D Echo: ₹800

Consultation Rates:
• OPD Visit: ₹300
• Specialist: ₹500

🏥 HOSPITAL TYPE MARKUPS (vs CGHS):
• Government Hospital: 1x (CGHS rate)
• CGHS Empaneled: 1.2x
• Private Hospital: 1.5-2x
• Corporate (Apollo, Fortis, Max): 2-2.5x
• Super Specialty (Medanta): 2.5-3x

💊 COMPETITOR LAB PRICES:
• Dr. Lal PathLabs: ~1.5x CGHS
• SRL Diagnostics: ~1.4x CGHS
• Thyrocare: ~1.2x CGHS (best value)

🏙️ CITY ADJUSTMENTS:
• Metro (Delhi, Mumbai): +30%
• Tier-2 (Lucknow, Jaipur): +10%
"""
    else:
        return """
US HEALTHCARE PRICING REFERENCE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 BENCHMARK: Medicare Fee Schedule
Government reimbursement rates (typically 20-40% of hospital charges)

Common CPT Codes:
• 99214 (Office Visit): $110
• 85025 (CBC): $11
• 80053 (Metabolic Panel): $14
• 70553 (MRI Brain): $350
• 74177 (CT Abdomen): $400

💡 NEGOTIATION FACTS:
• Hospitals routinely give 20-50% discounts for uninsured
• Cash pay often cheaper than insurance copay
• Ask for "self-pay discount" or "prompt pay discount"
• Many hospitals have charity care programs
"""


def get_competitor_price(test_name: str, competitor: str = "thyrocare") -> float:
    """
    Get competitor price for a specific test.
    
    Args:
        test_name: Name of the test (normalized)
        competitor: Which competitor to check
    
    Returns:
        Price or 0 if not found
    """
    test_key = test_name.lower().replace(" ", "_").replace("-", "_")
    
    chain_data = INDIA_PRICING["diagnostic_chains"].get(competitor, {})
    return chain_data.get(test_key, 0)


def get_cghs_rate(test_name: str) -> float:
    """
    Get CGHS rate for a test.
    
    Args:
        test_name: Name of the test
    
    Returns:
        CGHS rate or 0 if not found
    """
    test_key = test_name.lower().replace(" ", "_").replace("-", "_")
    return INDIA_PRICING["cghs_rates"].get(test_key, 0)

