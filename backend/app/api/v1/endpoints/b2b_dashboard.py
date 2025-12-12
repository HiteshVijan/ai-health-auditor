"""
B2B Hospital Dashboard Endpoints.

Dashboard for hospital administrators to view:
- Pricing comparisons vs market
- Hospital scores and rankings
- Competitor analysis
- Trends over time

Uses B2B authentication (separate from B2C).
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.db.session import get_db
from app.api.v1.endpoints.b2b_auth import get_current_b2b_admin
from app.models.hospital_admin import HospitalAdmin
from app.models.pricing import (
    Hospital, Procedure, PricePoint, HospitalScore,
    HospitalType, CityTier
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# Schemas
# ============================================

class DashboardStats(BaseModel):
    """Dashboard statistics."""
    hospital_id: int
    hospital_name: str
    city: str
    state: str
    hospital_type: str
    
    # Scores
    overall_score: float
    pricing_score: float
    transparency_score: float
    
    # Rankings
    city_rank: Optional[int] = None
    city_total: Optional[int] = None
    state_rank: Optional[int] = None
    national_rank: Optional[int] = None
    
    # Statistics
    total_procedures_priced: int
    total_bills_analyzed: int
    avg_overcharge_percent: float
    
    # Admin info
    admin_name: str
    admin_designation: str


class ProcedurePricing(BaseModel):
    """Pricing for a procedure."""
    procedure_id: int
    procedure_name: str
    category: str
    your_price: Optional[float]
    market_average: Optional[float]
    cghs_rate: Optional[float]
    pmjay_rate: Optional[float]
    vs_market_percent: Optional[float]
    status: str  # competitive, overpriced, underpriced


class PricingOverview(BaseModel):
    """Pricing overview."""
    total_procedures: int
    competitive_count: int
    overpriced_count: int
    underpriced_count: int
    procedures: List[ProcedurePricing]
    recommendations: List[str]


class CompetitorData(BaseModel):
    """Anonymized competitor data."""
    segment: str  # e.g., "Private hospitals in Delhi"
    avg_price: float
    sample_count: int
    your_position: str


# ============================================
# Helper Functions
# ============================================

def calculate_rankings(db: Session, hospital: Hospital) -> dict:
    """Calculate hospital rankings."""
    rankings = {}
    
    # City ranking
    city_hospitals = db.query(Hospital).filter(
        Hospital.city == hospital.city,
        Hospital.overall_score > 0
    ).order_by(Hospital.overall_score.desc()).all()
    
    for i, h in enumerate(city_hospitals):
        if h.id == hospital.id:
            rankings["city_rank"] = i + 1
            rankings["city_total"] = len(city_hospitals)
            break
    
    # State ranking
    state_hospitals = db.query(Hospital).filter(
        Hospital.state == hospital.state,
        Hospital.overall_score > 0
    ).order_by(Hospital.overall_score.desc()).all()
    
    for i, h in enumerate(state_hospitals):
        if h.id == hospital.id:
            rankings["state_rank"] = i + 1
            break
    
    # National ranking
    all_hospitals = db.query(Hospital).filter(
        Hospital.overall_score > 0
    ).order_by(Hospital.overall_score.desc()).all()
    
    for i, h in enumerate(all_hospitals):
        if h.id == hospital.id:
            rankings["national_rank"] = i + 1
            break
    
    return rankings


# ============================================
# Endpoints
# ============================================

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    admin: HospitalAdmin = Depends(get_current_b2b_admin),
    db: Session = Depends(get_db),
):
    """
    Get dashboard statistics for the admin's hospital.
    
    Shows scores, rankings, and key metrics.
    """
    hospital = db.query(Hospital).filter(Hospital.id == admin.hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    
    rankings = calculate_rankings(db, hospital)
    
    return DashboardStats(
        hospital_id=hospital.id,
        hospital_name=hospital.name,
        city=hospital.city,
        state=hospital.state,
        hospital_type=hospital.hospital_type.value if hospital.hospital_type else "private",
        overall_score=hospital.overall_score or 50.0,
        pricing_score=hospital.pricing_score or 50.0,
        transparency_score=hospital.transparency_score or 50.0,
        city_rank=rankings.get("city_rank"),
        city_total=rankings.get("city_total"),
        state_rank=rankings.get("state_rank"),
        national_rank=rankings.get("national_rank"),
        total_procedures_priced=hospital.total_procedures_priced or 0,
        total_bills_analyzed=hospital.total_bills_analyzed or 0,
        avg_overcharge_percent=hospital.avg_overcharge_percent or 0.0,
        admin_name=admin.full_name,
        admin_designation=admin.designation,
    )


@router.get("/pricing", response_model=PricingOverview)
async def get_pricing_comparison(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200),
    admin: HospitalAdmin = Depends(get_current_b2b_admin),
    db: Session = Depends(get_db),
):
    """
    Get pricing comparison for your hospital vs market.
    """
    hospital = db.query(Hospital).filter(Hospital.id == admin.hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    
    # Query procedures with pricing
    query = db.query(
        Procedure.id,
        Procedure.name,
        Procedure.category,
        Procedure.cghs_rate,
        Procedure.pmjay_package_rate,
        Procedure.market_median,
        func.avg(PricePoint.charged_amount).label("your_price"),
    ).outerjoin(
        PricePoint,
        (PricePoint.procedure_id == Procedure.id) & (PricePoint.hospital_id == hospital.id)
    )
    
    if category:
        query = query.filter(Procedure.category == category)
    
    results = query.group_by(Procedure.id).limit(limit).all()
    
    procedures = []
    competitive = 0
    overpriced = 0
    underpriced = 0
    
    for r in results:
        your_price = r.your_price
        benchmark = r.market_median or r.cghs_rate
        
        vs_market = None
        status = "competitive"
        
        if your_price and benchmark and benchmark > 0:
            vs_market = ((your_price - benchmark) / benchmark) * 100
            if vs_market > 20:
                status = "overpriced"
                overpriced += 1
            elif vs_market < -15:
                status = "underpriced"
                underpriced += 1
            else:
                competitive += 1
        elif your_price:
            competitive += 1
        
        procedures.append(ProcedurePricing(
            procedure_id=r.id,
            procedure_name=r.name,
            category=r.category or "unknown",
            your_price=your_price,
            market_average=r.market_median,
            cghs_rate=r.cghs_rate,
            pmjay_rate=r.pmjay_package_rate,
            vs_market_percent=round(vs_market, 1) if vs_market else None,
            status=status,
        ))
    
    # Sort by overcharge
    procedures.sort(key=lambda x: x.vs_market_percent or 0, reverse=True)
    
    # Recommendations
    recommendations = []
    if overpriced > 0:
        recommendations.append(
            f"📈 {overpriced} procedures are above market average. Review for competitive positioning."
        )
    if competitive > 0:
        recommendations.append(
            f"✅ {competitive} procedures are competitively priced."
        )
    if underpriced > 0:
        recommendations.append(
            f"📉 {underpriced} procedures may be underpriced. Consider market alignment."
        )
    
    return PricingOverview(
        total_procedures=len(procedures),
        competitive_count=competitive,
        overpriced_count=overpriced,
        underpriced_count=underpriced,
        procedures=procedures,
        recommendations=recommendations,
    )


@router.get("/competitors")
async def get_competitor_analysis(
    admin: HospitalAdmin = Depends(get_current_b2b_admin),
    db: Session = Depends(get_db),
):
    """
    Get anonymized competitor analysis.
    """
    hospital = db.query(Hospital).filter(Hospital.id == admin.hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    
    # Get competitor data by segment
    segments = []
    
    # Same city competitors
    city_avg = db.query(
        func.avg(PricePoint.charged_amount).label("avg_price"),
        func.count(PricePoint.id).label("count"),
    ).filter(
        PricePoint.city == hospital.city,
        PricePoint.hospital_id != hospital.id,
    ).first()
    
    if city_avg and city_avg.avg_price:
        # Get your average
        your_avg = db.query(
            func.avg(PricePoint.charged_amount)
        ).filter(
            PricePoint.hospital_id == hospital.id
        ).scalar() or 0
        
        diff = ((your_avg - city_avg.avg_price) / city_avg.avg_price * 100) if city_avg.avg_price else 0
        
        segments.append({
            "segment": f"Hospitals in {hospital.city}",
            "avg_price": round(city_avg.avg_price, 2),
            "sample_count": city_avg.count,
            "your_avg": round(your_avg, 2),
            "difference_percent": round(diff, 1),
            "your_position": "above" if diff > 10 else "below" if diff < -10 else "competitive",
        })
    
    # Same type competitors
    type_avg = db.query(
        func.avg(PricePoint.charged_amount).label("avg_price"),
        func.count(PricePoint.id).label("count"),
    ).filter(
        PricePoint.hospital_type == hospital.hospital_type,
        PricePoint.hospital_id != hospital.id,
    ).first()
    
    if type_avg and type_avg.avg_price:
        your_avg = db.query(
            func.avg(PricePoint.charged_amount)
        ).filter(
            PricePoint.hospital_id == hospital.id
        ).scalar() or 0
        
        diff = ((your_avg - type_avg.avg_price) / type_avg.avg_price * 100) if type_avg.avg_price else 0
        
        segments.append({
            "segment": f"{hospital.hospital_type.value.title()} hospitals nationwide",
            "avg_price": round(type_avg.avg_price, 2),
            "sample_count": type_avg.count,
            "your_avg": round(your_avg, 2),
            "difference_percent": round(diff, 1),
            "your_position": "above" if diff > 10 else "below" if diff < -10 else "competitive",
        })
    
    return {
        "hospital_name": hospital.name,
        "segments": segments,
        "insights": [
            "Data is anonymized and aggregated from verified bill submissions.",
            "Competitor averages update as new data is collected.",
        ],
    }


@router.get("/trends")
async def get_pricing_trends(
    period: str = Query("30d", description="Period: 7d, 30d, 90d"),
    admin: HospitalAdmin = Depends(get_current_b2b_admin),
    db: Session = Depends(get_db),
):
    """
    Get pricing trends over time.
    """
    hospital = db.query(Hospital).filter(Hospital.id == admin.hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Daily stats
    daily = db.query(
        func.date(PricePoint.created_at).label("date"),
        func.count(PricePoint.id).label("observations"),
        func.avg(PricePoint.charged_amount).label("avg_amount"),
    ).filter(
        PricePoint.hospital_id == hospital.id,
        PricePoint.created_at >= start_date,
    ).group_by(
        func.date(PricePoint.created_at)
    ).all()
    
    return {
        "hospital_name": hospital.name,
        "period": period,
        "data": [
            {
                "date": str(d.date),
                "observations": d.observations,
                "avg_amount": round(d.avg_amount, 2) if d.avg_amount else 0,
            }
            for d in daily
        ],
        "summary": {
            "total_observations": sum(d.observations for d in daily),
            "period_days": days,
        },
    }


@router.get("/categories")
async def get_category_breakdown(
    admin: HospitalAdmin = Depends(get_current_b2b_admin),
    db: Session = Depends(get_db),
):
    """
    Get breakdown by procedure category.
    """
    hospital = db.query(Hospital).filter(Hospital.id == admin.hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    
    results = db.query(
        Procedure.category,
        func.count(PricePoint.id).label("count"),
        func.avg(PricePoint.charged_amount).label("avg_price"),
        func.avg(PricePoint.cghs_comparison).label("avg_vs_cghs"),
    ).join(
        PricePoint, PricePoint.procedure_id == Procedure.id
    ).filter(
        PricePoint.hospital_id == hospital.id
    ).group_by(
        Procedure.category
    ).all()
    
    categories = []
    for r in results:
        status = "competitive"
        if r.avg_vs_cghs and r.avg_vs_cghs > 20:
            status = "overpriced"
        elif r.avg_vs_cghs and r.avg_vs_cghs < -10:
            status = "underpriced"
        
        categories.append({
            "category": r.category or "unknown",
            "observation_count": r.count,
            "avg_price": round(r.avg_price, 2) if r.avg_price else 0,
            "vs_benchmark": round(r.avg_vs_cghs, 1) if r.avg_vs_cghs else 0,
            "status": status,
        })
    
    categories.sort(key=lambda x: x["observation_count"], reverse=True)
    
    return {
        "hospital_name": hospital.name,
        "categories": categories,
    }

