"""
Negotiation API Endpoints.

Uses REAL AI for letter generation - NO hardcoded templates.
"""

import logging
from typing import Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.api.deps import get_current_user_id
from app.services.ai_service import ai_service
from app.services.ocr_service import ocr_service
from app.core.paths import get_upload_path

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# Schemas
# ============================================

class GenerateLetterRequest(BaseModel):
    documentId: int
    tone: str = "formal"


class GeneratedLetter(BaseModel):
    letterId: str
    content: str
    tone: str
    generatedAt: str
    wordCount: int
    ai_provider: str = "none"
    error_message: Optional[str] = None


class ExecuteNegotiationRequest(BaseModel):
    documentId: int
    channel: str
    tone: str
    recipient: str
    letterId: str


class NegotiationResult(BaseModel):
    success: bool
    deliveryStatus: str
    messageId: Optional[str] = None
    timestamp: str
    retryCount: int = 0
    errorMessage: Optional[str] = None


# ============================================
# Endpoints
# ============================================

@router.post("/generate", response_model=GeneratedLetter)
async def generate_letter(
    request: GenerateLetterRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    🤖 AI-Powered Negotiation Letter Generation
    
    Uses real OCR text + AI to create personalized letters.
    NO hardcoded templates.
    """
    # Get document
    result = db.execute(
        text("""SELECT id, filename, content_type, file_key 
                FROM documents WHERE id = :doc_id AND user_id = :user_id"""),
        {"doc_id": request.documentId, "user_id": user_id}
    ).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_id, filename, content_type, file_key = result
    
    # Try to get OCR text from the bill
    ocr_text = None
    if content_type and "image" in content_type.lower() and file_key:
        file_path = get_upload_path(file_key)
        if file_path.exists():
            ocr_text = ocr_service.extract_text(str(file_path))
            if ocr_text:
                logger.info(f"OCR extracted {len(ocr_text)} chars")
    
    if not ocr_text:
        return GeneratedLetter(
            letterId=str(uuid.uuid4()),
            content="",
            tone=request.tone,
            generatedAt=datetime.now().isoformat(),
            wordCount=0,
            ai_provider="none",
            error_message="Could not read document. Please upload a clear image of your bill."
        )
    
    # Detect region and currency from OCR text
    text_lower = ocr_text.lower()
    is_indian = any(kw in text_lower for kw in [
        "medanta", "apollo", "fortis", "max", "narayana", "manipal",
        "india", "gstin", "₹", "inr", "cghs", "pmjay", "nabh"
    ])
    region = "IN" if is_indian else "US"
    currency = "₹" if is_indian else "$"
    
    # First, run a quick audit to get issues and savings
    logger.info(f"Running quick audit for negotiation letter (region: {region})")
    audit_result = None
    try:
        audit_result = await ai_service.analyze_bill(
            ocr_text, 
            region=region,
            filename=filename
        )
    except Exception as e:
        logger.warning(f"Quick audit failed: {e}")
    
    # Extract issues and savings from audit
    issues_list = []
    total_savings = 0
    
    if audit_result and isinstance(audit_result, dict):
        # Get issues
        for issue in audit_result.get("issues", [])[:8]:
            issue_desc = issue.get("description", "")
            amount = issue.get("amount_impact", 0)
            fair = issue.get("fair_price", 0)
            if issue_desc:
                issues_list.append(f"{issue.get('type', 'ISSUE')}: {issue_desc} (Billed: {currency}{amount:,.0f}, Fair: {currency}{fair:,.0f})")
        
        total_savings = audit_result.get("potential_savings", 0)
    
    # Build detailed bill summary
    bill_summary = f"""Medical bill from: {filename}
Region: {region}
Currency: {currency}

--- BILL TEXT (OCR) ---
{ocr_text[:2000]}
--- END BILL TEXT ---

IDENTIFIED ISSUES:
{chr(10).join(issues_list) if issues_list else 'Overcharges detected in multiple line items'}

ESTIMATED SAVINGS: {currency}{total_savings:,.0f}"""
    
    # Use AI to generate the structured letter
    try:
        letter_content = await ai_service.generate_negotiation_letter(
            bill_summary=bill_summary,
            issues=issues_list,
            savings=total_savings,
            currency=currency,
            tone=request.tone,
            region=region,
        )
        
        if not letter_content or len(letter_content) < 100:
            return GeneratedLetter(
                letterId=str(uuid.uuid4()),
                content="",
                tone=request.tone,
                generatedAt=datetime.now().isoformat(),
                wordCount=0,
                ai_provider=ai_service.provider.value,
                error_message="AI could not generate letter. Please try again."
            )
        
        return GeneratedLetter(
            letterId=str(uuid.uuid4()),
            content=letter_content,
            tone=request.tone,
            generatedAt=datetime.now().isoformat(),
            wordCount=len(letter_content.split()),
            ai_provider=ai_service.provider.value,
        )
        
    except Exception as e:
        logger.error(f"Letter generation failed: {e}")
        return GeneratedLetter(
            letterId=str(uuid.uuid4()),
            content="",
            tone=request.tone,
            generatedAt=datetime.now().isoformat(),
            wordCount=0,
            ai_provider=ai_service.provider.value,
            error_message=f"Letter generation failed. Please try again."
        )


@router.post("/execute", response_model=NegotiationResult)
async def execute_negotiation(
    request: ExecuteNegotiationRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    Send the negotiation letter via selected channel.
    
    Note: Actual sending requires email/WhatsApp integration.
    For demo, this simulates the send.
    """
    logger.info(f"Sending negotiation via {request.channel} to {request.recipient}")
    
    # In production, integrate with email service or WhatsApp API
    # For now, return success for demo
    return NegotiationResult(
        success=True,
        deliveryStatus="pending",
        messageId=f"MSG-{uuid.uuid4().hex[:8].upper()}",
        timestamp=datetime.now().isoformat(),
        retryCount=0,
        errorMessage="Note: Email/WhatsApp sending requires additional integration."
    )
