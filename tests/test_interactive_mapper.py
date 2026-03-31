"""Tests for money_mapper.interactive_mapper module."""

import pytest

from money_mapper.interactive_mapper import (
    get_transaction_frequency,
    load_category_taxonomy,
    suggest_keyword,
    suggest_name,
)


class TestGetTransactionFrequency:
    """Test transaction frequency calculation."""

    def test_frequency_empty_transactions(self):
        """Test frequency with empty transaction list."""
        result = get_transaction_frequency([])
        assert result == {}

    def test_frequency_single_merchant(self):
        """Test frequency with single merchant."""
        transactions = [
            {"description": "STARBUCKS", "amount": 5.0},
            {"description": "STARBUCKS", "amount": 5.5},
        ]
        result = get_transaction_frequency(transactions)

        assert isinstance(result, dict)
        assert len(result) > 0

    def test_frequency_multiple_merchants(self):
        """Test frequency with multiple merchants."""
        transactions = [
            {"description": "STARBUCKS", "amount": 5.0},
            {"description": "AMAZON", "amount": 25.0},
            {"description": "STARBUCKS", "amount": 5.5},
            {"description": "WHOLE FOODS", "amount": 50.0},
        ]
        result = get_transaction_frequency(transactions)

        assert isinstance(result, dict)
        assert len(result) >= 1

    def test_frequency_returns_dict_with_counts(self):
        """Test that frequency returns dict with integer counts."""
        transactions = [
            {"description": "TEST", "amount": 10.0},
        ]
        result = get_transaction_frequency(transactions)

        for key, value in result.items():
            assert isinstance(value, int)
            assert value >= 1


class TestSuggestKeyword:
    """Test keyword suggestion functionality."""

    def test_suggest_keyword_basic(self):
        """Test keyword suggestion with basic description."""
        result = suggest_keyword("STARBUCKS COFFEE SEATTLE WA")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_suggest_keyword_empty_string(self):
        """Test keyword suggestion with empty string."""
        result = suggest_keyword("")
        assert isinstance(result, str)

    def test_suggest_keyword_single_word(self):
        """Test keyword suggestion with single word."""
        result = suggest_keyword("STARBUCKS")
        assert isinstance(result, str)

    def test_suggest_keyword_multiple_merchants(self):
        """Test keyword suggestion with various merchant names."""
        merchants = [
            "STARBUCKS",
            "AMAZON.COM",
            "WHOLE FOODS MARKET",
            "APPLE STORE",
        ]

        for merchant in merchants:
            result = suggest_keyword(merchant)
            assert isinstance(result, str)

    @pytest.mark.parametrize(
        "description",
        [
            "MERCHANT NAME HERE",
            "STORE #12345 LOCATION",
            "COMPANY WITH LONG NAME",
        ],
    )
    def test_suggest_keyword_various_formats(self, description):
        """Test keyword suggestion with various formats."""
        result = suggest_keyword(description)
        assert isinstance(result, str)


class TestSuggestName:
    """Test name suggestion functionality."""

    def test_suggest_name_basic(self):
        """Test name suggestion with basic description."""
        result = suggest_name("STARBUCKS COFFEE SEATTLE WA")
        assert isinstance(result, str)

    def test_suggest_name_empty_string(self):
        """Test name suggestion with empty string."""
        result = suggest_name("")
        assert isinstance(result, str)

    def test_suggest_name_single_word(self):
        """Test name suggestion with single word."""
        result = suggest_name("AMAZON")
        assert isinstance(result, str)

    def test_suggest_name_multiple_words(self):
        """Test name suggestion with multiple words."""
        result = suggest_name("WHOLE FOODS MARKET SEATTLE WASHINGTON")
        assert isinstance(result, str)

    @pytest.mark.parametrize(
        "description",
        [
            "STARBUCKS",
            "AMAZON.COM",
            "WHOLE FOODS",
            "APPLE STORE",
            "WALMART SUPERCENTER",
        ],
    )
    def test_suggest_name_merchants(self, description):
        """Test name suggestion for various merchants."""
        result = suggest_name(description)
        assert isinstance(result, str)


class TestLoadCategoryTaxonomy:
    """Test category taxonomy loading."""

    def test_load_taxonomy_returns_tuple(self):
        """Test that load_category_taxonomy returns tuple."""
        result = load_category_taxonomy()
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_taxonomy_first_element_is_dict(self):
        """Test that first element is dictionary."""
        categories, _, _ = load_category_taxonomy()
        assert isinstance(categories, dict)
        assert len(categories) > 0

    def test_taxonomy_second_element_is_dict(self):
        """Test that second element is dictionary."""
        _, descriptions, _ = load_category_taxonomy()
        assert isinstance(descriptions, dict)

    def test_taxonomy_third_element_is_dict(self):
        """Test that third element is dictionary."""
        _, _, scopes = load_category_taxonomy()
        assert isinstance(scopes, dict)

    def test_taxonomy_categories_have_content(self):
        """Test that categories are populated."""
        categories, _, _ = load_category_taxonomy()

        # Should have at least one category
        assert len(categories) > 0

        # Categories should have valid structure
        for category, subcats in categories.items():
            assert isinstance(category, str)
            assert isinstance(subcats, list)
            assert len(subcats) > 0

    def test_taxonomy_consistency(self):
        """Test that taxonomy loading is consistent."""
        result1 = load_category_taxonomy()
        result2 = load_category_taxonomy()

        # Should return same data on multiple calls
        assert result1[0] == result2[0]  # Categories
        assert result1[1] == result2[1]  # Descriptions


class TestInteractiveMapperImports:
    """Test interactive_mapper module imports."""

    def test_module_imports(self):
        """Test that module can be imported."""
        try:
            from money_mapper import interactive_mapper

            assert interactive_mapper is not None
        except ImportError:
            pytest.fail("Could not import interactive_mapper module")

    def test_all_functions_exist(self):
        """Test that all major functions exist."""
        from money_mapper import interactive_mapper

        required_functions = [
            "get_transaction_frequency",
            "suggest_keyword",
            "suggest_name",
            "load_category_taxonomy",
            "display_category_menu",
            "create_mapping_entry",
            "run_mapping_wizard",
        ]

        for func_name in required_functions:
            assert hasattr(interactive_mapper, func_name), f"Missing function: {func_name}"
            assert callable(getattr(interactive_mapper, func_name)), f"Not callable: {func_name}"


class TestInteractiveMapperIntegration:
    """Integration tests for interactive mapper."""

    def test_taxonomy_and_suggestion_workflow(self):
        """Test typical taxonomy and suggestion workflow."""
        # Load taxonomy
        categories, _, _ = load_category_taxonomy()
        assert len(categories) > 0

        # Suggest keyword
        keyword = suggest_keyword("STARBUCKS COFFEE")
        assert isinstance(keyword, str)

        # Suggest name
        name = suggest_name("STARBUCKS")
        assert isinstance(name, str)

    def test_frequency_and_suggestion_workflow(self):
        """Test frequency calculation with suggestion."""
        transactions = [
            {"description": "STARBUCKS", "amount": 5.0},
            {"description": "AMAZON", "amount": 25.0},
            {"description": "STARBUCKS", "amount": 5.5},
        ]

        # Get frequency
        frequency = get_transaction_frequency(transactions)
        assert isinstance(frequency, dict)

        # Suggest keywords for frequent merchants
        for merchant in frequency.keys():
            keyword = suggest_keyword(merchant)
            assert isinstance(keyword, str)

    def test_full_mapping_preparation(self):
        """Test full mapping preparation workflow."""
        # Load taxonomy
        categories, descriptions, scopes = load_category_taxonomy()

        # All should be populated
        assert len(categories) > 0
        assert len(descriptions) > 0
        assert isinstance(scopes, dict)

        # Suggest names
        name = suggest_name("TEST MERCHANT")
        assert isinstance(name, str)

        # Suggest keywords
        keyword = suggest_keyword("TEST MERCHANT")
        assert isinstance(keyword, str)

    @pytest.mark.parametrize(
        "description",
        [
            "STARBUCKS COFFEE",
            "AMAZON STORE",
            "WHOLE FOODS",
        ],
    )
    def test_suggestion_consistency(self, description):
        """Test that suggestions are consistent."""
        name1 = suggest_name(description)
        name2 = suggest_name(description)

        # Should return same suggestion
        assert name1 == name2

        keyword1 = suggest_keyword(description)
        keyword2 = suggest_keyword(description)

        # Should return same suggestion
        assert keyword1 == keyword2
