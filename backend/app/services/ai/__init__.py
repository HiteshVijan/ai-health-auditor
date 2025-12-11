"""
AI Services Module

Modular AI-powered analysis components:
- prompts.py: AI prompt templates
- pricing_data.py: Market pricing reference  
- strategies.py: Negotiation strategies
- document_analysis.py: Document parsing and metrics
"""

from .prompts import SYSTEM_PROMPTS, get_audit_prompt, get_negotiation_prompt
from .pricing_data import get_pricing_context, INDIA_PRICING, US_PRICING
from .strategies import NEGOTIATION_STRATEGIES, get_insider_tips
from .document_analysis import parse_indian_bill, get_key_metrics, CGHS_PROCEDURE_RATES

