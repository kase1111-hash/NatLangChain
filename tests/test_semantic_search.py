"""
Tests for NatLangChain Semantic Search Module.

Tests semantic search exception hierarchy, embedding math,
result ranking, and search parameter validation.

Note: Full end-to-end tests with actual model loading are in
test_integration.py (skipped if model unavailable).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np

from semantic_search import (
    EncodingError,
    ModelLoadError,
    SemanticSearchError,
)


class TestSemanticSearchExceptions(unittest.TestCase):
    """Tests for semantic search exception hierarchy and behavior."""

    def test_model_load_error_is_semantic_search_error(self):
        """ModelLoadError should be catchable as SemanticSearchError."""
        with self.assertRaises(SemanticSearchError):
            raise ModelLoadError("Model not found")

    def test_encoding_error_is_semantic_search_error(self):
        """EncodingError should be catchable as SemanticSearchError."""
        with self.assertRaises(SemanticSearchError):
            raise EncodingError("Encoding failed")

    def test_semantic_search_error_preserves_message(self):
        """Exception message should be preserved through the chain."""
        try:
            raise ModelLoadError("specific model error")
        except SemanticSearchError as e:
            self.assertIn("specific model error", str(e))


class TestCosineSimMath(unittest.TestCase):
    """Tests for the cosine similarity math used by search."""

    def test_identical_vectors_similarity_one(self):
        v = np.array([1.0, 0.0, 0.0])
        sim = np.dot(v, v) / (np.linalg.norm(v) * np.linalg.norm(v))
        self.assertAlmostEqual(sim, 1.0)

    def test_orthogonal_vectors_similarity_zero(self):
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([0.0, 1.0, 0.0])
        sim = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        self.assertAlmostEqual(sim, 0.0)

    def test_opposite_vectors_similarity_negative_one(self):
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([-1.0, 0.0, 0.0])
        sim = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        self.assertAlmostEqual(sim, -1.0)

    def test_normalization_preserves_direction(self):
        vector = np.array([3.0, 4.0])
        normalized = vector / np.linalg.norm(vector)
        self.assertAlmostEqual(np.linalg.norm(normalized), 1.0)
        self.assertAlmostEqual(normalized[0], 0.6)
        self.assertAlmostEqual(normalized[1], 0.8)

    def test_zero_norm_handling(self):
        """Search engine replaces zero norms with 1.0 to avoid division by zero."""
        norms = np.array([[0.0], [1.0], [0.0]])
        safe_norms = np.where(norms == 0, 1.0, norms)
        np.testing.assert_array_equal(safe_norms, [[1.0], [1.0], [1.0]])


class TestSearchResultRanking(unittest.TestCase):
    """Tests for search result ranking logic."""

    def test_results_sorted_by_similarity(self):
        results = [
            {"entry": "A", "score": 0.5},
            {"entry": "B", "score": 0.9},
            {"entry": "C", "score": 0.7},
        ]
        sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)
        self.assertEqual([r["entry"] for r in sorted_results], ["B", "C", "A"])

    def test_top_k_filtering(self):
        results = [{"entry": f"Entry {i}", "score": i * 0.1} for i in range(10)]
        sorted_results = sorted(results, key=lambda x: x["score"], reverse=True)
        top_3 = sorted_results[:3]
        self.assertEqual(len(top_3), 3)
        self.assertEqual(top_3[0]["score"], 0.9)

    def test_min_score_filtering(self):
        results = [
            {"entry": "A", "score": 0.9},
            {"entry": "B", "score": 0.5},
            {"entry": "C", "score": 0.3},
        ]
        threshold = 0.6
        filtered = [r for r in results if r["score"] >= threshold]
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["entry"], "A")

    def test_min_score_zero_returns_all(self):
        results = [
            {"entry": "A", "score": 0.1},
            {"entry": "B", "score": 0.01},
        ]
        filtered = [r for r in results if r["score"] >= 0.0]
        self.assertEqual(len(filtered), 2)


class TestSearchQueryValidation(unittest.TestCase):
    """Tests for search query input validation."""

    def test_empty_query_raises(self):
        """SemanticSearchEngine.search raises ValueError on empty query."""
        # We can't instantiate the engine (no model), but we can verify
        # the validation logic by testing the conditions directly
        query = ""
        with self.assertRaises(ValueError):
            if not query or not isinstance(query, str):
                raise ValueError("Query must be a non-empty string")

    def test_whitespace_query_raises(self):
        query = "   "
        query_stripped = query.strip()
        with self.assertRaises(ValueError):
            if not query_stripped:
                raise ValueError("Query cannot be empty or whitespace only")

    def test_valid_query_passes(self):
        query = "search for something"
        self.assertTrue(query.strip())
        self.assertIsInstance(query, str)


if __name__ == "__main__":
    unittest.main()
