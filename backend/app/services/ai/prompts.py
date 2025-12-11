"""
AI Prompt Templates

All prompts for different AI tasks. Easy to update and version.
"""

# System prompts for different AI roles
SYSTEM_PROMPTS = {
    "auditor": """You are an expert medical bill auditor with insider knowledge of hospital billing.
You MUST ALWAYS respond with valid JSON only. Never include text before or after JSON.

Your expertise:
- Indian Healthcare: CGHS rates, PMJAY packages, NABH standards, hospital profit margins
- US Healthcare: Medicare rates, CPT/HCPCS codes, insurance negotiations
- Industry insider knowledge: How hospitals price, markup strategies, negotiation windows

Provide advice like a trusted friend who works in hospital administration.""",

    "negotiator": """You are an expert medical bill negotiator who has helped thousands of patients.
Write compelling, personalized letters that get results.
Include specific amounts, reference fair pricing, and cite patient rights.""",

    "analyzer": """You are a medical bill analyzer. Extract and structure information accurately.
Identify line items, charges, codes, dates, and totals. Flag suspicious charges.""",
    
    "assistant": """You are a helpful healthcare billing assistant.
Answer questions about medical bills clearly and empathetically.
Provide actionable advice while being respectful of patient concerns.""",
}


def get_audit_prompt(bill_json: str, region: str, pricing_context: str) -> str:
    """
    Generate the audit analysis prompt.
    
    Args:
        bill_json: JSON string of bill data
        region: "IN" or "US"
        pricing_context: Pricing reference data
    
    Returns:
        Complete prompt for AI analysis
    """
    currency = "₹" if region == "IN" else "$"
    
    return f"""Analyze this medical bill like an INSIDER who works in the hospital industry.
You MUST respond with ONLY valid JSON, no other text.

{pricing_context}

BILL DATA:
{bill_json[:2500]}

RESPOND WITH ONLY THIS JSON (include insider tips, market comparisons, negotiation scripts):
{{
    "score": <0-100>,
    "total_issues": <count>,
    "critical_count": <count>,
    "high_count": <count>,
    "medium_count": <count>,
    "low_count": <count>,
    "potential_savings": <amount>,
    "currency": "{currency}",
    "region": "{region}",
    "issues": [
        {{
            "type": "OVERCHARGE|DUPLICATE|ARITHMETIC|UPCODING|UNBUNDLING",
            "severity": "critical|high|medium|low",
            "description": "specific issue with amounts",
            "amount_impact": <number>,
            "fair_price": <what it should cost>,
            "recommendation": "specific action"
        }}
    ],
    "market_comparison": {{
        "hospital_type": "Corporate/Private/Government",
        "price_tier": "Premium/Standard/Budget",
        "competitor_prices": [
            {{"name": "Dr. Lal PathLabs", "price": <amount>, "test": "test name"}},
            {{"name": "SRL Diagnostics", "price": <amount>, "test": "test name"}},
            {{"name": "Thyrocare", "price": <amount>, "test": "test name"}}
        ],
        "cghs_rate": <government benchmark>,
        "market_average": <typical market price>
    }},
    "insider_tips": [
        "Tip about how hospitals work internally",
        "What billing staff can actually do", 
        "Best time/approach to negotiate"
    ],
    "negotiation_strategy": {{
        "success_probability": "high|medium|low",
        "expected_discount": "10-30%",
        "best_approach": "What to say and do",
        "scripts": [
            "Exact phrase to use with billing department",
            "Follow-up if initial request denied"
        ],
        "escalation_path": "Who to contact if billing refuses",
        "timing": "Best time to negotiate"
    }},
    "summary": "2-3 sentence assessment with savings potential",
    "disclaimer": "AI-generated analysis. Verify rates independently."
}}"""


def get_negotiation_prompt(bill_summary: str, issues: list, savings: float, 
                           currency: str, tone: str, region: str = "IN") -> str:
    """
    Generate the negotiation letter prompt with structured table format.
    
    Args:
        bill_summary: Summary of the bill
        issues: List of identified issues
        savings: Potential savings amount
        currency: Currency symbol
        tone: Letter tone (formal/friendly/assertive)
        region: "IN" or "US"
    
    Returns:
        Complete prompt for letter generation
    """
    issues_text = "\n".join([f"- {issue}" for issue in issues[:8]]) if issues else "Overcharges detected"
    
    tone_instructions = {
        "formal": "Professional, business-like. Reference regulations and patient rights.",
        "friendly": "Warm but firm. Express appreciation while requesting adjustment.",
        "assertive": "Direct and confident. Clearly state expectations and deadlines.",
    }
    
    if region == "IN":
        regulatory_context = """
REGULATORY REFERENCES (India):
- CGHS (Central Government Health Scheme) rates
- PMJAY (Ayushman Bharat) package rates  
- Clinical Establishments Act, 2010
- Consumer Protection Act, 2019
- Right to transparent billing under NABH guidelines"""
    else:
        regulatory_context = """
REGULATORY REFERENCES (US):
- Medicare Fee Schedule rates
- No Surprises Act protections
- Hospital Price Transparency Rule
- State patient billing rights laws"""

    return f"""Generate a professional medical bill dispute letter with STRUCTURED TABLES.

BILL DETAILS:
{bill_summary}

ISSUES IDENTIFIED:
{issues_text}

POTENTIAL SAVINGS: {currency}{savings:,.0f}

TONE: {tone_instructions.get(tone, tone_instructions['formal'])}

{regulatory_context}

=== REQUIRED LETTER FORMAT ===

1. HEADER: Date, Patient/Reference details, Hospital address

2. SUBJECT LINE: Bill Dispute - [Bill Number] - Request for Review

3. OPENING PARAGRAPH: State purpose clearly and professionally

4. **DISPUTE SUMMARY TABLE** (Use ASCII table format):
┌─────────────────────────────────────────────────────────────────────────────────┐
│ S.No │ Charge Description      │ Billed Amount │ Fair Rate │ Difference │ Reason│
├──────┼─────────────────────────┼───────────────┼───────────┼────────────┼───────┤
│ 1    │ [Item from bill]        │ {currency}XXX │ {currency}XXX │ {currency}XXX │ [Why disputed] │
│ 2    │ [Next item]             │ {currency}XXX │ {currency}XXX │ {currency}XXX │ [Reason]       │
└─────────────────────────────────────────────────────────────────────────────────┘

5. **DETAILED ANALYSIS SECTION** - For each disputed item explain:
   - Why the charge is excessive (compared to benchmark rates)
   - Supporting evidence (CGHS rates, market averages, competitor prices)
   - Recommended fair price

6. **SUMMARY BOX**:
┌────────────────────────────────────────┐
│ TOTAL BILLED:        {currency}XXXX   │
│ FAIR VALUE:          {currency}XXXX   │
│ REQUESTED ADJUSTMENT: {currency}XXXX  │
└────────────────────────────────────────┘

7. **REQUEST SECTION**: Specific actions requested with timeline

8. **ESCALATION NOTICE**: What happens if not resolved (regulatory bodies, consumer court)

9. CLOSING with contact details placeholder

=== IMPORTANT ===
- Use actual amounts from the bill in tables
- Be specific with numbers, not vague
- Include at least 3-5 line items in the dispute table
- Reference specific regulatory benchmarks
- Make tables easy to read with proper formatting

Generate the complete letter now:"""


def get_fair_price_prompt(procedure: str, region: str) -> str:
    """
    Generate prompt for fair price lookup.
    """
    if region == "IN":
        context = """Reference rates:
- CGHS (Central Government Health Scheme) rates
- PMJAY package rates
- Average rates from Dr. Lal PathLabs, SRL, Thyrocare
- Typical private hospital markup: 2-4x government rates"""
    else:
        context = """Reference rates:
- Medicare Fee Schedule
- Fair Health consumer database
- Healthcare Bluebook estimates"""
    
    return f"""What is the fair price for: {procedure}

{context}

Return JSON only:
{{
    "procedure": "{procedure}",
    "fair_price_low": <minimum fair price>,
    "fair_price_high": <maximum fair price>,
    "fair_price_median": <typical price>,
    "cghs_rate": <government rate if applicable>,
    "source": "reference source"
}}"""

