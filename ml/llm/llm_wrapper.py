"""
LLM wrapper for generating natural language audit summaries.

Integrates with OpenAI GPT-4 and HuggingFace models to provide
human-readable summaries and recommendations for audit results.
"""

import json
import logging
import os
import re
from abc import ABC, abstractmethod
from typing import Optional, TypedDict

logger = logging.getLogger(__name__)


class KeyIssue(TypedDict):
    """Type definition for a key issue."""

    id: int
    description: str
    recommendation: str


class AuditSummary(TypedDict):
    """Type definition for audit summary output."""

    summary_bullets: list[str]
    key_issues: list[KeyIssue]


# Default prompt template for audit summarization
AUDIT_SUMMARY_PROMPT = """You are a medical billing expert. Analyze the following audit results and provide a clear, actionable summary.

AUDIT RESULTS:
{audit_json}

Based on the audit results, provide your response in the following JSON format:
{{
    "summary_bullets": [
        "Brief bullet point summarizing a key finding",
        "Another important observation",
        "Overall assessment statement"
    ],
    "key_issues": [
        {{
            "id": 1,
            "description": "Clear description of the issue",
            "recommendation": "Specific actionable recommendation"
        }}
    ]
}}

Guidelines:
- Provide 3-5 summary bullets highlighting the most important findings
- For each issue with severity "high" or "critical", provide a key_issue with specific recommendations
- Recommendations should be actionable and specific
- Use clear, non-technical language where possible
- If the audit score is high (>80), acknowledge the bill appears mostly correct
- Focus on potential savings and areas requiring immediate attention

Respond ONLY with valid JSON, no additional text."""


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate text from prompt.

        Args:
            prompt: Input prompt text.

        Returns:
            str: Generated text response.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI GPT-4 provider implementation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4",
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key. Uses OPENAI_API_KEY env var if not provided.
            model: Model name (gpt-4, gpt-4-turbo, gpt-3.5-turbo).
            temperature: Sampling temperature (0-2).
            max_tokens: Maximum tokens in response.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None

    def is_available(self) -> bool:
        """Check if OpenAI is available."""
        if not self.api_key:
            return False
        try:
            import openai
            return True
        except ImportError:
            return False

    def _get_client(self):
        """Get or create OpenAI client."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def generate(self, prompt: str) -> str:
        """
        Generate text using OpenAI API.

        Args:
            prompt: Input prompt.

        Returns:
            str: Generated response text.

        Raises:
            RuntimeError: If API call fails.
        """
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical billing expert assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"OpenAI API call failed: {e}")


class HuggingFaceProvider(LLMProvider):
    """HuggingFace Transformers provider implementation."""

    def __init__(
        self,
        model_name: str = "mistralai/Mistral-7B-Instruct-v0.2",
        device: str = "auto",
        max_new_tokens: int = 1000,
        temperature: float = 0.3,
    ):
        """
        Initialize HuggingFace provider.

        Args:
            model_name: HuggingFace model identifier.
            device: Device to run on ("auto", "cuda", "cpu").
            max_new_tokens: Maximum new tokens to generate.
            temperature: Sampling temperature.
        """
        self.model_name = model_name
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self._pipeline = None

    def is_available(self) -> bool:
        """Check if HuggingFace is available."""
        try:
            import transformers
            import torch
            return True
        except ImportError:
            return False

    def _get_pipeline(self):
        """Get or create text generation pipeline."""
        if self._pipeline is None:
            from transformers import pipeline
            import torch

            self._pipeline = pipeline(
                "text-generation",
                model=self.model_name,
                device_map=self.device,
                torch_dtype=torch.float16,
            )
        return self._pipeline

    def generate(self, prompt: str) -> str:
        """
        Generate text using HuggingFace model.

        Args:
            prompt: Input prompt.

        Returns:
            str: Generated response text.

        Raises:
            RuntimeError: If generation fails.
        """
        try:
            pipe = self._get_pipeline()

            # Format prompt for instruction-tuned models
            formatted_prompt = f"[INST] {prompt} [/INST]"

            result = pipe(
                formatted_prompt,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                do_sample=True,
                return_full_text=False,
            )

            return result[0]["generated_text"]

        except Exception as e:
            logger.error(f"HuggingFace generation error: {e}")
            raise RuntimeError(f"HuggingFace generation failed: {e}")


class MockProvider(LLMProvider):
    """Mock provider for testing without API calls."""

    def __init__(self, response: Optional[str] = None):
        """
        Initialize mock provider.

        Args:
            response: Fixed response to return. Uses default if None.
        """
        self.response = response

    def is_available(self) -> bool:
        """Mock is always available."""
        return True

    def generate(self, prompt: str) -> str:
        """Return mock response."""
        if self.response:
            return self.response

        # Default mock response
        return json.dumps({
            "summary_bullets": [
                "Bill review completed with potential issues identified",
                "Recommend verification of flagged charges",
                "Overall audit score indicates areas for review",
            ],
            "key_issues": [
                {
                    "id": 1,
                    "description": "Potential billing discrepancy detected",
                    "recommendation": "Review and verify the flagged line items",
                }
            ],
        })


def summarize_audit(
    parsed_audit_json: dict,
    provider: Optional[LLMProvider] = None,
    prompt_template: Optional[str] = None,
) -> AuditSummary:
    """
    Generate a natural language summary of audit results.

    Uses an LLM to create human-readable summaries and actionable
    recommendations from audit findings.

    Args:
        parsed_audit_json: Audit results from audit_engine.
        provider: LLM provider to use. Auto-selects if None.
        prompt_template: Custom prompt template. Uses default if None.

    Returns:
        AuditSummary: Dictionary containing:
            - summary_bullets: List of key finding summaries.
            - key_issues: List of issues with recommendations.

    Example:
        >>> audit = {"score": 72, "issues": [...], "potential_savings": 150.0}
        >>> summary = summarize_audit(audit)
        >>> print(summary["summary_bullets"][0])
        "Bill review identified 3 potential issues..."
    """
    logger.info("Generating audit summary with LLM")

    # Select provider
    if provider is None:
        provider = _get_default_provider()

    # Build prompt
    template = prompt_template or AUDIT_SUMMARY_PROMPT
    audit_str = _format_audit_for_prompt(parsed_audit_json)
    prompt = template.format(audit_json=audit_str)

    try:
        # Generate summary
        response = provider.generate(prompt)

        # Parse response
        summary = _parse_llm_response(response)

        # Validate and fill missing fields
        summary = _validate_and_fill_summary(summary, parsed_audit_json)

        logger.info(
            f"Generated summary with {len(summary['summary_bullets'])} bullets "
            f"and {len(summary['key_issues'])} key issues"
        )

        return summary

    except Exception as e:
        logger.error(f"LLM summarization failed: {e}")
        # Return fallback summary
        return _generate_fallback_summary(parsed_audit_json)


def _get_default_provider() -> LLMProvider:
    """
    Get default LLM provider based on availability.

    Returns:
        LLMProvider: Available provider instance.
    """
    # Try OpenAI first
    openai_provider = OpenAIProvider()
    if openai_provider.is_available():
        logger.info("Using OpenAI provider")
        return openai_provider

    # Try HuggingFace
    hf_provider = HuggingFaceProvider()
    if hf_provider.is_available():
        logger.info("Using HuggingFace provider")
        return hf_provider

    # Fallback to mock
    logger.warning("No LLM provider available, using mock")
    return MockProvider()


def _format_audit_for_prompt(audit: dict) -> str:
    """
    Format audit JSON for inclusion in prompt.

    Args:
        audit: Raw audit dictionary.

    Returns:
        str: Formatted audit string.
    """
    # Extract key fields for cleaner prompt
    formatted = {
        "score": audit.get("score", "N/A"),
        "total_issues": audit.get("total_issues", 0),
        "critical_count": audit.get("critical_count", 0),
        "high_count": audit.get("high_count", 0),
        "medium_count": audit.get("medium_count", 0),
        "low_count": audit.get("low_count", 0),
        "potential_savings": audit.get("potential_savings", 0),
        "issues": [],
    }

    # Include issue details (limit to top 10 for prompt length)
    issues = audit.get("issues", [])[:10]
    for issue in issues:
        formatted["issues"].append({
            "type": issue.get("type", "unknown"),
            "severity": issue.get("severity", "unknown"),
            "description": issue.get("description", "No description"),
            "amount_impact": issue.get("amount_impact"),
        })

    return json.dumps(formatted, indent=2)


def _parse_llm_response(response: str) -> dict:
    """
    Parse LLM response into structured data.

    Args:
        response: Raw LLM response text.

    Returns:
        dict: Parsed response dictionary.

    Raises:
        ValueError: If response cannot be parsed.
    """
    # Clean response
    response = response.strip()

    # Try to extract JSON from response
    # Handle markdown code blocks
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
    if json_match:
        response = json_match.group(1).strip()

    # Try direct JSON parse
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in response
    json_match = re.search(r"\{[\s\S]*\}", response)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse LLM response as JSON: {response[:200]}")


def _validate_and_fill_summary(
    summary: dict,
    audit: dict,
) -> AuditSummary:
    """
    Validate summary and fill missing fields.

    Args:
        summary: Parsed LLM response.
        audit: Original audit data.

    Returns:
        AuditSummary: Validated and complete summary.
    """
    # Ensure summary_bullets exists and is a list
    bullets = summary.get("summary_bullets", [])
    if not isinstance(bullets, list):
        bullets = [str(bullets)] if bullets else []

    # Ensure at least one bullet
    if not bullets:
        bullets = [_generate_default_bullet(audit)]

    # Ensure key_issues exists and is a list
    issues = summary.get("key_issues", [])
    if not isinstance(issues, list):
        issues = []

    # Validate and fix each issue
    validated_issues = []
    for i, issue in enumerate(issues):
        if not isinstance(issue, dict):
            continue

        validated_issue = KeyIssue(
            id=issue.get("id", i + 1),
            description=issue.get(
                "description",
                "Issue identified during audit",
            ),
            recommendation=issue.get(
                "recommendation",
                "Review and verify this item",
            ),
        )
        validated_issues.append(validated_issue)

    return AuditSummary(
        summary_bullets=bullets,
        key_issues=validated_issues,
    )


def _generate_default_bullet(audit: dict) -> str:
    """Generate a default summary bullet from audit data."""
    score = audit.get("score", "N/A")
    total_issues = audit.get("total_issues", 0)
    savings = audit.get("potential_savings", 0)

    if total_issues == 0:
        return f"Audit completed with score {score}/100. No issues detected."
    else:
        return (
            f"Audit completed with score {score}/100. "
            f"Found {total_issues} issue(s) with potential savings of ${savings:.2f}."
        )


def _generate_fallback_summary(audit: dict) -> AuditSummary:
    """
    Generate fallback summary without LLM.

    Args:
        audit: Audit results dictionary.

    Returns:
        AuditSummary: Rule-based summary.
    """
    logger.info("Generating fallback summary (no LLM)")

    score = audit.get("score", 0)
    issues = audit.get("issues", [])
    savings = audit.get("potential_savings", 0)

    # Generate bullets based on audit data
    bullets = []

    # Overall score assessment
    if score >= 90:
        bullets.append(
            f"Bill audit score: {score}/100 - Excellent. "
            "No significant issues detected."
        )
    elif score >= 70:
        bullets.append(
            f"Bill audit score: {score}/100 - Good with minor issues. "
            "Review recommended for flagged items."
        )
    elif score >= 50:
        bullets.append(
            f"Bill audit score: {score}/100 - Moderate concerns. "
            "Several issues require attention."
        )
    else:
        bullets.append(
            f"Bill audit score: {score}/100 - Significant issues detected. "
            "Detailed review strongly recommended."
        )

    # Issue summary
    critical = audit.get("critical_count", 0)
    high = audit.get("high_count", 0)

    if critical > 0:
        bullets.append(
            f"Found {critical} critical issue(s) requiring immediate attention."
        )
    if high > 0:
        bullets.append(f"Found {high} high-severity issue(s) to review.")

    # Savings
    if savings > 0:
        bullets.append(f"Potential savings identified: ${savings:.2f}")

    # Generate key issues from high/critical audit issues
    key_issues = []
    issue_id = 0

    for issue in issues:
        severity = issue.get("severity", "low")
        if severity in ("critical", "high"):
            issue_id += 1
            key_issues.append(
                KeyIssue(
                    id=issue_id,
                    description=issue.get(
                        "description",
                        f"{issue.get('type', 'Issue')} detected",
                    ),
                    recommendation=_get_recommendation_for_type(
                        issue.get("type", "unknown")
                    ),
                )
            )

    # Ensure at least one key issue if problems exist
    if not key_issues and issues:
        key_issues.append(
            KeyIssue(
                id=1,
                description="Issues detected during bill audit",
                recommendation="Review flagged items and verify accuracy",
            )
        )

    return AuditSummary(
        summary_bullets=bullets,
        key_issues=key_issues,
    )


def _get_recommendation_for_type(issue_type: str) -> str:
    """Get recommendation based on issue type."""
    recommendations = {
        "duplicate_charge": (
            "Review line items for duplicates. Request removal of "
            "duplicate charges and refund if applicable."
        ),
        "arithmetic_mismatch": (
            "Verify all calculations. Request itemized breakdown and "
            "corrected invoice if discrepancies found."
        ),
        "tax_mismatch": (
            "Confirm applicable tax rates. Medical services are often "
            "tax-exempt; verify correct tax application."
        ),
        "overcharge": (
            "Compare charges against standard rates for your area. "
            "Request explanation for charges exceeding typical amounts."
        ),
        "missing_field": (
            "Request complete documentation with all required fields. "
            "Incomplete bills may indicate processing errors."
        ),
        "quantity_error": (
            "Verify service quantities match actual services received. "
            "Request correction if quantities are incorrect."
        ),
    }

    return recommendations.get(
        issue_type,
        "Review this issue and verify accuracy with the billing provider.",
    )

