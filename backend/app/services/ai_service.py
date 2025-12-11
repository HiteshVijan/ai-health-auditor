"""
🤖 AI Service for Medical Bill Auditing

FREE AI Integration using:
- Groq (FREE tier: 30 req/min, Llama 3.1, Mixtral)
- Ollama (LOCAL, completely free, any model)

AI is used at EVERY stage:
1. 📄 Bill OCR & Text Extraction
2. 🔍 Intelligent Bill Analysis
3. 💰 Overcharge Detection with Fair Pricing
4. ✉️ Personalized Negotiation Letter Generation
5. 💬 Conversational Assistance
"""

import os
import logging
import json
import httpx
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    """Available AI providers (all FREE!)."""
    GROQ = "groq"           # Free tier: 30 req/min
    OLLAMA = "ollama"       # Local, completely free
    MOCK = "mock"           # Fallback demo mode


# Import modular AI components
try:
    from app.services.ai.prompts import SYSTEM_PROMPTS, get_audit_prompt
    from app.services.ai.pricing_data import get_pricing_context
    from app.services.ai.strategies import get_insider_tips, get_success_probability
    AI_MODULES_AVAILABLE = True
    logger.info("✅ AI modules loaded successfully")
except ImportError as e:
    AI_MODULES_AVAILABLE = False
    logger.warning(f"AI modules not available: {e}. Using fallback prompts.")
    # Fallback system prompts
    SYSTEM_PROMPTS = {
        "auditor": "You are an expert medical bill auditor. Respond with valid JSON only.",
        "negotiator": "You are an expert medical bill negotiator.",
        "analyzer": "You are a medical bill analyzer.",
        "assistant": "You are a healthcare billing assistant.",
    }


class AIService:
    """
    🤖 AI-Powered Medical Bill Auditing Service
    
    FREE AI at every stage:
    ✅ Bill Analysis
    ✅ Issue Detection  
    ✅ Fair Price Comparison
    ✅ Negotiation Letters
    ✅ Patient Assistance
    """
    
    def __init__(self):
        """Initialize with best available FREE AI provider."""
        self.groq_api_key = os.environ.get("GROQ_API_KEY", "")
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        
        # Model preferences
        self.groq_model = "llama-3.1-8b-instant"  # Fast and free
        self.ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.2")
        
        # Detect provider
        self.provider = self._detect_provider()
        logger.info(f"🤖 AI Service initialized: {self.provider.value.upper()}")
    
    def _detect_provider(self) -> AIProvider:
        """Detect available FREE AI provider."""
        # Prefer Groq (cloud, reliable, free tier)
        if self.groq_api_key:
            logger.info("✅ Groq API key found - using cloud AI")
            return AIProvider.GROQ
        
        # Check Ollama (local)
        try:
            response = httpx.get(f"{self.ollama_url}/api/tags", timeout=2.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                if models:
                    logger.info(f"✅ Ollama found with {len(models)} models")
                    return AIProvider.OLLAMA
        except Exception:
            pass
        
        logger.warning("⚠️ No AI provider - using demo mode")
        return AIProvider.MOCK
    
    def get_status(self) -> Dict[str, Any]:
        """Get AI service status for display."""
        return {
            "provider": self.provider.value,
            "model": self.groq_model if self.provider == AIProvider.GROQ else self.ollama_model,
            "status": "active" if self.provider != AIProvider.MOCK else "demo_mode",
            "capabilities": [
                "bill_analysis",
                "issue_detection", 
                "fair_pricing",
                "negotiation_letters",
                "patient_assistance"
            ]
        }

    # =========================================================
    # 📄 STAGE 1: Bill Text Extraction & Parsing
    # =========================================================
    
    async def extract_bill_data(self, bill_text: str) -> Dict[str, Any]:
        """
        🔍 AI-powered bill data extraction.
        
        Extracts structured data from raw bill text:
        - Hospital/Provider info
        - Patient details
        - Line items with codes and amounts
        - Totals and taxes
        """
        prompt = f"""Extract structured data from this medical bill.

BILL TEXT:
{bill_text[:3000]}

Return JSON with this structure:
{{
    "provider": {{
        "name": "hospital/clinic name",
        "address": "address if found",
        "type": "government|private|corporate"
    }},
    "patient": {{
        "name": "patient name",
        "id": "patient/invoice ID"
    }},
    "date": "bill date",
    "line_items": [
        {{
            "description": "service description",
            "code": "CPT/procedure code if present",
            "quantity": 1,
            "unit_price": 0,
            "total": 0
        }}
    ],
    "subtotal": 0,
    "tax_amount": 0,
    "tax_rate": 0,
    "total": 0,
    "currency": "₹ or $",
    "region": "IN or US"
}}"""
        
        response = await self._call_llm(prompt, "analyzer")
        return self._parse_json_response(response, self._default_bill_data())

    # =========================================================
    # 🔍 STAGE 2: Intelligent Bill Analysis
    # =========================================================
    
    async def analyze_bill(
        self,
        bill_data: Dict[str, Any],
        region: str = "IN"
    ) -> Dict[str, Any]:
        """
        🔍 AI-powered comprehensive bill analysis.
        
        Analyzes for:
        - Overcharges vs fair market rates
        - Duplicate/unbundled charges
        - Arithmetic errors
        - Unnecessary services
        - Coding issues
        """
        if region == "IN":
            pricing_context = """
INDIAN HEALTHCARE PRICING REFERENCE:
- CGHS (Central Govt) rates are the benchmark
- PMJAY packages for common surgeries
- Hospital type multipliers:
  * Government: 1.0x (baseline)
  * CGHS Empaneled: 1.2x
  * Private: 1.5x
  * Corporate (Apollo, Fortis): 2.0x
- Common procedure rates:
  * Cholecystectomy: ₹45,000-90,000 (CGHS: ₹45,000)
  * MRI: ₹3,000-8,000 (CGHS: ₹3,000)
  * ICU/day: ₹5,000-20,000
  * Room/day: ₹2,000-8,000
"""
        else:
            pricing_context = """
US HEALTHCARE PRICING REFERENCE:
- Medicare Fee Schedule is the benchmark
- Common CPT code rates:
  * 99214 (Office visit): $75-150
  * 85025 (CBC): $10-30
  * 70553 (MRI Brain): $400-800
  * 71046 (Chest X-ray): $30-75
- Watch for upcoding (higher code than warranted)
- Watch for unbundling (separate billing for bundled services)
"""

        bill_json = json.dumps(bill_data, indent=2, default=str)
        
        prompt = f"""Analyze this medical bill like an INSIDER who works in the hospital industry.
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
    "currency": "{'₹' if region == 'IN' else '$'}",
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

        response = await self._call_llm(prompt, "auditor")
        return self._parse_json_response(response, self._default_analysis(region))

    # =========================================================
    # 💰 STAGE 3: Fair Price Lookup with AI
    # =========================================================
    
    async def get_fair_price(
        self,
        procedure: str,
        region: str = "IN",
        hospital_type: str = "private"
    ) -> Dict[str, Any]:
        """
        💰 AI-powered fair price estimation.
        
        Returns fair market price for a procedure based on:
        - Region (India/US)
        - Hospital type
        - Standard pricing databases
        """
        prompt = f"""What is the fair market price for this medical procedure?

Procedure: {procedure}
Region: {region}
Hospital Type: {hospital_type}

Return JSON:
{{
    "procedure": "{procedure}",
    "fair_price_low": <minimum fair price>,
    "fair_price_high": <maximum fair price>,
    "fair_price_median": <typical price>,
    "benchmark_source": "CGHS|Medicare|market average",
    "notes": "any relevant notes"
}}

Use actual healthcare pricing data."""

        response = await self._call_llm(prompt, "auditor")
        return self._parse_json_response(response, {
            "procedure": procedure,
            "fair_price_low": 0,
            "fair_price_high": 0,
            "fair_price_median": 0,
            "benchmark_source": "estimate",
            "notes": "AI estimation"
        })

    # =========================================================
    # ✉️ STAGE 4: Negotiation Letter Generation
    # =========================================================
    
    async def generate_negotiation_letter(
        self,
        bill_summary: str,
        issues: List,
        savings: float,
        currency: str,
        tone: str = "formal",
        patient_name: str = "[Your Name]",
        hospital_name: str = "the hospital",
        region: str = "IN",
    ) -> str:
        """
        ✉️ AI-powered personalized negotiation letter with structured tables.
        
        Generates compelling dispute letters with:
        - Tabular breakdown of disputed charges
        - Detailed analysis per charge
        - Clear summary boxes
        - Regulatory references
        """
        # Use the new prompt from prompts module
        from app.services.ai.prompts import get_negotiation_prompt
        
        prompt = get_negotiation_prompt(
            bill_summary=bill_summary,
            issues=issues if isinstance(issues, list) else [],
            savings=savings,
            currency=currency,
            tone=tone,
            region=region,
        )
        
        letter = await self._call_llm(prompt, "negotiator")
        
        # Clean and validate
        letter = letter.strip()
        if len(letter) < 200:
            letter = self._fallback_letter(issues, savings, currency, tone)
        
        return letter

    # =========================================================
    # 💬 STAGE 5: Conversational Assistant
    # =========================================================
    
    async def chat(
        self,
        message: str,
        context: Optional[Dict] = None
    ) -> str:
        """
        💬 AI-powered patient assistance chatbot.
        
        Helps patients:
        - Understand their bills
        - Navigate the dispute process
        - Answer healthcare billing questions
        """
        context_str = ""
        if context:
            context_str = f"\nCONTEXT: {json.dumps(context, default=str)[:500]}"
        
        prompt = f"""Patient question: {message}
{context_str}

Provide a helpful, accurate response about medical billing.
Be empathetic but professional. Keep response under 200 words."""

        return await self._call_llm(prompt, "assistant")

    # =========================================================
    # 🔧 Internal Methods
    # =========================================================
    
    async def _call_llm(self, prompt: str, role: str = "auditor") -> str:
        """Call the LLM with appropriate system prompt."""
        system_prompt = SYSTEM_PROMPTS.get(role, SYSTEM_PROMPTS["auditor"])
        
        if self.provider == AIProvider.GROQ:
            return await self._call_groq(prompt, system_prompt)
        elif self.provider == AIProvider.OLLAMA:
            return await self._call_ollama(prompt, system_prompt)
        else:
            return self._mock_response(prompt, role)
    
    async def _call_groq(self, prompt: str, system_prompt: str) -> str:
        """Call Groq API (FREE tier)."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.groq_url,
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.groq_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 2000,
                    },
                    timeout=30.0,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    logger.info(f"✅ Groq response: {len(content)} chars")
                    return content
                else:
                    logger.error(f"Groq error: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Groq call failed: {e}")
        
        return ""
    
    async def _call_ollama(self, prompt: str, system_prompt: str) -> str:
        """Call Ollama API (LOCAL, FREE)."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": f"{system_prompt}\n\n{prompt}",
                        "stream": False,
                    },
                    timeout=60.0,
                )
                
                if response.status_code == 200:
                    content = response.json().get("response", "")
                    logger.info(f"✅ Ollama response received ({len(content)} chars)")
                    return content
                    
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
        
        return ""
    
    def _parse_json_response(self, response: str, default: Dict) -> Dict:
        """Extract JSON from LLM response."""
        if not response:
            return default
        try:
            # Remove markdown code blocks if present
            text = response
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                parts = text.split('```')
                for part in parts:
                    if '{' in part and '}' in part:
                        text = part
                        break
            
            # Find JSON in response
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
        except Exception as e:
            logger.warning(f"JSON parse failed: {e}")
        return default
    
    def _mock_response(self, prompt: str, role: str) -> str:
        """Mock response for demo mode."""
        if role == "negotiator":
            return self._fallback_letter([], 45000, "₹", "formal")
        return "{}"
    
    def _default_bill_data(self) -> Dict:
        """Default bill data structure."""
        return {
            "provider": {"name": "Unknown", "type": "private"},
            "patient": {"name": "Patient"},
            "line_items": [],
            "total": 0,
            "currency": "₹",
            "region": "IN"
        }
    
    def _default_analysis(self, region: str) -> Dict:
        """Empty analysis when AI unavailable - NO hardcoded data."""
        return {
            "score": 0,
            "total_issues": 0,
            "critical_count": 0,
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "potential_savings": 0,
            "currency": "₹" if region == "IN" else "$",
            "region": region,
            "issues": [],
            "summary": "Analysis unavailable. Please ensure AI is configured.",
            "error": "AI provider not available"
        }
    
    def _fallback_letter(self, issues: List, savings: float, currency: str, tone: str) -> str:
        """Fallback letter template."""
        issues_text = "\n".join([
            f"  • {issue.get('description', 'Billing discrepancy')}"
            for issue in issues[:5]
        ]) or "  • Charges exceed standard healthcare pricing benchmarks"
        
        return f"""Dear Billing Department,

I am writing to formally dispute charges on my recent medical bill.

After careful analysis using healthcare pricing benchmarks, I have identified the following issues:

{issues_text}

Based on standard rates (CGHS/Medicare fee schedules), I believe there is an overcharge of approximately {currency}{savings:,.0f}.

I respectfully request:
1. A detailed itemized breakdown of all charges
2. Justification for charges exceeding standard rates  
3. Adjustment to reflect fair market pricing

Please respond within 30 days as required by healthcare billing regulations.

Sincerely,
[Your Name]
[Contact Information]

---
[Generated by AI Medical Bill Auditor]"""


# Lazy singleton - initialized on first access to pick up env vars
_ai_service_instance = None

def get_ai_service() -> AIService:
    """Get AI service instance (lazy initialization)."""
    global _ai_service_instance
    if _ai_service_instance is None:
        _ai_service_instance = AIService()
    return _ai_service_instance

# For backwards compat - create a real instance only when accessed
# This class wraps the lazy singleton
class _LazyAIService:
    """Lazy proxy that creates AIService on first use."""
    _instance = None
    
    def __getattribute__(self, name):
        if name == '_instance':
            return object.__getattribute__(self, name)
        
        if _LazyAIService._instance is None:
            _LazyAIService._instance = AIService()
        return getattr(_LazyAIService._instance, name)

ai_service = _LazyAIService()
