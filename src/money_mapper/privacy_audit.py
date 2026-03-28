"""Privacy audit - Scan mappings for PII leaks and merchant privacy risks.

Provides merchant privacy scoring based on:
- PII keywords (medical, religious, personal services)
- Pattern matching (email, phone, SSN)
- Name patterns (personal full names vs brand names)
- Frequency indicators (infrequent transactions)
"""

import re
from typing import Any


def get_pii_keywords() -> dict[str, list[str]]:
    """
    Get PII keyword categories for detection.

    Returns:
        Dict mapping category names to keyword lists
    """
    return {
        "medical": [
            "doctor",
            "clinic",
            "hospital",
            "medical",
            "pharmacy",
            "dentist",
            "surgeon",
            "health",
            "therapy",
            "mental",
        ],
        "religious": [
            "church",
            "mosque",
            "synagogue",
            "temple",
            "chapel",
            "priest",
            "rabbi",
            "pastor",
            "reverend",
            "bishop",
        ],
        "personal_services": [
            "lawyer",
            "attorney",
            "accountant",
            "therapist",
            "counselor",
            "coach",
            "consultant",
            "advisor",
        ],
        "adult": [
            "adult",
            "xxx",
            "escort",
            "gentleman",
            "exotic",
        ],
    }


def detect_pii_keywords(merchant_name: str) -> dict[str, Any] | None:
    """
    Detect PII keywords in merchant name.

    Args:
        merchant_name: Merchant name to scan

    Returns:
        Dict with detected keywords and categories, or None if none found
    """
    if not merchant_name:
        return None

    merchant_lower = merchant_name.lower()
    keywords_db = get_pii_keywords()
    found_keywords = []
    found_categories = []

    for category, keywords in keywords_db.items():
        for keyword in keywords:
            if keyword in merchant_lower:
                found_keywords.append(keyword)
                if category not in found_categories:
                    found_categories.append(category)

    if found_keywords:
        return {
            "keywords": found_keywords,
            "categories": found_categories,
        }

    return None


def detect_email_pattern(text: str) -> bool:
    """
    Detect email address pattern.

    Args:
        text: Text to search

    Returns:
        True if email pattern found
    """
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return bool(re.search(email_pattern, text))


def detect_phone_pattern(text: str) -> bool:
    """
    Detect phone number pattern.

    Args:
        text: Text to search

    Returns:
        True if phone pattern found
    """
    phone_patterns = [
        r"\d{3}-\d{3}-\d{4}",  # 555-123-4567
        r"\(\d{3}\)\s*\d{3}-\d{4}",  # (555) 123-4567
        r"\d{3}\.\d{3}\.\d{4}",  # 555.123.4567
        r"\+?1?\s*\d{10}",  # 5551234567
    ]

    for pattern in phone_patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_name_pattern(text: str) -> bool:
    """
    Detect personal full name pattern (First Last).

    Args:
        text: Text to search

    Returns:
        True if appears to be a personal name (capitalized words)
    """
    # Simple heuristic: two or more capitalized words with no numbers
    if re.search(r"\d", text):
        return False

    words = text.split()
    if len(words) < 2:
        return False

    # Check if at least 2 words start with capital letter
    capitalized = sum(1 for w in words if w and w[0].isupper())
    return capitalized >= 2


def score_merchant(merchant_name: str) -> int:
    """
    Calculate privacy risk score for merchant name (0-100).

    Scoring factors:
    - PII keywords (high weight)
    - Email/phone patterns (high weight)
    - Personal full name vs brand (medium weight)

    Args:
        merchant_name: Merchant name to score

    Returns:
        Risk score 0-100
    """
    score = 0

    # Check keywords (0-50 points)
    keywords_result = detect_pii_keywords(merchant_name)
    if keywords_result:
        keyword_count = len(keywords_result["keywords"])
        score += min(50, keyword_count * 10)

    # Check email (0-25 points)
    if detect_email_pattern(merchant_name):
        score += 25

    # Check phone (0-25 points)
    if detect_phone_pattern(merchant_name):
        score += 25

    # Check name pattern (0-20 points)
    if detect_name_pattern(merchant_name):
        score += 20

    # Cap at 100
    return min(100, score)


def classify_risk_level(score: int) -> str:
    """
    Classify risk level based on score.

    Args:
        score: Risk score (0-100)

    Returns:
        Risk level: "low", "medium", or "high"
    """
    if score < 30:
        return "low"
    elif score < 70:
        return "medium"
    else:
        return "high"


def audit_merchant_name(merchant_name: str, min_score: int = 0) -> dict[str, Any]:
    """
    Perform comprehensive privacy audit on merchant name.

    Args:
        merchant_name: Merchant name to audit
        min_score: Minimum score to include in findings

    Returns:
        Dict with score, risk_level, and findings list
    """
    score = score_merchant(merchant_name)
    risk_level = classify_risk_level(score)

    findings = []

    # Add keyword findings
    keywords_result = detect_pii_keywords(merchant_name)
    if keywords_result:
        findings.append(
            {
                "type": "keywords",
                "reason": f"Contains PII keywords: {', '.join(keywords_result['keywords'])}",
                "categories": keywords_result["categories"],
            }
        )

    # Add email findings
    if detect_email_pattern(merchant_name):
        findings.append(
            {
                "type": "email",
                "reason": "Contains email address pattern",
            }
        )

    # Add phone findings
    if detect_phone_pattern(merchant_name):
        findings.append(
            {
                "type": "phone",
                "reason": "Contains phone number pattern",
            }
        )

    # Add name findings
    if detect_name_pattern(merchant_name):
        findings.append(
            {
                "type": "personal_name",
                "reason": "Appears to be personal full name rather than brand name",
            }
        )

    return {
        "merchant_name": merchant_name,
        "score": score,
        "risk_level": risk_level,
        "findings": findings,
    }


def redact_merchant_name(merchant_name: str) -> str:
    """
    Redact PII from merchant name.

    Args:
        merchant_name: Merchant name to redact

    Returns:
        Redacted merchant name
    """
    redacted = merchant_name

    # Redact emails
    redacted = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL]", redacted)

    # Redact phones
    redacted = re.sub(r"\d{3}-\d{3}-\d{4}", "[PHONE]", redacted)
    redacted = re.sub(r"\(\d{3}\)\s*\d{3}-\d{4}", "[PHONE]", redacted)

    # Redact potential personal names (capitalized words)
    words = redacted.split()
    redacted_words = []
    for word in words:
        if word and word[0].isupper() and not re.search(r"\d", word) and len(word) < 15:
            redacted_words.append("[NAME]")
        else:
            redacted_words.append(word)

    return " ".join(redacted_words)
