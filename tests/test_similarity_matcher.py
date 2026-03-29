"""Tests for similarity-based merchant matching."""

import tempfile
from pathlib import Path

import numpy as np

from money_mapper.similarity_matcher import (
    calculate_similarity,
    embed_text,
    find_similar_merchant,
    load_merchant_embeddings,
)


class TestEmbeddings:
    """Test embedding utilities."""

    def test_embed_text_with_mock_model(self):
        """Test embedding text with mocked model."""

        class MockModel:
            def encode(self, text, convert_to_numpy=False):
                # Simple mock: return fixed-size vector based on text length
                size = 384  # MiniLM size
                return np.ones(size) * (len(text) % 10)

        model = MockModel()
        embedding = embed_text("test merchant", model)

        assert isinstance(embedding, np.ndarray)
        assert len(embedding) > 0

    def test_embed_text_empty_model(self):
        """Test embedding with None model."""
        embedding = embed_text("test", None)
        assert len(embedding) == 0

    def test_calculate_similarity(self):
        """Test cosine similarity calculation."""
        # Two identical embeddings should have similarity 1.0
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([1.0, 0.0, 0.0])

        similarity = calculate_similarity(embedding1, embedding2)
        assert 0.99 <= similarity <= 1.01

    def test_calculate_similarity_orthogonal(self):
        """Test similarity of orthogonal vectors."""
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([0.0, 1.0, 0.0])

        similarity = calculate_similarity(embedding1, embedding2)
        assert 0.0 - 0.01 <= similarity <= 0.01

    def test_calculate_similarity_empty_vectors(self):
        """Test similarity with empty vectors."""
        embedding1 = np.array([])
        embedding2 = np.array([1.0, 0.0])

        similarity = calculate_similarity(embedding1, embedding2)
        assert similarity == 0.0

    def test_load_merchant_embeddings_nonexistent(self):
        """Test loading from nonexistent file."""
        merchants, embeddings = load_merchant_embeddings("/nonexistent/file.npy")

        assert merchants == {}
        assert len(embeddings) == 0

    def test_load_merchant_embeddings_valid(self):
        """Test loading valid embeddings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test embeddings file
            test_data = {
                "merchants": {
                    0: {"name": "Test", "category": "FOOD"},
                    1: {"name": "Test2", "category": "GAS"},
                },
                "embeddings": np.array([[1.0, 0.0], [0.0, 1.0]]),
            }

            filepath = Path(tmpdir) / "test_vectors.npy"
            np.save(filepath, test_data)

            merchants, embeddings = load_merchant_embeddings(str(filepath))

            assert len(merchants) == 2
            assert len(embeddings) == 2

    def test_find_similar_merchant_no_model(self):
        """Test find_similar_merchant without model."""
        merchants = {0: {"name": "Test", "category": "FOOD"}}
        embeddings = np.array([[1.0, 0.0]])

        result = find_similar_merchant("test", merchants, embeddings, model=None)

        assert result is None

    def test_find_similar_merchant_empty_embeddings(self):
        """Test find_similar_merchant with empty embeddings."""

        class MockModel:
            def encode(self, text, convert_to_numpy=False):
                return np.ones(2)

        merchants = {0: {"name": "Test", "category": "FOOD"}}
        embeddings = np.array([])

        result = find_similar_merchant("test", merchants, embeddings, model=MockModel())

        assert result is None

    def test_find_similar_merchant_above_threshold(self):
        """Test finding similar merchant above threshold."""

        class MockModel:
            def encode(self, text, convert_to_numpy=False):
                # Return same vector for matching names
                if "starbucks" in text.lower():
                    return np.array([1.0, 0.0, 0.0])
                return np.array([0.5, 0.5, 0.0])

        merchants = {
            0: {
                "name": "Starbucks Coffee",
                "category": "FOOD_AND_DRINK",
                "subcategory": "FOOD_AND_DRINK.COFFEE",
            }
        }

        # Create embedding that matches Starbucks
        embeddings = np.array([[1.0, 0.0, 0.0]])

        result = find_similar_merchant(
            "starbucks", merchants, embeddings, threshold=0.5, model=MockModel()
        )

        # Should find match with high similarity
        assert result is not None
        assert result["name"] == "Starbucks Coffee"

    def test_find_similar_merchant_below_threshold(self):
        """Test that low similarity is rejected."""

        class MockModel:
            def encode(self, text, convert_to_numpy=False):
                # Return very different vectors
                return np.array([0.1, 0.1, 0.1])

        merchants = {
            0: {
                "name": "Some Merchant",
                "category": "FOOD",
                "subcategory": "FOOD.RESTAURANT",
            }
        }

        embeddings = np.array([[1.0, 0.0, 0.0]])

        result = find_similar_merchant(
            "different merchant",
            merchants,
            embeddings,
            threshold=0.85,
            model=MockModel(),
        )

        # Should reject low similarity
        assert result is None

    def test_find_similar_merchant_threshold_boundary(self):
        """Test threshold boundary conditions."""

        class MockModel:
            def encode(self, text, convert_to_numpy=False):
                return np.array([1.0, 0.0, 0.0])

        merchants = {0: {"name": "Test", "category": "FOOD", "subcategory": "FOOD.MAIN"}}
        embeddings = np.array([[1.0, 0.0, 0.0]])

        # Exactly at threshold (1.0 similarity)
        result = find_similar_merchant(
            "test", merchants, embeddings, threshold=1.0, model=MockModel()
        )

        assert result is not None

        # Just below threshold
        result = find_similar_merchant(
            "test", merchants, embeddings, threshold=1.01, model=MockModel()
        )

        assert result is None
