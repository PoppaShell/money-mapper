"""Tests for money_mapper.mapping_validator module."""

from money_mapper.mapping_validator import (
    check_required_files,
    validate_mapping_structure,
    validate_mappings,
    validate_single_mapping,
)


class TestValidateMappings:
    """Test mapping validation."""

    def test_validate_mappings_basic(self):
        """Test basic validation of mappings."""
        mappings = {
            "FOOD_AND_DRINK": {
                "starbucks": {
                    "name": "Starbucks",
                    "category": "FOOD_AND_DRINK",
                    "subcategory": "FOOD_AND_DRINK_COFFEE",
                    "scope": "public",
                }
            }
        }

        issues = validate_mappings(mappings)

        assert isinstance(issues, list)

    def test_validate_mappings_empty(self):
        """Test validation of empty mappings."""
        mappings = {}

        issues = validate_mappings(mappings)

        assert issues == []

    def test_validate_mappings_missing_scope(self):
        """Test validation detects missing scope field."""
        mappings = {
            "FOOD_AND_DRINK": {
                "starbucks": {
                    "name": "Starbucks",
                    "category": "FOOD_AND_DRINK",
                    "subcategory": "FOOD_AND_DRINK_COFFEE",
                }
            }
        }

        issues = validate_mappings(mappings)

        # Should find missing scope
        assert len(issues) > 0

    def test_validate_mappings_invalid_category(self):
        """Test validation detects invalid categories."""
        mappings = {
            "FOOD_AND_DRINK": {
                "starbucks": {
                    "name": "Starbucks",
                    "category": "INVALID_CATEGORY",
                    "subcategory": "FOOD_AND_DRINK_COFFEE",
                    "scope": "public",
                }
            }
        }

        issues = validate_mappings(mappings)

        # Should find invalid category
        assert any("category" in str(issue).lower() for issue in issues)

    def test_validate_mappings_invalid_scope(self):
        """Test validation detects invalid scope values."""
        mappings = {
            "FOOD_AND_DRINK": {
                "starbucks": {
                    "name": "Starbucks",
                    "category": "FOOD_AND_DRINK",
                    "subcategory": "FOOD_AND_DRINK_COFFEE",
                    "scope": "invalid",
                }
            }
        }

        issues = validate_mappings(mappings)

        # Should find invalid scope
        assert any("scope" in str(issue).lower() for issue in issues)

    def test_validate_mappings_multiple_issues(self):
        """Test validation finds multiple issues."""
        mappings = {
            "FOOD_AND_DRINK": {
                "starbucks": {
                    "name": "Starbucks",
                    "category": "INVALID_CAT",
                    "subcategory": "INVALID_SUB",
                    # Missing scope
                }
            }
        }

        issues = validate_mappings(mappings)

        assert len(issues) > 1


class TestValidateSingleMapping:
    """Test single mapping validation."""

    def test_validate_single_mapping_valid(self):
        """Test validation of a valid mapping."""
        mapping = {
            "name": "Starbucks",
            "category": "FOOD_AND_DRINK",
            "subcategory": "FOOD_AND_DRINK_COFFEE",
            "scope": "public",
        }

        issues = validate_single_mapping("starbucks", mapping)

        assert issues == []

    def test_validate_single_mapping_missing_name(self):
        """Test validation detects missing name."""
        mapping = {
            "category": "FOOD_AND_DRINK",
            "subcategory": "FOOD_AND_DRINK_COFFEE",
            "scope": "public",
        }

        issues = validate_single_mapping("starbucks", mapping)

        assert any("name" in issue.lower() for issue in issues)

    def test_validate_single_mapping_missing_category(self):
        """Test validation detects missing category."""
        mapping = {"name": "Starbucks", "subcategory": "FOOD_AND_DRINK_COFFEE", "scope": "public"}

        issues = validate_single_mapping("starbucks", mapping)

        assert any("category" in issue.lower() for issue in issues)

    def test_validate_single_mapping_missing_subcategory(self):
        """Test validation detects missing subcategory."""
        mapping = {"name": "Starbucks", "category": "FOOD_AND_DRINK", "scope": "public"}

        issues = validate_single_mapping("starbucks", mapping)

        assert any("subcategory" in issue.lower() for issue in issues)

    def test_validate_single_mapping_missing_scope(self):
        """Test validation detects missing scope."""
        mapping = {
            "name": "Starbucks",
            "category": "FOOD_AND_DRINK",
            "subcategory": "FOOD_AND_DRINK_COFFEE",
        }

        issues = validate_single_mapping("starbucks", mapping)

        assert any("scope" in issue.lower() for issue in issues)

    def test_validate_single_mapping_invalid_scope(self):
        """Test validation detects invalid scope value."""
        mapping = {
            "name": "Starbucks",
            "category": "FOOD_AND_DRINK",
            "subcategory": "FOOD_AND_DRINK_COFFEE",
            "scope": "invalid_scope",
        }

        issues = validate_single_mapping("starbucks", mapping)

        assert any("scope" in issue.lower() for issue in issues)

    def test_validate_single_mapping_invalid_category(self):
        """Test validation detects invalid category."""
        mapping = {
            "name": "Starbucks",
            "category": "INVALID_CATEGORY",
            "subcategory": "FOOD_AND_DRINK_COFFEE",
            "scope": "public",
        }

        issues = validate_single_mapping("starbucks", mapping)

        assert any("category" in issue.lower() for issue in issues)


class TestCheckRequiredFiles:
    """Test checking for required mapping files."""

    def test_check_required_files_exists(self, tmp_path):
        """Test checking when all required files exist."""
        # Create temp files
        private_file = tmp_path / "private_mappings.toml"
        public_file = tmp_path / "public_mappings.toml"
        private_file.write_text("")
        public_file.write_text("")

        result = check_required_files(str(private_file), str(public_file))

        assert result is True

    def test_check_required_files_missing_private(self, tmp_path):
        """Test checking when private file is missing."""
        private_file = tmp_path / "private_mappings.toml"
        public_file = tmp_path / "public_mappings.toml"
        public_file.write_text("")

        result = check_required_files(str(private_file), str(public_file))

        assert result is False

    def test_check_required_files_missing_public(self, tmp_path):
        """Test checking when public file is missing."""
        private_file = tmp_path / "private_mappings.toml"
        public_file = tmp_path / "public_mappings.toml"
        private_file.write_text("")

        result = check_required_files(str(private_file), str(public_file))

        assert result is False

    def test_check_required_files_both_missing(self):
        """Test checking when both files are missing."""
        result = check_required_files("/nonexistent/private.toml", "/nonexistent/public.toml")

        assert result is False


class TestValidateMappingStructure:
    """Test validation of mapping structure."""

    def test_validate_mapping_structure_valid(self):
        """Test validation of valid structure."""
        mappings = {
            "FOOD_AND_DRINK": {
                "starbucks": {
                    "name": "Starbucks",
                    "category": "FOOD_AND_DRINK",
                    "subcategory": "FOOD_AND_DRINK_COFFEE",
                    "scope": "public",
                }
            }
        }

        issues = validate_mapping_structure(mappings)

        assert isinstance(issues, list)

    def test_validate_mapping_structure_not_dict(self):
        """Test validation with non-dict structure."""
        result = validate_mapping_structure("not a dict")

        assert isinstance(result, list)
        assert len(result) > 0

    def test_validate_mapping_structure_with_invalid_nested_mapping(self):
        """Test validation with invalid nested mapping."""
        mappings = {"FOOD_AND_DRINK": {"starbucks": "not a dict"}}

        issues = validate_mapping_structure(mappings)

        assert len(issues) > 0

    def test_validate_mapping_structure_empty(self):
        """Test validation of empty structure."""
        mappings = {}

        issues = validate_mapping_structure(mappings)

        assert issues == []


class TestValidatorIntegration:
    """Integration tests for mapping validator."""

    def test_validator_full_workflow(self, tmp_path):
        """Test complete validation workflow."""
        # Create test files
        private_file = tmp_path / "private_mappings.toml"
        public_file = tmp_path / "public_mappings.toml"

        private_file.write_text("")
        public_file.write_text("")

        # Check files exist
        files_exist = check_required_files(str(private_file), str(public_file))
        assert files_exist is True

        # Validate structure
        mappings = {
            "FOOD_AND_DRINK": {
                "starbucks": {
                    "name": "Starbucks",
                    "category": "FOOD_AND_DRINK",
                    "subcategory": "FOOD_AND_DRINK_COFFEE",
                    "scope": "public",
                }
            }
        }

        issues = validate_mappings(mappings)
        assert len(issues) == 0

    def test_validator_complex_mappings(self):
        """Test validation of complex mapping set."""
        mappings = {
            "FOOD_AND_DRINK": {
                "starbucks*": {
                    "name": "Starbucks",
                    "category": "FOOD_AND_DRINK",
                    "subcategory": "FOOD_AND_DRINK_COFFEE",
                    "scope": "public",
                },
                "mcdonalds*": {
                    "name": "McDonald's",
                    "category": "FOOD_AND_DRINK",
                    "subcategory": "FOOD_AND_DRINK_FAST_FOOD",
                    "scope": "public",
                },
            },
            "TRANSPORTATION": {
                "shell*gas": {
                    "name": "Shell",
                    "category": "TRANSPORTATION",
                    "subcategory": "TRANSPORTATION_GAS",
                    "scope": "public",
                }
            },
        }

        issues = validate_mappings(mappings)

        assert len(issues) == 0
