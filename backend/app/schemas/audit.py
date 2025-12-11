"""
Audit Response Schemas

Pydantic models for audit API responses.
Modular and easy to extend.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


# =============================================================================
# ISSUE SCHEMAS
# =============================================================================

class AuditIssue(BaseModel):
    """Individual billing issue found during audit."""
    type: str = Field(..., description="OVERCHARGE|DUPLICATE|ARITHMETIC|UPCODING|UNBUNDLING")
    severity: str = Field(..., description="critical|high|medium|low")
    description: str = Field(..., description="Detailed description of the issue")
    amount_impact: Optional[float] = Field(None, description="Financial impact in local currency")
    fair_price: Optional[float] = Field(None, description="What the item should cost")
    recommendation: Optional[str] = Field(None, description="Suggested action")


# =============================================================================
# MARKET COMPARISON SCHEMAS
# =============================================================================

class CompetitorPrice(BaseModel):
    """Price from a competitor for comparison."""
    name: str = Field(..., description="Competitor name (e.g., 'Dr. Lal PathLabs')")
    price: float = Field(..., description="Competitor price")
    test: Optional[str] = Field(None, description="Test name")


class MarketComparison(BaseModel):
    """Market analysis and competitor comparison."""
    hospital_type: Optional[str] = Field(None, description="Corporate/Private/Government")
    price_tier: Optional[str] = Field(None, description="Premium/Standard/Budget")
    competitor_prices: Optional[List[CompetitorPrice]] = Field(
        None, description="Prices from competing providers"
    )
    cghs_rate: Optional[float] = Field(None, description="CGHS government benchmark rate")
    market_average: Optional[float] = Field(None, description="Typical market price")


# =============================================================================
# NEGOTIATION STRATEGY SCHEMAS
# =============================================================================

class NegotiationStrategy(BaseModel):
    """AI-generated negotiation strategy and scripts."""
    success_probability: Optional[str] = Field(None, description="high|medium|low")
    expected_discount: Optional[str] = Field(None, description="Expected discount range (e.g., '15-25%')")
    best_approach: Optional[str] = Field(None, description="Recommended approach")
    scripts: Optional[List[str]] = Field(None, description="Ready-to-use negotiation phrases")
    escalation_path: Optional[str] = Field(None, description="Who to contact if initial attempt fails")
    timing: Optional[str] = Field(None, description="Best time to negotiate")


# =============================================================================
# MAIN AUDIT RESULT SCHEMA
# =============================================================================

# =============================================================================
# DOCUMENT SCAN & TRANSPARENCY SCHEMAS
# =============================================================================

class ScanSummary(BaseModel):
    """Summary of OCR scan results."""
    text_length: int = Field(0, description="Characters extracted")
    lines_detected: int = Field(0, description="Lines detected")
    ocr_confidence: str = Field("medium", description="OCR confidence level")


class ExtractedLineItem(BaseModel):
    """Line item extracted from bill."""
    description: str
    category: Optional[str] = None
    quantity: float = 1.0
    amount: float = 0
    cghs_rate: Optional[float] = Field(None, description="CGHS benchmark rate")
    market_rate: Optional[float] = Field(None, description="Market average rate")
    overcharge_amount: Optional[float] = Field(None, description="Amount overcharged")
    overcharge_percent: Optional[float] = Field(None, description="% over fair price")


class CategoryBreakdown(BaseModel):
    """Breakdown by category."""
    category: str
    amount: float
    percent_of_total: float
    cghs_benchmark: Optional[float] = None
    status: str = Field("normal", description="normal|overcharged|fair")


class KeyMetrics(BaseModel):
    """Key financial metrics dashboard."""
    total_bill: float = 0
    cghs_equivalent: Optional[float] = Field(None, description="What CGHS would pay")
    market_average: Optional[float] = Field(None, description="Market average for this")
    overcharge_amount: float = 0
    overcharge_percent: float = 0
    largest_category: Optional[str] = None
    largest_category_amount: float = 0
    tax_amount: float = 0
    payments_made: float = 0
    outstanding: float = 0


class DocumentBreakdown(BaseModel):
    """Complete transparency on what was scanned and extracted."""
    scan_summary: Optional[ScanSummary] = None
    hospital_name: Optional[str] = None
    hospital_type: Optional[str] = None
    bill_number: Optional[str] = None
    bill_date: Optional[str] = None
    patient_name: Optional[str] = None
    line_items: Optional[List[ExtractedLineItem]] = None
    categories: Optional[List[CategoryBreakdown]] = None
    key_metrics: Optional[KeyMetrics] = None
    raw_text_preview: Optional[str] = Field(None, description="First 500 chars of OCR")


class InsiderAnalysis(BaseModel):
    """Insider-level analysis and negotiation intelligence."""
    hospital_profit_margin: Optional[str] = Field(None, description="Estimated margin on this bill")
    negotiation_window: Optional[str] = Field(None, description="How much room to negotiate")
    decision_maker: Optional[str] = Field(None, description="Who can approve discounts")
    best_time_to_call: Optional[str] = Field(None, description="When billing dept is most flexible")
    leverage_points: Optional[List[str]] = Field(None, description="What gives you negotiating power")
    red_flags: Optional[List[str]] = Field(None, description="Suspicious items to question")
    priority_items: Optional[List[str]] = Field(None, description="Negotiate these first")


class AuditResult(BaseModel):
    """
    Complete audit result with analysis, market comparison, and strategies.
    
    This is the main response schema for the /audit/{document_id} endpoint.
    """
    # Basic info
    document_id: Optional[int] = None
    
    # Audit scores
    score: int = Field(..., ge=0, le=100, description="Overall bill health score (0-100)")
    total_issues: int = Field(0, description="Total number of issues found")
    critical_count: int = Field(0, description="Number of critical issues")
    high_count: int = Field(0, description="Number of high severity issues")
    medium_count: int = Field(0, description="Number of medium severity issues")
    low_count: int = Field(0, description="Number of low severity issues")
    
    # Financial
    potential_savings: float = Field(0, description="Estimated potential savings")
    currency: str = Field("₹", description="Currency symbol")
    region: str = Field("IN", description="Region code (IN/US)")
    
    # Detailed analysis
    issues: List[AuditIssue] = Field(default_factory=list, description="List of issues found")
    
    # Market intelligence
    market_comparison: Optional[MarketComparison] = Field(
        None, description="Market analysis and competitor prices"
    )
    
    # Insider tips
    insider_tips: Optional[List[str]] = Field(
        None, description="Industry insider tips for negotiation"
    )
    
    # Negotiation guidance
    negotiation_strategy: Optional[NegotiationStrategy] = Field(
        None, description="AI-generated negotiation strategy"
    )
    
    # Complete transparency - Document breakdown
    document_breakdown: Optional[DocumentBreakdown] = Field(
        None, description="Complete breakdown of scanned document"
    )
    
    # Insider analysis
    insider_analysis: Optional[InsiderAnalysis] = Field(
        None, description="Insider-level analysis for negotiation"
    )
    
    # Summary
    summary: Optional[str] = Field(None, description="Brief overall assessment")
    
    # Metadata
    ocr_used: bool = Field(False, description="Whether OCR was used to extract text")
    ai_provider: str = Field("none", description="AI provider used (groq/ollama/mock)")
    error_message: Optional[str] = Field(None, description="Error message if analysis failed")
    
    # Disclaimer (always included)
    disclaimer: str = Field(
        default="⚠️ AI-GENERATED ANALYSIS: This report is generated by artificial intelligence. "
        "Prices are estimates based on publicly available data including CGHS rates, PMJAY packages, "
        "and market research. Always verify with official sources before negotiating. "
        "This is not legal or medical advice.",
        description="AI disclaimer"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": 10,
                "score": 60,
                "total_issues": 5,
                "critical_count": 1,
                "high_count": 2,
                "medium_count": 1,
                "low_count": 1,
                "potential_savings": 3466.5,
                "currency": "₹",
                "region": "IN",
                "issues": [
                    {
                        "type": "OVERCHARGE",
                        "severity": "critical",
                        "description": "Renal Function Test charged ₹990, CGHS rate is ₹250",
                        "amount_impact": 740,
                        "fair_price": 250,
                        "recommendation": "Request price adjustment to CGHS rate"
                    }
                ],
                "insider_tips": [
                    "Corporate hospitals have 25-40% margin on diagnostics",
                    "Ask for 'cash discount' - typically 15-25% off"
                ],
                "summary": "Bill shows significant overcharges compared to government rates.",
                "ai_provider": "groq",
                "ocr_used": True,
            }
        }


# =============================================================================
# REQUEST SCHEMAS
# =============================================================================

class AnalyzeBillRequest(BaseModel):
    """Request to analyze bill text directly."""
    bill_text: str = Field(..., min_length=10, description="Raw bill text to analyze")
    region: str = Field("IN", description="Region code (IN/US)")


class GenerateLetterRequest(BaseModel):
    """Request to generate a negotiation letter."""
    document_id: int = Field(..., description="Document ID to generate letter for")
    tone: str = Field("formal", description="Letter tone: formal|friendly|assertive")

