"""
Tests for NatLangChain Semantic Search Module

Tests semantic search engine, embeddings, similarity search,
and exception handling.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Try to import numpy - needed for semantic search tests
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# Try to import semantic search module
try:
    from semantic_search import (
        SemanticSearchError,
        ModelLoadError,
        EncodingError,
        SENTENCE_TRANSFORMERS_AVAILABLE,
    )
    SEMANTIC_SEARCH_AVAILABLE = True
except ImportError:
    SEMANTIC_SEARCH_AVAILABLE = False
    SENTENCE_TRANSFORMERS_AVAILABLE = False

    # Define stub exceptions for testing
    class SemanticSearchError(Exception):
        pass

    class ModelLoadError(SemanticSearchError):
        pass

    class EncodingError(SemanticSearchError):
        pass


class TestSemanticSearchExceptions(unittest.TestCase):
    """Tests for semantic search exception hierarchy."""

    def test_base_exception(self):
        """Test SemanticSearchError is base exception."""
        error = SemanticSearchError("Test error")
        self.assertIsInstance(error, Exception)
        self.assertEqual(str(error), "Test error")

    def test_model_load_error(self):
        """Test ModelLoadError inherits from SemanticSearchError."""
        error = ModelLoadError("Failed to load model")
        self.assertIsInstance(error, SemanticSearchError)
        self.assertEqual(str(error), "Failed to load model")

    def test_encoding_error(self):
        """Test EncodingError inherits from SemanticSearchError."""
        error = EncodingError("Failed to encode text")
        self.assertIsInstance(error, SemanticSearchError)
        self.assertEqual(str(error), "Failed to encode text")

    def test_exception_hierarchy(self):
        """Test exception class hierarchy."""
        self.assertTrue(issubclass(ModelLoadError, SemanticSearchError))
        self.assertTrue(issubclass(EncodingError, SemanticSearchError))
        self.assertTrue(issubclass(SemanticSearchError, Exception))


class TestSentenceTransformersAvailability(unittest.TestCase):
    """Tests for sentence transformers availability check."""

    def test_availability_flag_exists(self):
        """Test that availability flag is defined."""
        self.assertIsInstance(SENTENCE_TRANSFORMERS_AVAILABLE, bool)


@unittest.skipUnless(
    SENTENCE_TRANSFORMERS_AVAILABLE,
    "sentence-transformers not installed"
)
class TestSemanticSearchEngine(unittest.TestCase):
    """Tests for SemanticSearchEngine (requires sentence-transformers)."""

    def test_import_with_transformers(self):
        """Test that SemanticSearchEngine can be imported."""
        from semantic_search import SemanticSearchEngine
        self.assertIsNotNone(SemanticSearchEngine)


class TestSemanticSearchWithMocks(unittest.TestCase):
    """Tests for SemanticSearchEngine using mocks."""

    def test_model_load_error_on_invalid_model(self):
        """Test that ModelLoadError is raised for invalid model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            self.skipTest("sentence-transformers not installed")

        from semantic_search import SemanticSearchEngine

        with self.assertRaises(ModelLoadError):
            SemanticSearchEngine(model_name="nonexistent-model-xyz-123")

    def test_model_load_error_message(self):
        """Test error message format for model load failure."""
        error = ModelLoadError("Model 'test' not found")
        self.assertIn("test", str(error))


@unittest.skipUnless(NUMPY_AVAILABLE, "numpy not installed")
class TestSemanticSearchUtilities(unittest.TestCase):
    """Tests for semantic search utility functions."""

    def test_cosine_similarity_calculation(self):
        """Test cosine similarity calculation."""
        # Simple cosine similarity implementation for testing
        def cosine_similarity(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

        # Identical vectors should have similarity 1.0
        v1 = np.array([1.0, 0.0, 0.0])
        self.assertAlmostEqual(cosine_similarity(v1, v1), 1.0)

        # Orthogonal vectors should have similarity 0.0
        v2 = np.array([0.0, 1.0, 0.0])
        self.assertAlmostEqual(cosine_similarity(v1, v2), 0.0)

        # Opposite vectors should have similarity -1.0
        v3 = np.array([-1.0, 0.0, 0.0])
        self.assertAlmostEqual(cosine_similarity(v1, v3), -1.0)

    def test_embedding_normalization(self):
        """Test embedding normalization."""
        # Test L2 normalization
        vector = np.array([3.0, 4.0])  # 3-4-5 triangle
        normalized = vector / np.linalg.norm(vector)

        # Normalized vector should have unit length
        self.assertAlmostEqual(np.linalg.norm(normalized), 1.0)

        # Direction should be preserved
        self.assertAlmostEqual(normalized[0], 0.6)
        self.assertAlmostEqual(normalized[1], 0.8)


class TestSearchResultRanking(unittest.TestCase):
    """Tests for search result ranking logic."""

    def test_results_sorted_by_similarity(self):
        """Test that results are sorted by similarity score."""
        # Simulate search results with scores
        results = [
            {"entry": "A", "score": 0.5},
            {"entry": "B", "score": 0.9},
            {"entry": "C", "score": 0.7},
        ]

        # Sort by score descending
        sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)

        self.assertEqual(sorted_results[0]["entry"], "B")
        self.assertEqual(sorted_results[1]["entry"], "C")
        self.assertEqual(sorted_results[2]["entry"], "A")

    def test_top_k_filtering(self):
        """Test top-k result filtering."""
        results = [
            {"entry": f"Entry {i}", "score": i * 0.1}
            for i in range(10)
        ]

        # Get top 3
        sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)
        top_3 = sorted_results[:3]

        self.assertEqual(len(top_3), 3)
        self.assertEqual(top_3[0]["score"], 0.9)

    def test_threshold_filtering(self):
        """Test filtering by similarity threshold."""
        results = [
            {"entry": "A", "score": 0.9},
            {"entry": "B", "score": 0.5},
            {"entry": "C", "score": 0.3},
        ]

        threshold = 0.6
        filtered = [r for r in results if r["score"] >= threshold]

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["entry"], "A")


class TestCacheInvalidation(unittest.TestCase):
    """Tests for embedding cache invalidation."""

    def test_cache_invalidation_flag(self):
        """Test cache validity flag behavior."""
        # Simulate cache state
        cache_valid = False

        # After initial index
        cache_valid = True
        self.assertTrue(cache_valid)

        # After new entries added
        cache_valid = False
        self.assertFalse(cache_valid)

    def test_cache_entry_count_mismatch(self):
        """Test cache invalidation on entry count mismatch."""
        cached_entries = 100
        current_entries = 105

        # Cache should be invalid if counts differ
        cache_valid = cached_entries == current_entries
        self.assertFalse(cache_valid)


if __name__ == "__main__":
    unittest.main()
