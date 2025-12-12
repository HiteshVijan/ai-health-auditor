"""
Pricing Intelligence API Endpoints.

Public and B2B APIs for:
- Price lookups (CGHS/PMJAY + crowdsourced data)
- Procedure search
- Hospital scoring and search
- Price contributions
- Analytics endpoints

This is the core B2B API that creates the "Data Moat".
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.db.session import get_db
from app.api.deps import get_current_user_id, get_optional_user_id
from app.services.pricing_service import pricing_service
from app.models.pricing import (
    Hospital, Procedure, PricePoint, HospitalType, CityTier
)
from app.schemas.pricing import (
    # Lookup
    PriceLookupRequest, PriceLookupResponse,
    ProcedureSearchResult, ProcedureSearchResponse,
    # Hospital
    HospitalCreate, HospitalRead, HospitalScore,
    HospitalSearchRequest, HospitalSearchResponse, HospitalCompare,
    # Contributions
    PriceContributionCreate, PriceContributionResponse,
    BulkPriceContribution, BulkContributionResponse,
    # Analytics
    PricingStats, DatabaseStats,
    HospitalTypeEnum, CityTierEnum
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# Price Lookup Endpoints (Public)
# ============================================

@router.get("/lookup", response_model=PriceLookupResponse)
async def lookup_price(
    procedure: str = Query(..., min_length=2, description="Procedure name to look up"),
    city: Optional[str] = Query(None, description="City for location-based pricing"),
    hospital_name: Optional[str] = Query(None, description="Specific hospital name"),
    hospital_type: Optional[HospitalTypeEnum] = Query(None, description="Hospital type filter"),
    db: Session = Depends(get_db),
):
    """
    🔍 Look up fair price for a medical procedure.
    
    Returns:
    - Official CGHS/PMJAY rates
    - Crowdsourced market prices
    - Fair price range
    
    **Free API** - No authentication required.
    Rate limited to 100 requests/hour per IP.
    """
    result = pricing_service.lookup_price(
        procedure_name=procedure,
        db=db,
        city=city,
        hospital_name=hospital_name,
        hospital_type=HospitalType(hospital_type.value) if hospital_type else None,
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No pricing data found for procedure: {procedure}"
        )
    
    return result


@router.get("/lookup/batch")
async def lookup_prices_batch(
    procedures: List[str] = Query(..., description="List of procedures to look up"),
    city: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    🔍 Batch price lookup for multiple procedures.
    
    **B2B API** - For insurers and TPAs processing multiple procedures.
    """
    if len(procedures) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 procedures per batch"
        )
    
    results = []
    for proc in procedures:
        result = pricing_service.lookup_price(
            procedure_name=proc,
            db=db,
            city=city,
        )
        results.append({
            "procedure": proc,
            "found": result is not None,
            "data": result.model_dump() if result else None
        })
    
    return {
        "total": len(procedures),
        "found": sum(1 for r in results if r["found"]),
        "results": results
    }


@router.get("/search", response_model=ProcedureSearchResponse)
async def search_procedures(
    query: str = Query(..., min_length=2, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    🔎 Search for procedures by name.
    
    Uses fuzzy matching to find procedures even with spelling variations.
    """
    results = pricing_service.search_procedures(query, db, limit)
    
    # Filter by category if provided
    if category:
        results = [r for r in results if category.lower() in r.category.lower()]
    
    return ProcedureSearchResponse(
        query=query,
        results=results,
        total_count=len(results)
    )


@router.get("/categories")
async def list_categories(
    db: Session = Depends(get_db),
):
    """
    📂 List all procedure categories with counts.
    """
    # Get categories from procedures table
    db_cats = db.query(
        Procedure.category,
        func.count(Procedure.id).label('count')
    ).group_by(Procedure.category).all()
    
    # Also include categories from static data
    index = pricing_service._build_procedure_index()
    static_cats = {}
    for data in index.values():
        cat = data.get("category", "unknown")
        base_cat = cat.split("/")[0] if "/" in cat else cat
        static_cats[base_cat] = static_cats.get(base_cat, 0) + 1
    
    # Merge
    categories = {}
    for cat, count in db_cats:
        categories[cat] = categories.get(cat, 0) + count
    for cat, count in static_cats.items():
        categories[cat] = categories.get(cat, 0) + count
    
    return {
        "categories": [
            {"name": cat, "procedure_count": count}
            for cat, count in sorted(categories.items(), key=lambda x: -x[1])
        ]
    }


# ============================================
# Hospital Endpoints
# ============================================

@router.get("/hospitals/search", response_model=HospitalSearchResponse)
async def search_hospitals(
    query: Optional[str] = Query(None, description="Hospital name search"),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    hospital_type: Optional[HospitalTypeEnum] = Query(None),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    is_cghs_empaneled: Optional[bool] = Query(None),
    sort_by: str = Query("overall_score", enum=["overall_score", "pricing_score", "name"]),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    🏥 Search and filter hospitals.
    
    Returns hospitals with their pricing scores and billing statistics.
    """
    query_obj = db.query(Hospital)
    
    if query:
        query_obj = query_obj.filter(
            Hospital.name.ilike(f"%{query}%")
        )
    if city:
        query_obj = query_obj.filter(func.lower(Hospital.city) == city.lower())
    if state:
        query_obj = query_obj.filter(func.lower(Hospital.state) == state.lower())
    if hospital_type:
        query_obj = query_obj.filter(Hospital.hospital_type == HospitalType(hospital_type.value))
    if min_score is not None:
        query_obj = query_obj.filter(Hospital.overall_score >= min_score)
    if is_cghs_empaneled is not None:
        query_obj = query_obj.filter(Hospital.is_cghs_empaneled == is_cghs_empaneled)
    
    # Sorting
    if sort_by == "pricing_score":
        query_obj = query_obj.order_by(desc(Hospital.pricing_score))
    elif sort_by == "name":
        query_obj = query_obj.order_by(Hospital.name)
    else:
        query_obj = query_obj.order_by(desc(Hospital.overall_score))
    
    total = query_obj.count()
    hospitals = query_obj.offset(offset).limit(limit).all()
    
    # Build response
    hospital_reads = []
    for h in hospitals:
        hospital_reads.append(HospitalRead(
            id=h.id,
            name=h.name,
            normalized_name=h.normalized_name,
            city=h.city,
            state=h.state,
            hospital_type=HospitalTypeEnum(h.hospital_type.value),
            city_tier=CityTierEnum(h.city_tier.value),
            is_cghs_empaneled=h.is_cghs_empaneled,
            is_nabh_accredited=h.is_nabh_accredited,
            is_pmjay_empaneled=h.is_pmjay_empaneled,
            scores=HospitalScore(
                pricing_score=h.pricing_score,
                transparency_score=h.transparency_score,
                overall_score=h.overall_score
            ),
            total_bills_analyzed=h.total_bills_analyzed,
            total_procedures_priced=h.total_procedures_priced,
            avg_overcharge_percent=h.avg_overcharge_percent,
            is_verified=h.is_verified,
            created_at=h.created_at
        ))
    
    return HospitalSearchResponse(
        hospitals=hospital_reads,
        total_count=total,
        filters_applied={
            "query": query,
            "city": city,
            "state": state,
            "hospital_type": hospital_type.value if hospital_type else None,
            "min_score": min_score,
            "is_cghs_empaneled": is_cghs_empaneled,
        }
    )


@router.get("/hospitals/{hospital_id}", response_model=HospitalRead)
async def get_hospital(
    hospital_id: int,
    db: Session = Depends(get_db),
):
    """
    🏥 Get detailed hospital information with scoring.
    """
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    
    # Calculate fresh score
    score = pricing_service.calculate_hospital_score(db, hospital_id)
    
    return HospitalRead(
        id=hospital.id,
        name=hospital.name,
        normalized_name=hospital.normalized_name,
        city=hospital.city,
        state=hospital.state,
        hospital_type=HospitalTypeEnum(hospital.hospital_type.value),
        city_tier=CityTierEnum(hospital.city_tier.value),
        is_cghs_empaneled=hospital.is_cghs_empaneled,
        is_nabh_accredited=hospital.is_nabh_accredited,
        is_pmjay_empaneled=hospital.is_pmjay_empaneled,
        scores=score or HospitalScore(
            pricing_score=hospital.pricing_score,
            transparency_score=hospital.transparency_score,
            overall_score=hospital.overall_score
        ),
        total_bills_analyzed=hospital.total_bills_analyzed,
        total_procedures_priced=hospital.total_procedures_priced,
        avg_overcharge_percent=hospital.avg_overcharge_percent,
        is_verified=hospital.is_verified,
        created_at=hospital.created_at
    )


@router.get("/hospitals/{hospital_id}/prices")
async def get_hospital_prices(
    hospital_id: int,
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    💰 Get all prices for a specific hospital.
    
    Useful for comparing hospital pricing across procedures.
    """
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    
    query = db.query(
        PricePoint,
        Procedure.name.label('procedure_name'),
        Procedure.category.label('category'),
        Procedure.cghs_rate.label('cghs_rate'),
    ).join(
        Procedure, PricePoint.procedure_id == Procedure.id
    ).filter(
        PricePoint.hospital_id == hospital_id
    )
    
    if category:
        query = query.filter(func.lower(Procedure.category) == category.lower())
    
    results = query.order_by(desc(PricePoint.created_at)).limit(limit).all()
    
    prices = []
    for pp, proc_name, cat, cghs_rate in results:
        prices.append({
            "procedure": proc_name,
            "category": cat,
            "charged_amount": pp.charged_amount,
            "cghs_rate": cghs_rate,
            "vs_cghs_percent": pp.cghs_comparison,
            "observation_date": pp.observation_date,
            "is_verified": pp.is_verified
        })
    
    return {
        "hospital": hospital.name,
        "city": hospital.city,
        "total_prices": len(prices),
        "prices": prices
    }


@router.get("/hospitals/compare")
async def compare_hospitals(
    hospital_ids: List[int] = Query(..., description="Hospital IDs to compare"),
    procedure: Optional[str] = Query(None, description="Specific procedure to compare"),
    db: Session = Depends(get_db),
):
    """
    ⚖️ Compare pricing between multiple hospitals.
    
    Useful for patients deciding between hospitals.
    """
    if len(hospital_ids) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 hospitals for comparison"
        )
    
    hospitals = db.query(Hospital).filter(Hospital.id.in_(hospital_ids)).all()
    
    if len(hospitals) != len(hospital_ids):
        raise HTTPException(status_code=404, detail="One or more hospitals not found")
    
    comparison = []
    for hospital in hospitals:
        # Get average prices
        query = db.query(
            func.avg(PricePoint.charged_amount).label('avg_price'),
            func.avg(PricePoint.cghs_comparison).label('avg_vs_cghs'),
            func.count(PricePoint.id).label('data_points')
        ).filter(
            PricePoint.hospital_id == hospital.id
        )
        
        if procedure:
            proc = db.query(Procedure).filter(
                func.lower(Procedure.name).like(f"%{procedure.lower()}%")
            ).first()
            if proc:
                query = query.filter(PricePoint.procedure_id == proc.id)
        
        result = query.first()
        
        comparison.append({
            "hospital_id": hospital.id,
            "hospital_name": hospital.name,
            "city": hospital.city,
            "hospital_type": hospital.hospital_type.value,
            "overall_score": hospital.overall_score,
            "pricing_score": hospital.pricing_score,
            "avg_price": float(result.avg_price) if result.avg_price else None,
            "avg_vs_cghs_percent": float(result.avg_vs_cghs) if result.avg_vs_cghs else None,
            "data_points": result.data_points,
        })
    
    # Sort by pricing score
    comparison.sort(key=lambda x: x.get("pricing_score", 0), reverse=True)
    
    return {
        "procedure_filter": procedure,
        "hospitals": comparison,
        "recommendation": comparison[0]["hospital_name"] if comparison else None
    }


# ============================================
# Price Contribution Endpoints
# ============================================

@router.post("/contribute", response_model=PriceContributionResponse)
async def contribute_price(
    contribution: PriceContributionCreate,
    db: Session = Depends(get_db),
    user_id: Optional[int] = Depends(get_optional_user_id),
):
    """
    📤 Contribute a price data point.
    
    Every contribution helps build better pricing intelligence.
    Authenticated users earn contribution points.
    """
    result = pricing_service.add_price_contribution(
        db=db,
        contribution=contribution,
        user_id=user_id
    )
    return result


@router.post("/contribute/bulk", response_model=BulkContributionResponse)
async def contribute_prices_bulk(
    bulk: BulkPriceContribution,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    📤 Bulk contribute price data from a processed bill.
    
    Used internally after bill processing.
    """
    successful = 0
    failed = 0
    errors = []
    total_points = 0
    
    for contribution in bulk.contributions:
        try:
            contribution.source_document_id = bulk.document_id
            result = pricing_service.add_price_contribution(
                db=db,
                contribution=contribution,
                user_id=user_id
            )
            if result.success:
                successful += 1
                total_points += result.points_earned
            else:
                failed += 1
                errors.append(f"{contribution.procedure_name}: Failed")
        except Exception as e:
            failed += 1
            errors.append(f"{contribution.procedure_name}: {str(e)}")
    
    return BulkContributionResponse(
        success=successful > 0,
        total_submitted=len(bulk.contributions),
        successful=successful,
        failed=failed,
        errors=errors[:10],  # Limit errors
        total_points_earned=total_points
    )


# ============================================
# Analytics Endpoints (B2B)
# ============================================

@router.get("/stats", response_model=DatabaseStats)
async def get_database_stats(
    db: Session = Depends(get_db),
):
    """
    📊 Get pricing database statistics.
    
    Shows the size and coverage of the pricing intelligence database.
    """
    return pricing_service.get_database_stats(db)


@router.get("/analytics/pricing")
async def get_pricing_analytics(
    category: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    hospital_type: Optional[HospitalTypeEnum] = Query(None),
    db: Session = Depends(get_db),
):
    """
    📈 Get pricing analytics and trends.
    
    **B2B API** - Aggregated pricing insights for insurers and analysts.
    """
    # Build base query
    query = db.query(PricePoint).filter(PricePoint.is_outlier == False)
    
    if city:
        query = query.filter(func.lower(PricePoint.city) == city.lower())
    if hospital_type:
        query = query.filter(PricePoint.hospital_type == HospitalType(hospital_type.value))
    
    # Get basic stats
    stats = query.with_entities(
        func.count(PricePoint.id).label('count'),
        func.avg(PricePoint.charged_amount).label('avg'),
        func.min(PricePoint.charged_amount).label('min'),
        func.max(PricePoint.charged_amount).label('max'),
        func.avg(PricePoint.cghs_comparison).label('avg_vs_cghs'),
        func.avg(PricePoint.pmjay_comparison).label('avg_vs_pmjay'),
    ).first()
    
    # Get top overcharged procedures
    overcharged = db.query(
        Procedure.name,
        Procedure.category,
        func.avg(PricePoint.cghs_comparison).label('avg_overcharge'),
        func.count(PricePoint.id).label('data_points')
    ).join(
        PricePoint, PricePoint.procedure_id == Procedure.id
    ).filter(
        PricePoint.cghs_comparison.isnot(None),
        PricePoint.is_outlier == False
    ).group_by(
        Procedure.id
    ).having(
        func.count(PricePoint.id) >= 3
    ).order_by(
        desc(func.avg(PricePoint.cghs_comparison))
    ).limit(10).all()
    
    # Get city breakdown
    city_stats = db.query(
        PricePoint.city,
        func.count(PricePoint.id).label('count'),
        func.avg(PricePoint.cghs_comparison).label('avg_overcharge')
    ).filter(
        PricePoint.city.isnot(None),
        PricePoint.is_outlier == False
    ).group_by(
        PricePoint.city
    ).order_by(
        desc(func.count(PricePoint.id))
    ).limit(20).all()
    
    return {
        "filters": {
            "category": category,
            "city": city,
            "hospital_type": hospital_type.value if hospital_type else None
        },
        "summary": {
            "total_data_points": stats.count,
            "avg_price": float(stats.avg) if stats.avg else None,
            "min_price": float(stats.min) if stats.min else None,
            "max_price": float(stats.max) if stats.max else None,
            "avg_vs_cghs_percent": float(stats.avg_vs_cghs) if stats.avg_vs_cghs else None,
            "avg_vs_pmjay_percent": float(stats.avg_vs_pmjay) if stats.avg_vs_pmjay else None,
        },
        "top_overcharged_procedures": [
            {
                "procedure": name,
                "category": cat,
                "avg_overcharge_percent": float(avg_oc),
                "data_points": dp
            }
            for name, cat, avg_oc, dp in overcharged
        ],
        "by_city": [
            {
                "city": city,
                "data_points": count,
                "avg_overcharge_percent": float(avg_oc) if avg_oc else None
            }
            for city, count, avg_oc in city_stats
        ],
        "generated_at": datetime.now(timezone.utc)
    }


@router.get("/analytics/hospital-rankings")
async def get_hospital_rankings(
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    🏆 Get hospital rankings by pricing score.
    
    Shows which hospitals offer the fairest pricing.
    """
    query = db.query(Hospital).filter(Hospital.total_bills_analyzed >= 5)
    
    if city:
        query = query.filter(func.lower(Hospital.city) == city.lower())
    if state:
        query = query.filter(func.lower(Hospital.state) == state.lower())
    
    # Best (highest pricing score = closest to CGHS)
    best = query.order_by(desc(Hospital.pricing_score)).limit(limit).all()
    
    # Worst (lowest pricing score = most expensive)
    worst = query.order_by(Hospital.pricing_score).limit(limit).all()
    
    def format_hospital(h):
        return {
            "id": h.id,
            "name": h.name,
            "city": h.city,
            "hospital_type": h.hospital_type.value,
            "pricing_score": h.pricing_score,
            "overall_score": h.overall_score,
            "avg_overcharge_percent": h.avg_overcharge_percent,
            "bills_analyzed": h.total_bills_analyzed
        }
    
    return {
        "filters": {"city": city, "state": state},
        "most_affordable": [format_hospital(h) for h in best],
        "most_expensive": [format_hospital(h) for h in worst],
        "generated_at": datetime.now(timezone.utc)
    }

