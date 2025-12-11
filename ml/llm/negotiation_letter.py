"""
Negotiation letter generation module.

Generates professional letters for disputing medical billing issues
using LLM-powered content generation.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Optional

from llm.llm_wrapper import (
    LLMProvider,
    OpenAIProvider,
    HuggingFaceProvider,
    MockProvider,
    _get_default_provider,
)

logger = logging.getLogger(__name__)


class LetterTone(str, Enum):
    """Available letter tone options."""

    FORMAL = "formal"
    FRIENDLY = "friendly"
    ASSERTIVE = "assertive"


# Tone-specific instructions for LLM
TONE_INSTRUCTIONS = {
    LetterTone.FORMAL: """
Write in a formal, professional business tone:
- Use formal salutations (Dear Sir/Madam, To Whom It May Concern)
- Maintain respectful, neutral language throughout
- Use formal closings (Sincerely, Respectfully)
- Avoid contractions and casual language
- Be precise and factual
""",
    LetterTone.FRIENDLY: """
Write in a friendly, collaborative tone:
- Use warmer salutations (Dear Billing Team, Hello)
- Maintain a cooperative, solution-oriented approach
- Express appreciation for their time and assistance
- Use approachable but still professional language
- Focus on working together to resolve issues
""",
    LetterTone.ASSERTIVE: """
Write in an assertive, firm tone:
- Be direct and confident in stating concerns
- Clearly state expectations and deadlines
- Reference consumer rights and regulations where appropriate
- Maintain professionalism while being firm
- Include clear consequences if issues aren't resolved
- Request specific actions and responses
""",
}

# Letter generation prompt template
LETTER_PROMPT_TEMPLATE = """You are a medical billing advocate helping patients dispute incorrect charges.

Generate a negotiation letter based on the following audit findings:

AUDIT RESULTS:
Score: {score}/100
Total Issues: {total_issues}
Potential Savings: ${potential_savings:.2f}

ISSUES FOUND:
{issues_text}

TONE INSTRUCTIONS:
{tone_instructions}

PATIENT INFORMATION (use placeholders):
- Patient Name: [PATIENT NAME]
- Account Number: [ACCOUNT NUMBER]  
- Date of Service: [DATE OF SERVICE]
- Provider Name: [PROVIDER NAME]

Generate a complete letter that:
1. Introduces the patient and account
2. States the purpose (disputing charges)
3. Lists each issue with specific amounts
4. Requests specific corrections
5. Includes a deadline for response (30 days)
6. Provides contact information placeholder

Format the letter properly with:
- Date
- Recipient address placeholder
- Salutation
- Body paragraphs
- Closing
- Signature block

Return ONLY the letter text, no additional commentary."""


def generate_letter(
    parsed_audit_json: dict,
    tone: str = "formal",
    provider: Optional[LLMProvider] = None,
    patient_info: Optional[dict] = None,
) -> str:
    """
    Generate a negotiation letter for disputing billing issues.

    Creates a professional letter suitable for sending to healthcare
    providers or billing departments to dispute identified issues.

    Args:
        parsed_audit_json: Audit results from audit_engine.
        tone: Letter tone - "formal", "friendly", or "assertive".
        provider: LLM provider to use. Auto-selects if None.
        patient_info: Optional dict with patient details to fill in.

    Returns:
        str: Complete letter text ready for customization.

    Raises:
        ValueError: If tone is not valid.

    Example:
        >>> audit = {"score": 65, "issues": [...], "potential_savings": 150.0}
        >>> letter = generate_letter(audit, tone="formal")
        >>> print(letter)
    """
    # Validate tone
    try:
        letter_tone = LetterTone(tone.lower())
    except ValueError:
        valid_tones = [t.value for t in LetterTone]
        raise ValueError(
            f"Invalid tone '{tone}'. Must be one of: {valid_tones}"
        )

    logger.info(f"Generating {letter_tone.value} negotiation letter")

    # Check if there are issues to dispute
    issues = parsed_audit_json.get("issues", [])
    if not issues:
        logger.info("No issues to dispute, generating acknowledgment letter")
        return _generate_no_issues_letter(parsed_audit_json, letter_tone)

    # Select provider
    if provider is None:
        provider = _get_default_provider()

    # Build prompt
    prompt = _build_letter_prompt(parsed_audit_json, letter_tone)

    try:
        # Generate letter
        letter = provider.generate(prompt)

        # Clean up response
        letter = _clean_letter_response(letter)

        # Fill in patient info if provided
        if patient_info:
            letter = _fill_patient_info(letter, patient_info)

        logger.info("Letter generated successfully")
        return letter

    except Exception as e:
        logger.error(f"LLM letter generation failed: {e}")
        # Return fallback letter
        return _generate_fallback_letter(parsed_audit_json, letter_tone, patient_info)


def _build_letter_prompt(audit: dict, tone: LetterTone) -> str:
    """
    Build the prompt for letter generation.

    Args:
        audit: Audit results dictionary.
        tone: Selected letter tone.

    Returns:
        str: Formatted prompt string.
    """
    # Format issues for prompt
    issues_text = _format_issues_for_prompt(audit.get("issues", []))

    prompt = LETTER_PROMPT_TEMPLATE.format(
        score=audit.get("score", "N/A"),
        total_issues=audit.get("total_issues", 0),
        potential_savings=audit.get("potential_savings", 0),
        issues_text=issues_text,
        tone_instructions=TONE_INSTRUCTIONS[tone],
    )

    return prompt


def _format_issues_for_prompt(issues: list) -> str:
    """
    Format issues list for inclusion in prompt.

    Args:
        issues: List of audit issues.

    Returns:
        str: Formatted issues text.
    """
    if not issues:
        return "No specific issues identified."

    lines = []
    for i, issue in enumerate(issues, 1):
        severity = issue.get("severity", "unknown").upper()
        issue_type = issue.get("type", "unknown").replace("_", " ").title()
        description = issue.get("description", "No description")
        amount = issue.get("amount_impact")

        line = f"{i}. [{severity}] {issue_type}: {description}"
        if amount:
            line += f" (Impact: ${amount:.2f})"

        lines.append(line)

    return "\n".join(lines)


def _clean_letter_response(response: str) -> str:
    """
    Clean up LLM response to extract just the letter.

    Args:
        response: Raw LLM response.

    Returns:
        str: Cleaned letter text.
    """
    # Remove common prefixes
    prefixes_to_remove = [
        "Here's the letter:",
        "Here is the letter:",
        "Below is the letter:",
        "The letter:",
    ]

    response = response.strip()

    for prefix in prefixes_to_remove:
        if response.lower().startswith(prefix.lower()):
            response = response[len(prefix):].strip()

    # Remove markdown formatting if present
    if response.startswith("```"):
        lines = response.split("\n")
        # Remove first and last ``` lines
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response = "\n".join(lines)

    return response.strip()


def _fill_patient_info(letter: str, patient_info: dict) -> str:
    """
    Replace placeholders with actual patient information.

    Args:
        letter: Letter text with placeholders.
        patient_info: Dictionary with patient details.

    Returns:
        str: Letter with filled information.
    """
    replacements = {
        "[PATIENT NAME]": patient_info.get("patient_name", "[PATIENT NAME]"),
        "[ACCOUNT NUMBER]": patient_info.get("account_number", "[ACCOUNT NUMBER]"),
        "[DATE OF SERVICE]": patient_info.get("date_of_service", "[DATE OF SERVICE]"),
        "[PROVIDER NAME]": patient_info.get("provider_name", "[PROVIDER NAME]"),
        "[PATIENT ADDRESS]": patient_info.get("patient_address", "[PATIENT ADDRESS]"),
        "[PATIENT PHONE]": patient_info.get("patient_phone", "[PATIENT PHONE]"),
        "[PATIENT EMAIL]": patient_info.get("patient_email", "[PATIENT EMAIL]"),
    }

    for placeholder, value in replacements.items():
        letter = letter.replace(placeholder, value)

    return letter


def _generate_no_issues_letter(audit: dict, tone: LetterTone) -> str:
    """
    Generate a letter when no issues are found.

    Args:
        audit: Audit results.
        tone: Letter tone.

    Returns:
        str: Acknowledgment letter.
    """
    today = datetime.now().strftime("%B %d, %Y")
    score = audit.get("score", 100)

    if tone == LetterTone.FORMAL:
        salutation = "Dear Sir/Madam,"
        closing = "Sincerely,"
    elif tone == LetterTone.FRIENDLY:
        salutation = "Hello,"
        closing = "Best regards,"
    else:  # assertive
        salutation = "To Whom It May Concern,"
        closing = "Regards,"

    letter = f"""{today}

[PROVIDER NAME]
[PROVIDER ADDRESS]

Re: Account Number [ACCOUNT NUMBER]
Patient: [PATIENT NAME]
Date of Service: [DATE OF SERVICE]

{salutation}

I am writing regarding the medical bill referenced above. After careful review of the charges, I have completed an audit of this statement.

I am pleased to confirm that the bill appears to be accurate, with an audit score of {score}/100. No significant discrepancies or issues were identified during this review.

Thank you for your accurate billing practices. If you have any questions regarding this correspondence, please do not hesitate to contact me.

{closing}

[PATIENT NAME]
[PATIENT ADDRESS]
[PATIENT PHONE]
[PATIENT EMAIL]
"""
    return letter


def _generate_fallback_letter(
    audit: dict,
    tone: LetterTone,
    patient_info: Optional[dict] = None,
) -> str:
    """
    Generate a fallback letter without LLM.

    Args:
        audit: Audit results.
        tone: Letter tone.
        patient_info: Optional patient information.

    Returns:
        str: Template-based letter.
    """
    logger.info("Generating fallback letter (no LLM)")

    today = datetime.now().strftime("%B %d, %Y")
    score = audit.get("score", 0)
    total_issues = audit.get("total_issues", 0)
    savings = audit.get("potential_savings", 0)
    issues = audit.get("issues", [])

    # Tone-specific elements
    if tone == LetterTone.FORMAL:
        salutation = "Dear Sir/Madam,"
        opening = "I am writing to formally dispute certain charges on the medical bill referenced above."
        closing = "Sincerely,"
        urgency = "I respectfully request a response within 30 days of receipt of this letter."
    elif tone == LetterTone.FRIENDLY:
        salutation = "Hello,"
        opening = "I hope this letter finds you well. I'm reaching out regarding some concerns I have about my recent medical bill."
        closing = "Thank you for your help!"
        urgency = "I would appreciate hearing back from you within the next 30 days so we can resolve this together."
    else:  # assertive
        salutation = "To Whom It May Concern,"
        opening = "I am writing to dispute the following charges on my medical bill, which I believe to be incorrect."
        closing = "Regards,"
        urgency = "I expect a written response within 30 days. If I do not receive a satisfactory resolution, I will escalate this matter to the appropriate regulatory authorities."

    # Format issues section
    issues_section = ""
    if issues:
        issues_section = "\nThe following issues were identified:\n\n"
        for i, issue in enumerate(issues, 1):
            severity = issue.get("severity", "unknown").upper()
            description = issue.get("description", "Issue identified")
            amount = issue.get("amount_impact")

            issues_section += f"{i}. {description}"
            if amount:
                issues_section += f" (Disputed amount: ${amount:.2f})"
            issues_section += "\n"

    # Build letter
    letter = f"""{today}

[PROVIDER NAME]
Billing Department
[PROVIDER ADDRESS]

Re: Billing Dispute
Account Number: [ACCOUNT NUMBER]
Patient: [PATIENT NAME]
Date of Service: [DATE OF SERVICE]

{salutation}

{opening}

After conducting a thorough audit of my bill (Score: {score}/100), I have identified {total_issues} issue(s) that require your attention. The potential overcharges total ${savings:.2f}.
{issues_section}
I am requesting the following actions:

1. A detailed, itemized breakdown of all charges
2. Correction of the identified errors
3. An adjusted bill reflecting the accurate amounts
4. Written confirmation of any adjustments made

{urgency}

Please send your response to:

[PATIENT NAME]
[PATIENT ADDRESS]
[PATIENT PHONE]
[PATIENT EMAIL]

{closing}

[PATIENT NAME]

Enclosures:
- Copy of original bill
- Audit report
"""

    # Fill patient info if provided
    if patient_info:
        letter = _fill_patient_info(letter, patient_info)

    return letter


def get_letter_template(tone: str) -> str:
    """
    Get a blank letter template for a given tone.

    Args:
        tone: Letter tone ("formal", "friendly", "assertive").

    Returns:
        str: Blank letter template.
    """
    try:
        letter_tone = LetterTone(tone.lower())
    except ValueError:
        letter_tone = LetterTone.FORMAL

    # Create minimal audit for template generation
    minimal_audit = {
        "score": 0,
        "total_issues": 0,
        "potential_savings": 0,
        "issues": [
            {
                "type": "example_issue",
                "severity": "high",
                "description": "[ISSUE DESCRIPTION]",
                "amount_impact": 0,
            }
        ],
    }

    return _generate_fallback_letter(minimal_audit, letter_tone)


def validate_tone(tone: str) -> bool:
    """
    Check if a tone value is valid.

    Args:
        tone: Tone string to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    try:
        LetterTone(tone.lower())
        return True
    except ValueError:
        return False


def get_available_tones() -> list[str]:
    """
    Get list of available tone options.

    Returns:
        list[str]: Available tone values.
    """
    return [t.value for t in LetterTone]

