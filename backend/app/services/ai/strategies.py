"""
Negotiation Strategies & Insider Tips

Evidence-based negotiation strategies and insider knowledge
about hospital billing practices.
"""

from typing import List, Dict

# =============================================================================
# INSIDER TIPS BY HOSPITAL TYPE
# =============================================================================

INSIDER_TIPS = {
    "corporate": [
        "Corporate hospitals (Medanta, Apollo, Fortis) have 25-40% margin on diagnostics - there's always room to negotiate",
        "Ask for 'corporate rate' or 'panel rate' even as individual - billing staff often have discretion",
        "Request the hospital's 'self-pay' or 'cash discount' rate - it's typically 15-25% off",
        "Billing disputes are handled by a separate team - ask to escalate to 'Revenue Recovery' for faster resolution",
        "End of month is the best time to negotiate - hospitals have collection targets to meet",
        "Package deals are negotiable - ask 'What's the best price if I pay today in full?'",
    ],
    
    "private": [
        "Private hospitals typically markup lab tests 2-3x over cost - significant negotiation room",
        "Ask if they price-match with standalone labs like Thyrocare or Dr. Lal",
        "Many private hospitals have tie-ups with insurance TPAs - mention you'll review publicly if not resolved",
        "Request to speak with the 'Admin Manager' rather than billing clerk for better discounts",
    ],
    
    "government": [
        "Government hospital rates are already at CGHS - limited negotiation room",
        "Focus on verifying if all charges are legitimate rather than negotiating price",
        "Check if any charity quota or subsidized category applies to you",
    ],
    
    "diagnostic_lab": [
        "Standalone labs have 40-60% margins - always negotiate, especially for expensive tests",
        "Ask for 'family package' or 'repeat customer' discount",
        "Home collection is often negotiable - ask to waive the fee",
        "Early morning appointments sometimes have promotional rates",
    ],
}


# =============================================================================
# NEGOTIATION STRATEGIES
# =============================================================================

NEGOTIATION_STRATEGIES = {
    "high_success": {
        "description": "High probability of success (70%+)",
        "scenarios": [
            "Bill has clear arithmetic errors",
            "Duplicate charges present",
            "Prices significantly above CGHS rates (>2x)",
            "Hospital is CGHS/NABH empaneled",
        ],
        "approach": "Direct request with documentation",
        "expected_discount": "30-50%",
    },
    
    "medium_success": {
        "description": "Medium probability (40-70%)",
        "scenarios": [
            "Prices moderately above market (1.5-2x)",
            "Corporate hospital with standard pricing",
            "No specific errors but overpriced",
        ],
        "approach": "Polite negotiation with market comparison",
        "expected_discount": "15-30%",
    },
    
    "low_success": {
        "description": "Lower probability (<40%)",
        "scenarios": [
            "Prices within market range",
            "Already discounted package",
            "Emergency services (limited negotiation power)",
        ],
        "approach": "Request itemized bill and payment plan",
        "expected_discount": "5-15%",
    },
}


# =============================================================================
# NEGOTIATION SCRIPTS
# =============================================================================

NEGOTIATION_SCRIPTS = {
    "initial_request": {
        "formal": """Dear Billing Department,

I am writing regarding Bill No. {bill_number} dated {bill_date}.

Upon review, I have identified the following concerns:
{issues}

Comparing with CGHS benchmark rates and market prices from accredited labs (Dr. Lal PathLabs, SRL, Thyrocare), the charges appear to exceed fair market rates by approximately {overcharge_percent}%.

I respectfully request:
1. A detailed itemized breakdown of all charges
2. Review and adjustment of the overcharges mentioned above
3. Application of any applicable discounts

I believe a fair adjustment would be approximately ₹{expected_savings}.

Please respond within 14 business days. I am happy to discuss this further.

Regards,
[YOUR NAME]""",

        "assertive": """Subject: URGENT - Billing Dispute - Bill No. {bill_number}

To Whom It May Concern,

This is a formal dispute regarding excessive charges on Bill No. {bill_number}.

Your charges exceed government CGHS rates by {overcharge_percent}%. This is unacceptable.

Specific issues:
{issues}

I DEMAND:
1. Immediate correction of these overcharges
2. Refund of excess amount paid (if applicable)
3. Written explanation for the pricing discrepancy

If this is not resolved within 10 business days, I will:
- File a complaint with the State Medical Council
- Report to the Consumer Forum
- Share my experience on public review platforms

Expected adjustment: ₹{expected_savings}

[YOUR NAME]
[YOUR CONTACT]""",

        "friendly": """Hi there!

Hope you're doing well. I recently received my bill (No. {bill_number}) and wanted to chat about a few charges that seemed a bit high.

I did some research and noticed:
{issues}

I really appreciated the care I received, but these prices seem higher than what I've seen at other places. Would it be possible to review these and maybe offer a small adjustment?

I'm hoping we can work something out - even a {expected_discount}% reduction would really help!

Thanks so much for looking into this.

Best,
[YOUR NAME]""",
    },
    
    "follow_up": {
        "no_response": """Subject: Follow-up: Billing Dispute - Bill No. {bill_number}

I am following up on my previous communication dated {original_date} regarding billing discrepancies.

I have not received a response yet. Please treat this as urgent.

If I do not hear back within 7 days, I will escalate this matter to:
- Hospital Administrator
- Consumer Grievance Forum
- State Health Department

[YOUR NAME]""",

        "partial_resolution": """Thank you for your response regarding Bill No. {bill_number}.

While I appreciate the {offered_discount}% discount offered, my analysis shows the charges are still {remaining_overcharge}% above fair market rates.

I would like to request a further review, specifically for:
{remaining_issues}

Could we schedule a brief call to discuss this?

[YOUR NAME]""",
    },
    
    "escalation": {
        "admin": """To: Hospital Administrator
Subject: Escalation - Unresolved Billing Dispute

Dear Sir/Madam,

Despite multiple attempts, my billing dispute (Bill No. {bill_number}) remains unresolved.

Issue summary: Charges exceed CGHS/market rates by {overcharge_percent}%
Amount in dispute: ₹{dispute_amount}

I request your personal intervention to resolve this fairly.

[YOUR NAME]""",

        "consumer_forum": """NOTICE BEFORE CONSUMER FORUM COMPLAINT

This serves as a final notice before I file a formal complaint with the Consumer Disputes Redressal Forum.

Bill No: {bill_number}
Disputed Amount: ₹{dispute_amount}
Hospital: {hospital_name}

Violation: Charging prices significantly above government-notified rates (CGHS)

I will file the complaint within 7 days if this is not resolved.

[YOUR NAME]""",
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_insider_tips(hospital_type: str = "corporate", limit: int = 3) -> List[str]:
    """
    Get relevant insider tips based on hospital type.
    
    Args:
        hospital_type: Type of hospital (corporate, private, government, diagnostic_lab)
        limit: Maximum number of tips to return
    
    Returns:
        List of insider tips
    """
    tips = INSIDER_TIPS.get(hospital_type, INSIDER_TIPS["corporate"])
    return tips[:limit]


def get_negotiation_script(
    tone: str,
    script_type: str,
    bill_number: str = "",
    bill_date: str = "",
    issues: str = "",
    overcharge_percent: float = 0,
    expected_savings: float = 0,
    expected_discount: str = "20",
    **kwargs
) -> str:
    """
    Get a negotiation script with filled-in values.
    
    Args:
        tone: formal, assertive, or friendly
        script_type: initial_request, follow_up, escalation
        Various bill details to fill in
    
    Returns:
        Formatted script string
    """
    scripts = NEGOTIATION_SCRIPTS.get(script_type, {})
    template = scripts.get(tone, scripts.get("formal", ""))
    
    if not template:
        return ""
    
    return template.format(
        bill_number=bill_number,
        bill_date=bill_date,
        issues=issues,
        overcharge_percent=overcharge_percent,
        expected_savings=expected_savings,
        expected_discount=expected_discount,
        **kwargs
    )


def get_success_probability(issues: List[Dict]) -> str:
    """
    Estimate negotiation success probability based on issues found.
    
    Args:
        issues: List of audit issues
    
    Returns:
        "high", "medium", or "low"
    """
    if not issues:
        return "low"
    
    # High success indicators
    critical_count = sum(1 for i in issues if i.get("severity") == "critical")
    has_arithmetic = any(i.get("type") == "ARITHMETIC" for i in issues)
    has_duplicate = any(i.get("type") == "DUPLICATE" for i in issues)
    
    if critical_count >= 2 or has_arithmetic or has_duplicate:
        return "high"
    
    high_count = sum(1 for i in issues if i.get("severity") == "high")
    if high_count >= 2 or critical_count >= 1:
        return "medium"
    
    return "low"


def get_escalation_path(hospital_type: str = "corporate") -> str:
    """
    Get the recommended escalation path for a hospital type.
    """
    paths = {
        "corporate": "Billing Dept → Admin Manager → Hospital Administrator → Consumer Forum",
        "private": "Billing Dept → Owner/Director → State Medical Council → Consumer Forum",
        "government": "Billing Dept → Medical Superintendent → CMO Office → RTI/Grievance Portal",
        "diagnostic_lab": "Customer Care → Branch Manager → Regional Head → Consumer Forum",
    }
    return paths.get(hospital_type, paths["corporate"])

