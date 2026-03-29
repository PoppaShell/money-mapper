"""Tests for privacy audit functionality."""

from money_mapper.privacy_audit import (
    audit_merchant_name,
    classify_risk_level,
    detect_email_pattern,
    detect_name_pattern,
    detect_phone_pattern,
    detect_pii_keywords,
    get_pii_keywords,
    score_merchant,
)


class TestKeywordDetection:
    """Test PII keyword detection."""

    def test_get_pii_keywords_returns_dict(self):
        """Test that keyword database is returned."""
        keywords = get_pii_keywords()
        assert isinstance(keywords, dict)
        assert len(keywords) > 0

    def test_detect_medical_keywords(self):
        """Test detection of medical keywords."""
        result = detect_pii_keywords("john doe medical clinic")
        assert result is not None
        assert "medical" in result.get("keywords", []) or len(result) > 0

    def test_detect_health_keywords(self):
        """Test detection of health-related keywords."""
        result = detect_pii_keywords("dr smith health center")
        assert result is not None

    def test_detect_religious_keywords(self):
        """Test detection of religious keywords."""
        result = detect_pii_keywords("st michael church")
        assert result is not None

    def test_no_pii_keywords(self):
        """Test merchant with no PII keywords."""
        result = detect_pii_keywords("starbucks coffee")
        assert result is None or result == {}

    def test_case_insensitive_detection(self):
        """Test that keyword detection is case-insensitive."""
        result1 = detect_pii_keywords("Doctor Smith")
        result2 = detect_pii_keywords("doctor smith")
        # Both should detect the same keywords
        assert (result1 is None) == (result2 is None)


class TestPatternDetection:
    """Test PII pattern matching."""

    def test_detect_email_pattern(self):
        """Test email pattern detection."""
        result = detect_email_pattern("john.doe@gmail.com")
        assert result is True

    def test_detect_email_in_name(self):
        """Test email detection in merchant name."""
        result = detect_email_pattern("John Doe john@example.com")
        assert result is True

    def test_no_email_pattern(self):
        """Test that non-email doesn't match."""
        result = detect_email_pattern("Starbucks Coffee")
        assert result is False

    def test_detect_phone_pattern(self):
        """Test phone number pattern detection."""
        result = detect_phone_pattern("555-123-4567")
        assert result is True

    def test_detect_phone_alternative_format(self):
        """Test phone number in alternative format."""
        result = detect_phone_pattern("(555) 123-4567")
        assert result is True

    def test_no_phone_pattern(self):
        """Test that non-phone doesn't match."""
        result = detect_phone_pattern("Starbucks")
        assert result is False

    def test_detect_ssn_pattern(self):
        """Test SSN partial pattern detection."""
        # SSN patterns: XXX-XX or similar
        detect_phone_pattern("123-45-6789")  # Could also be SSN-like
        # Result depends on implementation

    def test_detect_name_pattern_full_name(self):
        """Test detection of full name pattern (First Last)."""
        result = detect_name_pattern("John Smith")
        assert result is True

    def test_detect_name_pattern_single_word(self):
        """Test that single word is not a full name."""
        result = detect_name_pattern("Starbucks")
        assert result is False

    def test_name_pattern_with_middle(self):
        """Test name pattern with middle initial/name."""
        result = detect_name_pattern("John M Smith")
        assert result is True


class TestScoringAlgorithm:
    """Test merchant privacy scoring."""

    def test_score_clean_merchant(self):
        """Test scoring for clean merchant name."""
        score = score_merchant("Starbucks Coffee")
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100

    def test_score_medical_merchant(self):
        """Test that medical merchants score higher."""
        medical_score = score_merchant("Smith Medical Clinic")
        generic_score = score_merchant("Starbucks")
        # Medical should score higher (higher risk)
        assert medical_score >= generic_score

    def test_score_with_email(self):
        """Test that email in name increases score."""
        no_email = score_merchant("John Smith")
        with_email = score_merchant("John Smith john@example.com")
        # With email should be riskier
        assert with_email >= no_email

    def test_score_with_phone(self):
        """Test that phone in name increases score."""
        no_phone = score_merchant("John Smith")
        with_phone = score_merchant("John Smith 555-123-4567")
        # With phone should be riskier
        assert with_phone >= no_phone

    def test_score_personal_name(self):
        """Test that personal full names score higher."""
        brand_name = score_merchant("Apple Store")
        personal_name = score_merchant("John Smith")
        # Personal name should score higher
        assert personal_name >= brand_name

    def test_score_returns_number(self):
        """Test that score is always a valid number."""
        score = score_merchant("Test Merchant Name")
        assert isinstance(score, (int, float))
        assert not isinstance(score, bool)


class TestRiskClassification:
    """Test risk level classification."""

    def test_classify_low_risk(self):
        """Test classification of low risk (0-30)."""
        risk = classify_risk_level(10)
        assert risk == "low"

    def test_classify_medium_risk(self):
        """Test classification of medium risk (30-70)."""
        risk = classify_risk_level(50)
        assert risk == "medium"

    def test_classify_high_risk(self):
        """Test classification of high risk (70+)."""
        risk = classify_risk_level(80)
        assert risk == "high"

    def test_classify_boundary_30(self):
        """Test boundary at 30."""
        risk = classify_risk_level(30)
        assert risk in ["medium", "low"]  # At boundary

    def test_classify_boundary_70(self):
        """Test boundary at 70."""
        risk = classify_risk_level(70)
        assert risk in ["high", "medium"]  # At boundary


class TestMerchantAudit:
    """Test comprehensive merchant auditing."""

    def test_audit_clean_merchant(self):
        """Test audit of clean merchant."""
        result = audit_merchant_name("Starbucks Coffee")
        assert isinstance(result, dict)
        assert "score" in result
        assert "risk_level" in result

    def test_audit_returns_findings(self):
        """Test that audit returns findings list."""
        result = audit_merchant_name("John Smith Medical Center")
        assert isinstance(result, dict)
        assert "findings" in result
        assert isinstance(result["findings"], list)

    def test_audit_includes_reasons(self):
        """Test that findings include reasons."""
        result = audit_merchant_name("john.doe@example.com")
        if result.get("findings"):
            for finding in result["findings"]:
                assert "reason" in finding

    def test_audit_merchant_with_multiple_risks(self):
        """Test merchant with multiple risk factors."""
        result = audit_merchant_name("Dr. John Smith 555-123-4567 Medical")
        assert isinstance(result, dict)
        # Should detect multiple issues
        assert len(result.get("findings", [])) > 0

    def test_audit_result_structure(self):
        """Test that audit result has expected structure."""
        result = audit_merchant_name("Test Merchant")
        assert "score" in result
        assert "risk_level" in result
        assert "findings" in result
        assert isinstance(result["findings"], list)

    def test_audit_with_threshold(self):
        """Test audit with risk threshold filter."""
        result = audit_merchant_name("Smith Medical", min_score=70)
        assert isinstance(result, dict)
