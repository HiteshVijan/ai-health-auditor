"""
Hospital Dashboard API Endpoints.

B2B feature allowing hospitals to:
- View their pricing vs competitors
- See their hospital score and ranking
- Get insights on pricing optimization
- Track trends over time
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.db.session import get_db
from app.api.deps import get_current_user_id
from app.models.user import User, UserRole
from app.models.pricing import (
    Hospital, Procedure, PricePoint, HospitalScore,
    HospitalType, CityTier, PriceSource
)
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# Schemas
# ============================================

class ProcedurePricing(BaseModel):
    """Pricing for a single procedure."""
    procedure_id: int
    procedure_name: str
    category: str
    your_price: Optional[float] = None
    market_average: Optional[float] = None
    market_low: Optional[float] = None
    market_high: Optional[float] = None
    cghs_rate: Optional[float] = None
    pmjay_rate: Optional[float] = None
    vs_market_percent: Optional[float] = None  # +10 means 10% above market
    vs_cghs_percent: Optional[float] = None
    sample_count: int = 0
    status: str = "competitive"  # competitive, overpriced, underpriced


class CompetitorSummary(BaseModel):
    """Anonymized competitor data."""
    hospital_type: str
    city_tier: str
    avg_price: float
    sample_count: int


class HospitalDashboardStats(BaseModel):
    """Overall dashboard statistics."""
    hospital_id: int
    hospital_name: str
    city: str
    hospital_type: str
    
    # Scores
    overall_score: float
    pricing_score: float
    transparency_score: float
    
    # Rankings
    city_rank: Optional[int] = None
    city_total: Optional[int] = None
    state_rank: Optional[int] = None
    state_total: Optional[int] = None
    national_rank: Optional[int] = None
    national_total: Optional[int] = None
    
    # Statistics
    total_procedures_priced: int = 0
    total_bills_analyzed: int = 0
    avg_overcharge_percent: float = 0.0
    
    # Trends
    score_change_30d: Optional[float] = None
    bills_last_30d: int = 0


class PricingComparison(BaseModel):
    """Pricing comparison result."""
    procedures: List[ProcedurePricing]
    summary: dict
    recommendations: List[str]


class CompetitorAnalysis(BaseModel):
    """Competitor analysis results."""
    your_hospital: str
    competitors: List[CompetitorSummary]
    your_position: str  # "above_average", "competitive", "below_average"
    insights: List[str]


class HospitalClaimRequest(BaseModel):
    """Request to claim a hospital."""
    hospital_id: int
    verification_type: str = "email"  # email, document, phone
    contact_email: str
    contact_phone: Optional[str] = None
    designation: str  # e.g., "Admin", "Billing Manager"
    notes: Optional[str] = None


class HospitalClaimResponse(BaseModel):
    """Response for hospital claim."""
    claim_id: int
    status: str  # pending, approved, rejected
    message: str


# ============================================
# Helper Functions
# ============================================

def get_hospital_admin(db: Session, user_id: int) -> tuple[User, Hospital]:
    """Get user and verify they are a hospital admin."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # For demo purposes, if not hospital admin, check if admin
    if user.role == UserRole.ADMIN:
        # Admins can view any hospital - use query param
        return user, None
    
    if user.role != UserRole.HOSPITAL_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Hospital dashboard requires hospital admin access"
        )
    
    if not user.hospital_id:
        raise HTTPException(
            status_code=403,
            detail="No hospital linked to your account. Please claim your hospital first."
        )
    
    hospital = db.query(Hospital).filter(Hospital.id == user.hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    
    return user, hospital


def calculate_hospital_rankings(db: Session, hospital: Hospital) -> dict:
    """Calculate hospital rankings at different levels."""
    rankings = {}
    
    # City ranking
    city_hospitals = db.query(Hospital).filter(
        Hospital.city == hospital.city,
        Hospital.overall_score > 0
    ).order_by(Hospital.overall_score.desc()).all()
    
    if city_hospitals:
        rankings["city_rank"] = next(
            (i + 1 for i, h in enumerate(city_hospitals) if h.id == hospital.id), 
            None
        )
        rankings["city_total"] = len(city_hospitals)
    
    # State ranking
    state_hospitals = db.query(Hospital).filter(
        Hospital.state == hospital.state,
        Hospital.overall_score > 0
    ).order_by(Hospital.overall_score.desc()).all()
    
    if state_hospitals:
        rankings["state_rank"] = next(
            (i + 1 for i, h in enumerate(state_hospitals) if h.id == hospital.id),
            None
        )
        rankings["state_total"] = len(state_hospitals)
    
    # National ranking
    national_hospitals = db.query(Hospital).filter(
        Hospital.overall_score > 0
    ).order_by(Hospital.overall_score.desc()).all()
    
    if national_hospitals:
        rankings["national_rank"] = next(
            (i + 1 for i, h in enumerate(national_hospitals) if h.id == hospital.id),
            None
        )
        rankings["national_total"] = len(national_hospitals)
    
    return rankings


# ============================================
# Endpoints
# ============================================

@router.get("/stats", response_model=HospitalDashboardStats)
async def get_dashboard_stats(
    hospital_id: Optional[int] = Query(None, description="Hospital ID (admin only)"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Get hospital dashboard statistics.
    
    Shows overall scores, rankings, and key metrics.
    """
    user, hospital = get_hospital_admin(db, user_id)
    
    # If admin viewing specific hospital
    if hospital is None and hospital_id:
        hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")
    elif hospital is None:
        raise HTTPException(status_code=400, detail="Hospital ID required for admin users")
    
    # Calculate rankings
    rankings = calculate_hospital_rankings(db, hospital)
    
    # Get 30-day stats
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    bills_last_30d = db.query(func.count(PricePoint.id)).filter(
        PricePoint.hospital_id == hospital.id,
        PricePoint.created_at >= thirty_days_ago
    ).scalar() or 0
    
    # Calculate score change
    recent_score = db.query(HospitalScore).filter(
        HospitalScore.hospital_id == hospital.id
    ).order_by(HospitalScore.period_end.desc()).first()
    
    older_score = db.query(HospitalScore).filter(
        HospitalScore.hospital_id == hospital.id,
        HospitalScore.period_end < thirty_days_ago
    ).order_by(HospitalScore.period_end.desc()).first()
    
    score_change = None
    if recent_score and older_score:
        score_change = recent_score.overall_score - older_score.overall_score
    
    return HospitalDashboardStats(
        hospital_id=hospital.id,
        hospital_name=hospital.name,
        city=hospital.city,
        hospital_type=hospital.hospital_type.value if hospital.hospital_type else "unknown",
        overall_score=hospital.overall_score or 50.0,
        pricing_score=hospital.pricing_score or 50.0,
        transparency_score=hospital.transparency_score or 50.0,
        city_rank=rankings.get("city_rank"),
        city_total=rankings.get("city_total"),
        state_rank=rankings.get("state_rank"),
        state_total=rankings.get("state_total"),
        national_rank=rankings.get("national_rank"),
        national_total=rankings.get("national_total"),
        total_procedures_priced=hospital.total_procedures_priced or 0,
        total_bills_analyzed=hospital.total_bills_analyzed or 0,
        avg_overcharge_percent=hospital.avg_overcharge_percent or 0.0,
        score_change_30d=score_change,
        bills_last_30d=bills_last_30d,
    )


@router.get("/pricing", response_model=PricingComparison)
async def get_pricing_comparison(
    hospital_id: Optional[int] = Query(None, description="Hospital ID (admin only)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Get pricing comparison for your hospital vs market.
    
    Shows how your prices compare to:
    - Market average
    - CGHS rates
    - PMJAY rates
    """
    user, hospital = get_hospital_admin(db, user_id)
    
    if hospital is None and hospital_id:
        hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")
    elif hospital is None:
        raise HTTPException(status_code=400, detail="Hospital ID required")
    
    # Get procedures with pricing data for this hospital
    query = db.query(
        Procedure.id,
        Procedure.name,
        Procedure.category,
        Procedure.cghs_rate,
        Procedure.pmjay_package_rate,
        Procedure.market_median,
        Procedure.market_low,
        Procedure.market_high,
        func.avg(PricePoint.charged_amount).label("your_avg_price"),
        func.count(PricePoint.id).label("your_sample_count"),
    ).join(
        PricePoint, PricePoint.procedure_id == Procedure.id
    ).filter(
        PricePoint.hospital_id == hospital.id
    )
    
    if category:
        query = query.filter(Procedure.category == category)
    
    results = query.group_by(Procedure.id).limit(limit).all()
    
    procedures = []
    overpriced_count = 0
    underpriced_count = 0
    competitive_count = 0
    
    for r in results:
        your_price = r.your_avg_price
        market_avg = r.market_median or r.cghs_rate
        
        # Calculate comparison percentages
        vs_market = None
        vs_cghs = None
        status = "competitive"
        
        if your_price and market_avg and market_avg > 0:
            vs_market = ((your_price - market_avg) / market_avg) * 100
            if vs_market > 20:
                status = "overpriced"
                overpriced_count += 1
            elif vs_market < -20:
                status = "underpriced"
                underpriced_count += 1
            else:
                competitive_count += 1
        
        if your_price and r.cghs_rate and r.cghs_rate > 0:
            vs_cghs = ((your_price - r.cghs_rate) / r.cghs_rate) * 100
        
        procedures.append(ProcedurePricing(
            procedure_id=r.id,
            procedure_name=r.name,
            category=r.category or "unknown",
            your_price=your_price,
            market_average=r.market_median,
            market_low=r.market_low,
            market_high=r.market_high,
            cghs_rate=r.cghs_rate,
            pmjay_rate=r.pmjay_package_rate,
            vs_market_percent=round(vs_market, 1) if vs_market else None,
            vs_cghs_percent=round(vs_cghs, 1) if vs_cghs else None,
            sample_count=r.your_sample_count,
            status=status,
        ))
    
    # Sort by overcharge percentage
    procedures.sort(key=lambda x: x.vs_market_percent or 0, reverse=True)
    
    # Generate recommendations
    recommendations = []
    if overpriced_count > 0:
        recommendations.append(
            f"📈 {overpriced_count} procedures are priced above market average. "
            "Consider reviewing these for competitive positioning."
        )
    if competitive_count > 0:
        recommendations.append(
            f"✅ {competitive_count} procedures are competitively priced. "
            "Maintain these rates to attract patients."
        )
    if underpriced_count > 0:
        recommendations.append(
            f"📉 {underpriced_count} procedures may be underpriced. "
            "You might be leaving revenue on the table."
        )
    
    return PricingComparison(
        procedures=procedures,
        summary={
            "total_procedures": len(procedures),
            "overpriced": overpriced_count,
            "competitive": competitive_count,
            "underpriced": underpriced_count,
        },
        recommendations=recommendations,
    )


@router.get("/competitors", response_model=CompetitorAnalysis)
async def get_competitor_analysis(
    hospital_id: Optional[int] = Query(None, description="Hospital ID (admin only)"),
    procedure_id: Optional[int] = Query(None, description="Filter by procedure"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Get anonymized competitor analysis.
    
    Shows how your pricing compares to competitors in:
    - Same city
    - Same hospital type
    - Same tier
    """
    user, hospital = get_hospital_admin(db, user_id)
    
    if hospital is None and hospital_id:
        hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")
    elif hospital is None:
        raise HTTPException(status_code=400, detail="Hospital ID required")
    
    # Get competitor pricing (anonymized by hospital type and city tier)
    query = db.query(
        PricePoint.hospital_type,
        PricePoint.city_tier,
        func.avg(PricePoint.charged_amount).label("avg_price"),
        func.count(PricePoint.id).label("sample_count"),
    ).filter(
        PricePoint.hospital_id != hospital.id,  # Exclude own hospital
        PricePoint.city == hospital.city,  # Same city
    )
    
    if procedure_id:
        query = query.filter(PricePoint.procedure_id == procedure_id)
    
    results = query.group_by(
        PricePoint.hospital_type,
        PricePoint.city_tier
    ).all()
    
    competitors = []
    for r in results:
        competitors.append(CompetitorSummary(
            hospital_type=r.hospital_type.value if r.hospital_type else "unknown",
            city_tier=r.city_tier.value if r.city_tier else "unknown",
            avg_price=r.avg_price,
            sample_count=r.sample_count,
        ))
    
    # Get own average
    own_avg = db.query(
        func.avg(PricePoint.charged_amount)
    ).filter(
        PricePoint.hospital_id == hospital.id
    )
    if procedure_id:
        own_avg = own_avg.filter(PricePoint.procedure_id == procedure_id)
    own_avg = own_avg.scalar() or 0
    
    # Calculate position
    competitor_avg = sum(c.avg_price for c in competitors) / len(competitors) if competitors else 0
    
    if competitor_avg > 0:
        diff = ((own_avg - competitor_avg) / competitor_avg) * 100
        if diff > 15:
            position = "above_average"
        elif diff < -15:
            position = "below_average"
        else:
            position = "competitive"
    else:
        position = "unknown"
    
    # Generate insights
    insights = []
    if position == "above_average":
        insights.append(
            "⚠️ Your prices are above the city average. "
            "Consider if premium services justify higher prices."
        )
    elif position == "below_average":
        insights.append(
            "💡 Your prices are below average. "
            "You're well-positioned for cost-conscious patients."
        )
    else:
        insights.append(
            "✅ Your prices are competitive with the market. "
            "Focus on service quality for differentiation."
        )
    
    if hospital.is_nabh_accredited:
        insights.append(
            "🏆 NABH accreditation allows premium positioning. "
            "Highlight quality credentials in marketing."
        )
    
    return CompetitorAnalysis(
        your_hospital=hospital.name,
        competitors=competitors,
        your_position=position,
        insights=insights,
    )


@router.get("/trends")
async def get_pricing_trends(
    hospital_id: Optional[int] = Query(None, description="Hospital ID (admin only)"),
    period: str = Query("30d", description="Period: 7d, 30d, 90d, 1y"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Get pricing trends over time.
    
    Shows how your prices and scores have changed.
    """
    user, hospital = get_hospital_admin(db, user_id)
    
    if hospital is None and hospital_id:
        hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")
    elif hospital is None:
        raise HTTPException(status_code=400, detail="Hospital ID required")
    
    # Parse period
    period_days = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}.get(period, 30)
    start_date = datetime.now(timezone.utc) - timedelta(days=period_days)
    
    # Get historical scores
    scores = db.query(HospitalScore).filter(
        HospitalScore.hospital_id == hospital.id,
        HospitalScore.period_end >= start_date
    ).order_by(HospitalScore.period_end).all()
    
    # Get daily price observations
    daily_stats = db.query(
        func.date(PricePoint.created_at).label("date"),
        func.count(PricePoint.id).label("observations"),
        func.avg(PricePoint.charged_amount).label("avg_amount"),
    ).filter(
        PricePoint.hospital_id == hospital.id,
        PricePoint.created_at >= start_date
    ).group_by(
        func.date(PricePoint.created_at)
    ).order_by(
        func.date(PricePoint.created_at)
    ).all()
    
    return {
        "hospital_name": hospital.name,
        "period": period,
        "score_trend": [
            {
                "date": s.period_end.isoformat(),
                "overall_score": s.overall_score,
                "pricing_score": s.pricing_score,
            }
            for s in scores
        ],
        "daily_observations": [
            {
                "date": str(d.date),
                "observations": d.observations,
                "avg_amount": d.avg_amount,
            }
            for d in daily_stats
        ],
        "summary": {
            "total_observations": sum(d.observations for d in daily_stats),
            "avg_daily_observations": (
                sum(d.observations for d in daily_stats) / len(daily_stats) 
                if daily_stats else 0
            ),
        }
    }


@router.get("/categories")
async def get_category_breakdown(
    hospital_id: Optional[int] = Query(None, description="Hospital ID (admin only)"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Get pricing breakdown by procedure category.
    
    Shows which categories are overpriced or competitive.
    """
    user, hospital = get_hospital_admin(db, user_id)
    
    if hospital is None and hospital_id:
        hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital not found")
    elif hospital is None:
        raise HTTPException(status_code=400, detail="Hospital ID required")
    
    # Get category-wise stats
    results = db.query(
        Procedure.category,
        func.count(PricePoint.id).label("observation_count"),
        func.avg(PricePoint.charged_amount).label("avg_price"),
        func.avg(PricePoint.cghs_comparison).label("avg_cghs_diff"),
        func.avg(PricePoint.market_comparison).label("avg_market_diff"),
    ).join(
        PricePoint, PricePoint.procedure_id == Procedure.id
    ).filter(
        PricePoint.hospital_id == hospital.id
    ).group_by(
        Procedure.category
    ).all()
    
    categories = []
    for r in results:
        avg_diff = r.avg_cghs_diff or r.avg_market_diff or 0
        if avg_diff > 20:
            status = "overpriced"
        elif avg_diff < -10:
            status = "underpriced"
        else:
            status = "competitive"
        
        categories.append({
            "category": r.category or "unknown",
            "observation_count": r.observation_count,
            "avg_price": round(r.avg_price, 2) if r.avg_price else 0,
            "vs_benchmark_percent": round(avg_diff, 1),
            "status": status,
        })
    
    # Sort by observation count
    categories.sort(key=lambda x: x["observation_count"], reverse=True)
    
    return {
        "hospital_name": hospital.name,
        "categories": categories,
        "total_categories": len(categories),
    }


@router.post("/claim", response_model=HospitalClaimResponse)
async def claim_hospital(
    request: HospitalClaimRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Claim a hospital for dashboard access.
    
    Starts the verification process to link a hospital to your account.
    """
    # Check if hospital exists
    hospital = db.query(Hospital).filter(Hospital.id == request.hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    
    # Check if already claimed
    existing_admin = db.query(User).filter(
        User.hospital_id == request.hospital_id,
        User.role == UserRole.HOSPITAL_ADMIN,
    ).first()
    
    if existing_admin:
        raise HTTPException(
            status_code=400,
            detail="This hospital already has an administrator"
        )
    
    # For now, auto-approve (in production, this would require verification)
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.role = UserRole.HOSPITAL_ADMIN
        user.hospital_id = request.hospital_id
        db.commit()
        
        logger.info(f"Hospital {hospital.name} claimed by user {user_id}")
        
        return HospitalClaimResponse(
            claim_id=hospital.id,
            status="approved",
            message=f"You are now the administrator for {hospital.name}. "
                    "Access your dashboard at /hospital-dashboard"
        )
    
    raise HTTPException(status_code=404, detail="User not found")


@router.get("/available-hospitals")
async def list_available_hospitals(
    city: Optional[str] = Query(None, description="Filter by city"),
    search: Optional[str] = Query(None, description="Search by name"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    List hospitals available to claim.
    
    Shows hospitals that don't have an administrator yet.
    """
    # Get hospital IDs that are already claimed
    claimed_ids = db.query(User.hospital_id).filter(
        User.hospital_id.isnot(None),
        User.role == UserRole.HOSPITAL_ADMIN,
    ).all()
    claimed_ids = [x[0] for x in claimed_ids]
    
    # Query available hospitals
    query = db.query(Hospital)
    
    if claimed_ids:
        query = query.filter(Hospital.id.notin_(claimed_ids))
    
    if city:
        query = query.filter(func.lower(Hospital.city) == city.lower())
    
    if search:
        query = query.filter(Hospital.name.ilike(f"%{search}%"))
    
    hospitals = query.order_by(Hospital.name).limit(limit).all()
    
    return {
        "hospitals": [
            {
                "id": h.id,
                "name": h.name,
                "city": h.city,
                "state": h.state,
                "hospital_type": h.hospital_type.value if h.hospital_type else "unknown",
                "is_verified": h.is_verified,
                "total_bills_analyzed": h.total_bills_analyzed,
            }
            for h in hospitals
        ],
        "total": len(hospitals),
    }

