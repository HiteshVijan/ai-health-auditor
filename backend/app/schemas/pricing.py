"""
Pricing API Schemas.

Pydantic models for pricing lookup, hospital scoring, and price contribution APIs.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


# ============================================
# Enums
# ============================================

class HospitalTypeEnum(str, Enum):
    GOVERNMENT = "government"
    CGHS_EMPANELED = "cghs_empaneled"
    PRIVATE = "private"
    CORPORATE = "corporate"
    NABH_ACCREDITED = "nabh_accredited"
    TRUST = "trust"
    UNKNOWN = "unknown"


class CityTierEnum(str, Enum):
    METRO = "metro"
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"
    UNKNOWN = "unknown"


class PriceSourceEnum(str, Enum):
    CGHS = "cghs"
    PMJAY = "pmjay"
    USER_BILL = "user_bill"
    HOSPITAL_WEBSITE = "hospital_website"
    INSURANCE_CLAIM = "insurance_claim"
    SURVEY = "survey"
    SCRAPED = "scraped"
    MANUAL = "manual"


# ============================================
# Pricing Lookup Schemas
# ============================================

class PriceLookupRequest(BaseModel):
    """Request for price lookup."""
    procedure: str = Field(..., min_length=2, description="Procedure name to look up")
    city: Optional[str] = Field(None, description="City name for location-based pricing")
    hospital_name: Optional[str] = Field(None, description="Specific hospital name")
    hospital_type: Optional[HospitalTypeEnum] = Field(None, description="Type of hospital")


class PriceRange(BaseModel):
    """Price range with source attribution."""
    low: float = Field(..., description="Low end of price range (CGHS/PMJAY rate)")
    median: float = Field(..., description="Median market price")
    high: float = Field(..., description="High end (corporate hospital max)")
    p25: Optional[float] = Field(None, description="25th percentile")
    p75: Optional[float] = Field(None, description="75th percentile")
    currency: str = Field("INR", description="Currency code")


class BenchmarkPrice(BaseModel):
    """Official benchmark price."""
    source: str = Field(..., description="Source of benchmark (CGHS, PMJAY)")
    rate: float = Field(..., description="Official rate")
    description: Optional[str] = None
    effective_date: Optional[str] = None


class MarketPrice(BaseModel):
    """Aggregated market price from crowdsourced data."""
    hospital_type: HospitalTypeEnum
    city_tier: CityTierEnum
    price_range: PriceRange
    sample_size: int = Field(..., description="Number of price points")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in the data")
    last_updated: Optional[datetime] = None


class PriceLookupResponse(BaseModel):
    """Response for price lookup API."""
    procedure_name: str
    matched_procedure: str
    match_confidence: float = Field(..., ge=0, le=1)
    category: str
    
    # Benchmark prices
    benchmarks: List[BenchmarkPrice]
    
    # Market prices by context
    market_prices: List[MarketPrice]
    
    # Quick reference
    fair_price_range: PriceRange
    
    # Metadata
    data_points: int = Field(..., description="Total price observations")
    last_updated: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "procedure_name": "knee replacement",
                "matched_procedure": "Total Knee Replacement (one knee)",
                "match_confidence": 0.95,
                "category": "orthopedics",
                "benchmarks": [
                    {"source": "CGHS", "rate": 150000, "description": "Government rate"},
                    {"source": "PMJAY", "rate": 80000, "description": "Ayushman Bharat package"}
                ],
                "market_prices": [
                    {
                        "hospital_type": "private",
                        "city_tier": "metro",
                        "price_range": {"low": 180000, "median": 250000, "high": 400000, "currency": "INR"},
                        "sample_size": 47,
                        "confidence": 0.85
                    }
                ],
                "fair_price_range": {"low": 80000, "median": 180000, "high": 350000, "currency": "INR"},
                "data_points": 156,
                "last_updated": "2024-12-01T00:00:00Z"
            }
        }


class ProcedureSearchResult(BaseModel):
    """Single procedure in search results."""
    id: int
    name: str
    category: str
    subcategory: Optional[str] = None
    cghs_rate: Optional[float] = None
    pmjay_rate: Optional[float] = None
    market_median: Optional[float] = None
    price_point_count: int = 0
    match_score: Optional[float] = None


class ProcedureSearchResponse(BaseModel):
    """Response for procedure search."""
    query: str
    results: List[ProcedureSearchResult]
    total_count: int


# ============================================
# Hospital Schemas
# ============================================

class HospitalBase(BaseModel):
    """Base hospital schema."""
    name: str
    city: str
    state: str
    hospital_type: HospitalTypeEnum = HospitalTypeEnum.PRIVATE
    city_tier: CityTierEnum = CityTierEnum.TIER_2


class HospitalCreate(HospitalBase):
    """Schema for creating a hospital."""
    pincode: Optional[str] = None
    address: Optional[str] = None
    is_cghs_empaneled: bool = False
    is_nabh_accredited: bool = False
    is_pmjay_empaneled: bool = False
    gstin: Optional[str] = None
    website: Optional[str] = None


class HospitalScore(BaseModel):
    """Hospital scoring breakdown."""
    pricing_score: float = Field(..., ge=0, le=100, description="Lower prices = higher score")
    transparency_score: float = Field(..., ge=0, le=100, description="Consistent pricing = higher score")
    overall_score: float = Field(..., ge=0, le=100, description="Weighted overall score")
    
    # Comparison
    city_rank: Optional[int] = Field(None, description="Rank among hospitals in same city")
    city_total: Optional[int] = Field(None, description="Total hospitals in city")
    
    # Trend
    score_trend: Optional[str] = Field(None, description="improving/stable/declining")


class HospitalRead(HospitalBase):
    """Schema for reading hospital data."""
    id: int
    normalized_name: str
    
    # Accreditations
    is_cghs_empaneled: bool
    is_nabh_accredited: bool
    is_pmjay_empaneled: bool
    
    # Scores
    scores: HospitalScore
    
    # Statistics
    total_bills_analyzed: int
    total_procedures_priced: int
    avg_overcharge_percent: float
    
    # Metadata
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class HospitalCompare(BaseModel):
    """Schema for hospital comparison."""
    hospital: HospitalRead
    procedure_prices: List[dict]  # Procedure name -> price for this hospital
    vs_cghs_avg: float  # % difference from CGHS
    vs_market_avg: float  # % difference from market average


class HospitalSearchRequest(BaseModel):
    """Request for hospital search."""
    query: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    hospital_type: Optional[HospitalTypeEnum] = None
    min_score: Optional[float] = Field(None, ge=0, le=100)
    is_cghs_empaneled: Optional[bool] = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class HospitalSearchResponse(BaseModel):
    """Response for hospital search."""
    hospitals: List[HospitalRead]
    total_count: int
    filters_applied: dict


# ============================================
# Price Contribution Schemas
# ============================================

class PriceContributionCreate(BaseModel):
    """Schema for submitting a price contribution."""
    procedure_name: str = Field(..., min_length=2)
    charged_amount: float = Field(..., gt=0)
    
    # Hospital info
    hospital_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    hospital_type: Optional[HospitalTypeEnum] = None
    
    # Context
    observation_date: Optional[datetime] = None
    source_document_id: Optional[int] = None
    
    # Optional: bill image was already verified
    is_verified: bool = False


class PriceContributionResponse(BaseModel):
    """Response after submitting price contribution."""
    success: bool
    price_point_id: Optional[int] = None
    procedure_matched: Optional[str] = None
    hospital_matched: Optional[str] = None
    
    # Feedback
    comparison: Optional[dict] = None  # How this compares to existing data
    points_earned: int = 0
    message: str


class BulkPriceContribution(BaseModel):
    """Schema for bulk price contributions (from processed bills)."""
    document_id: int
    contributions: List[PriceContributionCreate]


class BulkContributionResponse(BaseModel):
    """Response for bulk contribution."""
    success: bool
    total_submitted: int
    successful: int
    failed: int
    errors: List[str] = []
    total_points_earned: int = 0


# ============================================
# Analytics Schemas (B2B)
# ============================================

class PricingStatsRequest(BaseModel):
    """Request for pricing statistics."""
    procedure: Optional[str] = None
    category: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    hospital_type: Optional[HospitalTypeEnum] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class PricingStats(BaseModel):
    """Aggregated pricing statistics."""
    total_price_points: int
    total_hospitals: int
    total_procedures: int
    
    # Price distribution
    price_mean: float
    price_median: float
    price_std: float
    price_min: float
    price_max: float
    
    # Comparison to benchmarks
    avg_vs_cghs: float  # Average % above CGHS
    avg_vs_pmjay: float  # Average % above PMJAY
    
    # Time trends
    price_trend_30d: Optional[float] = None  # % change last 30 days
    price_trend_90d: Optional[float] = None  # % change last 90 days


class CategoryPricing(BaseModel):
    """Pricing by category."""
    category: str
    procedure_count: int
    avg_cghs_rate: Optional[float]
    avg_market_price: Optional[float]
    avg_overcharge_percent: float
    most_overcharged_procedures: List[dict]


class CityPricing(BaseModel):
    """Pricing by city."""
    city: str
    state: str
    city_tier: CityTierEnum
    hospital_count: int
    avg_pricing_score: float
    most_expensive_hospitals: List[dict]
    most_affordable_hospitals: List[dict]


class PricingAnalytics(BaseModel):
    """Complete pricing analytics response."""
    stats: PricingStats
    by_category: List[CategoryPricing]
    by_city: List[CityPricing]
    top_overcharged_procedures: List[dict]
    price_heatmap_data: Optional[dict] = None  # For visualization
    generated_at: datetime


# ============================================
# Database Stats
# ============================================

class DatabaseStats(BaseModel):
    """Statistics about the pricing database."""
    total_price_points: int
    total_hospitals: int
    total_procedures: int
    
    # By source
    cghs_procedures: int
    pmjay_packages: int
    crowdsourced_points: int
    
    # Coverage
    cities_covered: int
    states_covered: int
    
    # Recency
    latest_contribution: Optional[datetime] = None
    contributions_last_7_days: int = 0
    contributions_last_30_days: int = 0
    
    # Quality
    verified_percentage: float = 0.0

