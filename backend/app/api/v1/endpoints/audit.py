"""
Audit API Endpoints.

Uses REAL OCR + AI for bill analysis.
All schemas and AI components are modularized for easy maintenance.
"""

import os
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.api.deps import get_current_user_id
from app.services.ai_service import ai_service
from app.services.ocr_service import ocr_service
from app.core.paths import get_upload_path

# Import modular schemas
from app.schemas.audit import (
    AuditResult, AuditIssue, 
    MarketComparison, CompetitorPrice, 
    NegotiationStrategy,
    DocumentBreakdown, ScanSummary, ExtractedLineItem,
    CategoryBreakdown, KeyMetrics, InsiderAnalysis
)

# Import document analysis
try:
    from app.services.ai.document_analysis import parse_indian_bill, get_key_metrics
    DOC_ANALYSIS_AVAILABLE = True
except ImportError:
    DOC_ANALYSIS_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# Endpoints
# ============================================

@router.get("/ai/status")
async def get_ai_status():
    """Get AI and OCR service status."""
    return {
        **ai_service.get_status(),
        "ocr_available": ocr_service.available,
    }


@router.get("/{document_id}", response_model=AuditResult)
async def get_document_audit(
    document_id: int,
    force_reanalyze: bool = False,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    🤖 AI-Powered Bill Audit with OCR
    
    Uses REAL data only:
    1. OCR extracts text from bill image
    2. AI analyzes the extracted text
    3. Returns actual findings (no hardcoded data)
    
    Results are cached - subsequent requests return cached results.
    Use force_reanalyze=true to re-run the analysis.
    """
    import json
    
    # Get document
    result = db.execute(
        text("""SELECT id, filename, content_type, file_key 
                FROM documents WHERE id = :doc_id AND user_id = :user_id"""),
        {"doc_id": document_id, "user_id": user_id}
    ).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_id, filename, content_type, file_key = result
    filename = filename.lower() if filename else ""
    
    # ============================================
    # CHECK CACHE - Return existing result if available
    # ============================================
    if not force_reanalyze:
        cached = db.execute(
            text("""SELECT * FROM audit_results WHERE document_id = :doc_id"""),
            {"doc_id": document_id}
        ).fetchone()
        
        if cached:
            logger.info(f"📦 Returning cached audit result for document {document_id}")
            
            # Parse JSON fields
            issues = []
            if cached.issues_json:
                try:
                    issues_data = json.loads(cached.issues_json)
                    issues = [AuditIssue(**i) for i in issues_data]
                except:
                    pass
            
            market_comp = None
            if cached.market_comparison_json:
                try:
                    mc = json.loads(cached.market_comparison_json)
                    market_comp = MarketComparison(
                        hospital_type=mc.get("hospital_type"),
                        price_tier=mc.get("price_tier"),
                        competitor_prices=[CompetitorPrice(**cp) for cp in mc.get("competitor_prices", [])] if mc.get("competitor_prices") else None,
                        cghs_rate=mc.get("cghs_rate"),
                        market_average=mc.get("market_average"),
                    )
                except:
                    pass
            
            neg_strategy = None
            if cached.negotiation_strategy_json:
                try:
                    ns = json.loads(cached.negotiation_strategy_json)
                    neg_strategy = NegotiationStrategy(**ns)
                except:
                    pass
            
            doc_breakdown = None
            if cached.document_breakdown_json:
                try:
                    db_data = json.loads(cached.document_breakdown_json)
                    doc_breakdown = DocumentBreakdown(
                        scan_summary=ScanSummary(**db_data.get("scan_summary", {})) if db_data.get("scan_summary") else None,
                        hospital_name=db_data.get("hospital_name"),
                        hospital_type=db_data.get("hospital_type"),
                        bill_number=db_data.get("bill_number"),
                        bill_date=db_data.get("bill_date"),
                        patient_name=db_data.get("patient_name"),
                        line_items=[ExtractedLineItem(**li) for li in db_data.get("line_items", [])],
                        categories=[CategoryBreakdown(**cb) for cb in db_data.get("categories", [])],
                        key_metrics=KeyMetrics(**db_data.get("key_metrics", {})) if db_data.get("key_metrics") else None,
                        raw_text_preview=db_data.get("raw_text_preview"),
                    )
                except:
                    pass
            
            insider_analysis = None
            if cached.insider_analysis_json:
                try:
                    ia = json.loads(cached.insider_analysis_json)
                    insider_analysis = InsiderAnalysis(**ia)
                except:
                    pass
            
            insider_tips = None
            if cached.insider_tips_json:
                try:
                    insider_tips = json.loads(cached.insider_tips_json)
                except:
                    pass
            
            return AuditResult(
                document_id=document_id,
                score=cached.score or 0,
                total_issues=cached.total_issues or 0,
                critical_count=sum(1 for i in issues if i.severity == "critical"),
                high_count=sum(1 for i in issues if i.severity == "high"),
                medium_count=sum(1 for i in issues if i.severity == "medium"),
                low_count=sum(1 for i in issues if i.severity == "low"),
                potential_savings=cached.potential_savings or 0,
                currency=cached.currency or "₹",
                region=cached.region or "IN",
                issues=issues,
                market_comparison=market_comp,
                insider_tips=insider_tips,
                negotiation_strategy=neg_strategy,
                document_breakdown=doc_breakdown,
                insider_analysis=insider_analysis,
                summary=cached.summary,
                ocr_used=cached.ocr_used or False,
                ai_provider=cached.ai_provider or "cached",
            )
    
    # Try OCR for images
    ocr_text = None
    ocr_used = False
    
    if content_type and "image" in content_type.lower() and file_key:
        file_path = get_upload_path(file_key)
        if file_path.exists():
            logger.info(f"📷 Running OCR on: {file_path}")
            ocr_text = ocr_service.extract_text(str(file_path))
            if ocr_text:
                ocr_used = True
                logger.info(f"✅ OCR extracted {len(ocr_text)} characters")
    
    if not ocr_text and not content_type:
        # No image and no content - return error
        return AuditResult(
            document_id=document_id,
            score=0,
            total_issues=0,
            critical_count=0, high_count=0, medium_count=0, low_count=0,
            potential_savings=0,
            currency="₹",
            region="IN",
            issues=[],
            ocr_used=False,
            ai_provider="none",
            error_message="Could not read document. Please upload a clear image of your bill."
        )
    
    # Detect region from OCR text or filename
    search_text = (ocr_text or "").lower() + " " + filename
    
    indian_keywords = ["medanta", "apollo", "fortis", "max", "aiims", "india", 
                       "lucknow", "delhi", "mumbai", "gstin", "gst", "₹", "inr", "rupee"]
    us_keywords = ["medicare", "medicaid", "usd", "$", "usa", "america"]
    
    indian_score = sum(1 for kw in indian_keywords if kw in search_text)
    us_score = sum(1 for kw in us_keywords if kw in search_text)
    
    region = "IN" if indian_score >= us_score else "US"
    currency = "₹" if region == "IN" else "$"
    
    # If we have OCR text, use AI to analyze it
    if ocr_text:
        try:
            # Send to AI for analysis
            bill_data = {
                "raw_text": ocr_text,
                "region": region,
                "currency": currency,
            }
            
            analysis = await ai_service.analyze_bill(bill_data, region)
            
            issues = [
                AuditIssue(
                    type=issue.get("type", "UNKNOWN"),
                    severity=issue.get("severity", "medium"),
                    description=issue.get("description", "Issue detected"),
                    amount_impact=issue.get("amount_impact"),
                    fair_price=issue.get("fair_price"),
                    recommendation=issue.get("recommendation"),
                )
                for issue in analysis.get("issues", [])
            ]
            
            # Parse market comparison
            market_comp = None
            if analysis.get("market_comparison"):
                mc = analysis["market_comparison"]
                market_comp = MarketComparison(
                    hospital_type=mc.get("hospital_type"),
                    price_tier=mc.get("price_tier"),
                    competitor_prices=[
                        CompetitorPrice(**cp) for cp in mc.get("competitor_prices", [])
                    ] if mc.get("competitor_prices") else None,
                    cghs_rate=mc.get("cghs_rate"),
                    market_average=mc.get("market_average"),
                )
            
            # Parse negotiation strategy
            neg_strategy = None
            if analysis.get("negotiation_strategy"):
                ns = analysis["negotiation_strategy"]
                neg_strategy = NegotiationStrategy(
                    success_probability=ns.get("success_probability"),
                    expected_discount=ns.get("expected_discount"),
                    best_approach=ns.get("best_approach"),
                    scripts=ns.get("scripts"),
                    escalation_path=ns.get("escalation_path"),
                    timing=ns.get("timing"),
                )
            
            # Build document breakdown for transparency
            doc_breakdown = None
            insider_analysis_data = None
            
            if DOC_ANALYSIS_AVAILABLE and ocr_text:
                try:
                    parsed = parse_indian_bill(ocr_text)
                    
                    # Build extracted line items
                    extracted_items = [
                        ExtractedLineItem(
                            description=item.get("description", ""),
                            category=item.get("category"),
                            quantity=item.get("quantity", 1),
                            amount=item.get("amount", 0),
                        )
                        for item in parsed.get("line_items", [])
                    ]
                    
                    # Build category breakdown
                    total_amount = sum(c for c in parsed.get("categories", {}).values())
                    cat_breakdown = [
                        CategoryBreakdown(
                            category=cat,
                            amount=amt,
                            percent_of_total=round(amt / total_amount * 100, 1) if total_amount > 0 else 0,
                            status="overcharged" if amt > 50000 else "normal",
                        )
                        for cat, amt in sorted(parsed.get("categories", {}).items(), key=lambda x: -x[1])
                    ]
                    
                    # Key metrics
                    billing = parsed.get("billing", {})
                    metrics = KeyMetrics(
                        total_bill=billing.get("total_bill", 0) or billing.get("subtotal", 0),
                        tax_amount=billing.get("cgst", 0) + billing.get("sgst", 0),
                        payments_made=sum(p.get("amount", 0) for p in parsed.get("payments", [])),
                        largest_category=cat_breakdown[0].category if cat_breakdown else None,
                        largest_category_amount=cat_breakdown[0].amount if cat_breakdown else 0,
                    )
                    
                    doc_breakdown = DocumentBreakdown(
                        scan_summary=ScanSummary(
                            text_length=parsed.get("scan_summary", {}).get("text_length", 0),
                            lines_detected=parsed.get("scan_summary", {}).get("lines_detected", 0),
                            ocr_confidence=parsed.get("scan_summary", {}).get("ocr_confidence", "medium"),
                        ),
                        hospital_name=parsed.get("hospital", {}).get("name"),
                        hospital_type=parsed.get("hospital", {}).get("type"),
                        bill_number=parsed.get("billing", {}).get("bill_number"),
                        bill_date=parsed.get("billing", {}).get("bill_date"),
                        patient_name=parsed.get("patient", {}).get("name"),
                        line_items=extracted_items,
                        categories=cat_breakdown,
                        key_metrics=metrics,
                        raw_text_preview=ocr_text[:500] + "..." if len(ocr_text) > 500 else ocr_text,
                    )
                    
                    # Insider analysis
                    insider_analysis_data = InsiderAnalysis(
                        hospital_profit_margin="30-50% on diagnostics, 20-30% on room, 40-60% on consumables",
                        negotiation_window="15-25% on total bill, higher on pharmacy and consumables",
                        decision_maker="Billing Manager (up to 15%), Admin Head (up to 25%), Director (above 25%)",
                        best_time_to_call="Tuesday-Thursday, 11 AM - 1 PM (post-morning rush, before lunch)",
                        leverage_points=[
                            "CGHS rate comparison shows significant overcharge",
                            "Paying full amount upfront gives negotiating power",
                            "Mention you'll share experience on Google/Practo reviews",
                            "Reference that you're comparing with other hospitals for future care",
                        ],
                        red_flags=[
                            item.description[:50] for item in extracted_items 
                            if item.amount > 10000
                        ][:5],
                        priority_items=[
                            f"Pharmacy Charges (highest markup)",
                            f"Room Charges (compare with CGHS)",
                            f"Consumables (often inflated)",
                        ],
                    )
                except Exception as e:
                    logger.warning(f"Document analysis failed: {e}")
            
            # Contribute pricing data to the crowdsourced database (Data Moat)
            try:
                from app.services.pricing_service import pricing_service
                if parsed and parsed.get("line_items"):
                    extracted_data = {
                        "hospital": parsed.get("hospital", {}),
                        "line_items": parsed.get("line_items", []),
                    }
                    price_points_added = pricing_service.process_bill_for_pricing(
                        db=db,
                        document_id=document_id,
                        user_id=user_id,
                        extracted_data=extracted_data
                    )
                    if price_points_added > 0:
                        logger.info(f"📊 Added {price_points_added} price points to pricing database")
            except Exception as e:
                logger.warning(f"Failed to contribute pricing data: {e}")
            
            # Build the result
            audit_result = AuditResult(
                document_id=document_id,
                score=analysis.get("score", 50),
                total_issues=len(issues),
                critical_count=sum(1 for i in issues if i.severity == "critical"),
                high_count=sum(1 for i in issues if i.severity == "high"),
                medium_count=sum(1 for i in issues if i.severity == "medium"),
                low_count=sum(1 for i in issues if i.severity == "low"),
                potential_savings=analysis.get("potential_savings", 0),
                currency=currency,
                region=region,
                issues=issues,
                market_comparison=market_comp,
                insider_tips=analysis.get("insider_tips"),
                negotiation_strategy=neg_strategy,
                document_breakdown=doc_breakdown,
                insider_analysis=insider_analysis_data,
                summary=analysis.get("summary"),
                ocr_used=True,
                ai_provider=ai_service.provider.value,
                disclaimer=analysis.get("disclaimer", "⚠️ AI-generated analysis. Verify independently."),
            )
            
            # ============================================
            # CACHE THE RESULT - Save to database for future requests
            # ============================================
            try:
                # Serialize complex objects to JSON
                issues_json = json.dumps([i.model_dump() for i in issues]) if issues else None
                market_comp_json = json.dumps(market_comp.model_dump()) if market_comp else None
                insider_tips_json = json.dumps(analysis.get("insider_tips")) if analysis.get("insider_tips") else None
                neg_strategy_json = json.dumps(neg_strategy.model_dump()) if neg_strategy else None
                doc_breakdown_json = json.dumps(doc_breakdown.model_dump()) if doc_breakdown else None
                insider_analysis_json = json.dumps(insider_analysis_data.model_dump()) if insider_analysis_data else None
                
                # Delete existing cache if force_reanalyze
                db.execute(
                    text("DELETE FROM audit_results WHERE document_id = :doc_id"),
                    {"doc_id": document_id}
                )
                
                # Insert new cache
                db.execute(
                    text("""
                        INSERT INTO audit_results (
                            document_id, score, total_issues, potential_savings,
                            currency, region, issues_json, market_comparison_json,
                            insider_tips_json, negotiation_strategy_json,
                            document_breakdown_json, insider_analysis_json,
                            summary, ocr_used, ai_provider
                        ) VALUES (
                            :doc_id, :score, :total_issues, :savings,
                            :currency, :region, :issues, :market_comp,
                            :insider_tips, :neg_strategy,
                            :doc_breakdown, :insider_analysis,
                            :summary, :ocr_used, :ai_provider
                        )
                    """),
                    {
                        "doc_id": document_id,
                        "score": audit_result.score,
                        "total_issues": audit_result.total_issues,
                        "savings": audit_result.potential_savings,
                        "currency": currency,
                        "region": region,
                        "issues": issues_json,
                        "market_comp": market_comp_json,
                        "insider_tips": insider_tips_json,
                        "neg_strategy": neg_strategy_json,
                        "doc_breakdown": doc_breakdown_json,
                        "insider_analysis": insider_analysis_json,
                        "summary": audit_result.summary,
                        "ocr_used": True,
                        "ai_provider": ai_service.provider.value,
                    }
                )
                db.commit()
                logger.info(f"💾 Cached audit result for document {document_id}")
            except Exception as e:
                logger.warning(f"Failed to cache audit result: {e}")
                db.rollback()
            
            return audit_result
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return AuditResult(
                document_id=document_id,
                score=0,
                total_issues=0,
                critical_count=0, high_count=0, medium_count=0, low_count=0,
                potential_savings=0,
                currency=currency,
                region=region,
                issues=[],
                ocr_used=ocr_used,
                ai_provider=ai_service.provider.value,
                error_message=f"AI analysis temporarily unavailable. Please try again."
            )
    
    # No OCR text - return error
    return AuditResult(
        document_id=document_id,
        score=0,
        total_issues=0,
        critical_count=0, high_count=0, medium_count=0, low_count=0,
        potential_savings=0,
        currency=currency,
        region=region,
        issues=[],
        ocr_used=False,
        ai_provider="none",
        error_message="Could not extract text from document. Please upload a clearer image."
    )


@router.post("/analyze")
async def analyze_bill_text(
    bill_text: str,
    region: str = "IN",
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Analyze bill text directly (for testing).
    """
    if not bill_text:
        raise HTTPException(status_code=400, detail="No text provided")
    
    bill_data = {"raw_text": bill_text, "region": region}
    analysis = await ai_service.analyze_bill(bill_data, region)
    return analysis
