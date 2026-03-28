"""Tests for community contribution flow.

Tests GitHub CLI integration, merchant validation, PR generation, and branch management.
"""

import subprocess
from unittest.mock import MagicMock, patch

from money_mapper.community_flow import (
    check_gh_cli_available,
    create_community_pr,
    create_contribution_branch,
    format_mapping_entry,
    generate_pr_template,
    submit_community_contribution,
    validate_merchant_for_community,
)


class TestGhCliAvailability:
    """Test GitHub CLI availability checking."""

    @patch("subprocess.run")
    def test_gh_cli_available_when_installed(self, mock_run):
        """check_gh_cli_available() should return True when gh CLI is installed."""
        mock_run.return_value = MagicMock(returncode=0)
        assert check_gh_cli_available() is True

    @patch("subprocess.run")
    def test_gh_cli_missing_when_not_installed(self, mock_run):
        """check_gh_cli_available() should return False when gh CLI not found."""
        mock_run.side_effect = FileNotFoundError()
        assert check_gh_cli_available() is False

    @patch("subprocess.run")
    def test_gh_cli_version_check(self, mock_run):
        """Should verify gh CLI version is compatible."""
        mock_run.return_value = MagicMock(returncode=0)
        result = check_gh_cli_available()
        assert result is True
        mock_run.assert_called_once()


class TestMerchantValidation:
    """Test merchant validation against privacy audit standards."""

    @patch("money_mapper.community_flow.audit_merchant_name")
    def test_merchant_passes_clean_validation(self, mock_audit):
        """validate_merchant_for_community() should pass safe merchant names."""
        mock_audit.return_value = {"score": 10, "findings": [], "risk_level": "low"}
        result = validate_merchant_for_community("Starbucks")
        assert result["passed"] is True
        assert result["score"] == 10

    @patch("money_mapper.community_flow.audit_merchant_name")
    def test_merchant_fails_with_pii_keywords(self, mock_audit):
        """Should reject merchants with PII keywords."""
        mock_audit.return_value = {
            "score": 50,
            "findings": [{"reason": "Contains email"}],
            "risk_level": "medium",
        }
        result = validate_merchant_for_community("john@example.com")
        assert result["passed"] is False

    @patch("money_mapper.community_flow.audit_merchant_name")
    def test_merchant_score_below_threshold(self, mock_audit):
        """Should accept merchants with risk score below 30."""
        mock_audit.return_value = {"score": 25, "findings": [], "risk_level": "low"}
        result = validate_merchant_for_community("SafeStore")
        assert result["passed"] is True

    @patch("money_mapper.community_flow.audit_merchant_name")
    def test_merchant_score_above_threshold(self, mock_audit):
        """Should reject merchants with risk score >= 30."""
        mock_audit.return_value = {
            "score": 30,
            "findings": [{"reason": "risk"}],
            "risk_level": "medium",
        }
        result = validate_merchant_for_community("RiskyMerchant")
        assert result["passed"] is False

    def test_validation_returns_detailed_result(self):
        """Result should include score, passed, and issues list."""
        with patch("money_mapper.community_flow.audit_merchant_name") as mock_audit:
            mock_audit.return_value = {"score": 15, "findings": [], "risk_level": "low"}
            result = validate_merchant_for_community("Test")
            assert "passed" in result
            assert "score" in result
            assert "issues" in result


class TestMappingFormatting:
    """Test TOML mapping entry formatting."""

    def test_format_mapping_basic(self):
        """format_mapping_entry() should create valid TOML entry."""
        result = format_mapping_entry("Starbucks", "Coffee", "transaction")
        assert "Starbucks" in result
        assert "Coffee" in result
        assert "transaction" in result

    def test_format_mapping_with_special_chars(self):
        """Should escape special characters in merchant name."""
        result = format_mapping_entry('Store "Name"', "Shopping", "user")
        assert '\\"' in result  # Should be escaped

    def test_format_mapping_preserves_category(self):
        """Formatted entry should preserve category exactly."""
        result = format_mapping_entry("Test", "My Category", "source")
        assert 'category = "My Category"' in result

    def test_format_mapping_includes_source(self):
        """Formatted entry should include source field."""
        result = format_mapping_entry("Test", "Cat", "test_source")
        assert "test_source" in result

    def test_format_mapping_valid_toml(self):
        """Output should be valid TOML syntax."""
        result = format_mapping_entry("Shop", "Shopping", "manual")
        assert result.count("=") >= 2  # At least key=value and category=value
        assert "{" in result and "}" in result


class TestPRTemplateGeneration:
    """Test PR template creation."""

    def test_pr_template_title_generated(self):
        """generate_pr_template() should create PR title."""
        result = generate_pr_template("Starbucks", "Coffee", "transaction")
        assert "title" in result
        assert "Starbucks" in result["title"]
        assert "Coffee" in result["title"]

    def test_pr_template_body_formatted(self):
        """PR body should include merchant details."""
        result = generate_pr_template("TestShop", "Shopping", "source")
        assert "body" in result
        assert "TestShop" in result["body"]
        assert "Shopping" in result["body"]

    def test_pr_template_branch_name(self):
        """PR template should include feature branch name."""
        result = generate_pr_template("Test", "Cat", "src")
        assert "branch" in result
        assert "feature/merchant-contributions" in result["branch"]

    def test_pr_template_with_special_chars(self):
        """Should handle special characters in merchant names."""
        result = generate_pr_template('Store "Name"', "Category", "source")
        assert result["branch"] is not None
        assert len(result["title"]) > 0

    def test_pr_template_includes_checklist(self):
        """PR body should include verification checklist."""
        result = generate_pr_template("Test", "Cat", "src")
        assert "Checklist" in result["body"] or "checklist" in result["body"]


class TestContributionBranch:
    """Test branch creation for contributions."""

    @patch("subprocess.run")
    def test_create_branch_success(self, mock_run):
        """create_contribution_branch() should create git branch successfully."""
        mock_run.return_value = MagicMock(returncode=0)
        result = create_contribution_branch("feature/test-123")
        assert result is True

    @patch("subprocess.run")
    def test_create_branch_follows_naming_convention(self, mock_run):
        """Branch name should follow feature/merchant-contributions-<timestamp> format."""
        mock_run.return_value = MagicMock(returncode=0)
        result = create_contribution_branch("feature/merchant-contributions-20260328_120000")
        assert result is True
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_create_branch_with_existing_branch(self, mock_run):
        """Should handle case where branch already exists."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        result = create_contribution_branch("feature/existing-branch")
        assert result is False

    def test_create_branch_timestamp_format(self):
        """Timestamp in branch name should be valid format."""
        template = generate_pr_template("Test", "Cat", "src")
        branch = template["branch"]
        # Should have timestamp format YYYYMMDD_HHMMSS
        assert "_" in branch
        parts = branch.split("-")
        timestamp = parts[-1]
        assert len(timestamp) == 15  # YYYYMMDD_HHMMSS


class TestCommunityPRCreation:
    """Test GitHub PR creation integration."""

    @patch("money_mapper.community_flow.subprocess.run")
    @patch("money_mapper.community_flow.check_gh_cli_available")
    def test_create_pr_success(self, mock_available, mock_run):
        """create_community_pr() should successfully create PR."""
        mock_available.return_value = True
        mock_run.return_value = MagicMock(stdout="https://github.com/user/repo/pull/1\n")
        template = {"title": "Test", "body": "Body"}
        result = create_community_pr(template)
        assert result is not None

    @patch("money_mapper.community_flow.subprocess.run")
    @patch("money_mapper.community_flow.check_gh_cli_available")
    def test_create_pr_with_full_template(self, mock_available, mock_run):
        """Should create PR with complete template data."""
        mock_available.return_value = True
        mock_run.return_value = MagicMock(stdout="https://github.com/user/repo/pull/2\n")
        template = generate_pr_template("Test", "Cat", "src")
        result = create_community_pr(template)
        assert result is not None

    @patch("money_mapper.community_flow.subprocess.run")
    @patch("money_mapper.community_flow.check_gh_cli_available")
    def test_create_pr_returns_pr_url(self, mock_available, mock_run):
        """Should return the created PR's URL."""
        mock_available.return_value = True
        mock_run.return_value = MagicMock(stdout="https://github.com/user/repo/pull/123\n")
        result = create_community_pr({"title": "T", "body": "B"})
        assert result is not None
        assert result.startswith("https://github.com/")

    @patch("money_mapper.community_flow.check_gh_cli_available")
    def test_create_pr_handles_missing_gh(self, mock_available):
        """Should return None if gh CLI not available."""
        mock_available.return_value = False
        result = create_community_pr({"title": "T", "body": "B"})
        assert result is None

    @patch("money_mapper.community_flow.subprocess.run")
    @patch("money_mapper.community_flow.check_gh_cli_available")
    def test_create_pr_handles_git_error(self, mock_available, mock_run):
        """Should handle git command failures gracefully."""
        mock_available.return_value = True
        mock_run.side_effect = subprocess.CalledProcessError(1, "gh")
        result = create_community_pr({"title": "T", "body": "B"})
        assert result is None

    @patch("money_mapper.community_flow.subprocess.run")
    @patch("money_mapper.community_flow.check_gh_cli_available")
    def test_create_pr_sets_labels(self, mock_available, mock_run):
        """Should set 'community-contribution' label on PR."""
        mock_available.return_value = True
        mock_run.return_value = MagicMock(stdout="https://pr\n")
        create_community_pr({"title": "T", "body": "B"})
        # Verify label was included in call
        call_args = mock_run.call_args[0][0]
        assert "community-contribution" in call_args


class TestIntegrationWithPrivacyAudit:
    """Test integration with privacy audit system."""

    @patch("money_mapper.community_flow.audit_merchant_name")
    def test_validates_against_privacy_audit(self, mock_audit):
        """Should use privacy_audit module for validation."""
        mock_audit.return_value = {"score": 0, "findings": [], "risk_level": "low"}
        validate_merchant_for_community("Test")
        mock_audit.assert_called_once()

    @patch("money_mapper.community_flow.audit_merchant_name")
    def test_only_safe_merchants_allowed(self, mock_audit):
        """Only merchants passing privacy audit should be allowed."""
        mock_audit.return_value = {
            "score": 50,
            "findings": [{"reason": "risk"}],
            "risk_level": "medium",
        }
        result = validate_merchant_for_community("Unsafe")
        assert result["passed"] is False

    def test_audit_failure_provides_reason(self):
        """When validation fails, should explain why."""
        with patch("money_mapper.community_flow.audit_merchant_name") as mock_audit:
            mock_audit.return_value = {
                "score": 40,
                "findings": [{"reason": "Contains email"}],
                "risk_level": "medium",
            }
            result = validate_merchant_for_community("Test")
            assert len(result["issues"]) > 0


class TestEndToEndFlow:
    """Test complete community contribution workflow."""

    @patch("money_mapper.community_flow.create_community_pr")
    @patch("money_mapper.community_flow.create_contribution_branch")
    @patch("money_mapper.community_flow.check_gh_cli_available")
    @patch("money_mapper.community_flow.audit_merchant_name")
    def test_full_workflow_happy_path(self, mock_audit, mock_gh, mock_branch, mock_pr):
        """Complete flow from validation to PR creation should work."""
        mock_audit.return_value = {"score": 0, "findings": [], "risk_level": "low"}
        mock_gh.return_value = True
        mock_branch.return_value = True
        mock_pr.return_value = "https://pr"

        result = submit_community_contribution("Test", "Category", "source")
        assert result["success"] is True

    @patch("money_mapper.community_flow.audit_merchant_name")
    def test_workflow_stops_on_validation_failure(self, mock_audit):
        """Should not create PR if merchant fails validation."""
        mock_audit.return_value = {
            "score": 50,
            "findings": [{"reason": "risk"}],
            "risk_level": "medium",
        }
        result = submit_community_contribution("Unsafe", "Cat", "src")
        assert result["success"] is False

    @patch("money_mapper.community_flow.check_gh_cli_available")
    @patch("money_mapper.community_flow.audit_merchant_name")
    def test_workflow_requires_gh_cli(self, mock_audit, mock_gh):
        """Complete flow should require gh CLI available."""
        mock_audit.return_value = {"score": 0, "findings": [], "risk_level": "low"}
        mock_gh.return_value = False
        result = submit_community_contribution("Test", "Cat", "src")
        assert result["success"] is False

    @patch("money_mapper.community_flow.create_community_pr")
    @patch("money_mapper.community_flow.create_contribution_branch")
    @patch("money_mapper.community_flow.check_gh_cli_available")
    @patch("money_mapper.community_flow.audit_merchant_name")
    def test_workflow_creates_feature_branch(self, mock_audit, mock_gh, mock_branch, mock_pr):
        """Workflow should create feature branch with proper name."""
        mock_audit.return_value = {"score": 0, "findings": [], "risk_level": "low"}
        mock_gh.return_value = True
        mock_branch.return_value = True
        mock_pr.return_value = "https://pr"
        submit_community_contribution("Test", "Cat", "src")
        mock_branch.assert_called_once()

    @patch("money_mapper.community_flow.create_community_pr")
    @patch("money_mapper.community_flow.create_contribution_branch")
    @patch("money_mapper.community_flow.check_gh_cli_available")
    @patch("money_mapper.community_flow.audit_merchant_name")
    def test_workflow_generates_proper_pr(self, mock_audit, mock_gh, mock_branch, mock_pr):
        """Final PR should have all required information."""
        mock_audit.return_value = {"score": 0, "findings": [], "risk_level": "low"}
        mock_gh.return_value = True
        mock_branch.return_value = True
        mock_pr.return_value = "https://github.com/user/repo/pull/1"
        result = submit_community_contribution("TestMerchant", "Category", "source")
        assert result["pr_url"] == "https://github.com/user/repo/pull/1"
