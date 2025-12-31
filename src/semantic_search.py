"""
NatLangChain - Semantic Search
Performs semantic search across blockchain entries using embeddings
Integrated version with correct data structures
"""

import logging
from typing import Any

import numpy as np

# Configure module-level logger
logger = logging.getLogger(__name__)

# Import SentenceTransformer with error handling for optional dependency
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning(
        "sentence-transformers not installed. Semantic search will be unavailable. "
        "Install with: pip install sentence-transformers"
    )

from blockchain import NatLangChain


class SemanticSearchError(Exception):
    """Exception raised for semantic search errors."""
    pass


class ModelLoadError(SemanticSearchError):
    """Exception raised when model fails to load."""
    pass


class EncodingError(SemanticSearchError):
    """Exception raised when encoding fails."""
    pass


class SemanticSearchEngine:
    """
    Performs semantic search across all natural language entries in the blockchain.

    Unlike keyword search, this uses embeddings to find semantically similar
    content even if different words are used.

    Example: Searching for "worker unrest" will match entries about "labor disputes"
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the semantic search engine.

        Args:
            model_name: Sentence transformer model to use for embeddings

        Raises:
            ModelLoadError: If the model cannot be loaded
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ModelLoadError(
                "sentence-transformers library is not installed. "
                "Install with: pip install sentence-transformers"
            )

        self.model_name = model_name
        try:
            logger.info("Loading sentence transformer model: %s", model_name)
            self.model = SentenceTransformer(model_name)
            logger.info("Successfully loaded model: %s", model_name)
        except OSError as e:
            logger.error(
                "Failed to load model '%s': %s. "
                "The model may not exist or there may be network issues.",
                model_name, str(e)
            )
            raise ModelLoadError(
                f"Failed to load sentence transformer model '{model_name}': {e!s}. "
                f"Check that the model name is correct and you have network access."
            ) from e
        except Exception as e:
            logger.error(
                "Unexpected error loading model '%s': %s: %s",
                model_name, type(e).__name__, str(e)
            )
            raise ModelLoadError(
                f"Unexpected error loading model '{model_name}': {type(e).__name__}: {e!s}"
            ) from e

        self._entries_cache = []
        self._embeddings_cache = None
        self._cache_valid = False

    def _extract_all_entries(self, blockchain: NatLangChain) -> list[dict[str, Any]]:
        """
        Extract all entries from the blockchain with metadata.

        Args:
            blockchain: The NatLangChain instance

        Returns:
            List of entry dictionaries with metadata
        """
        all_entries = []

        for block in blockchain.chain:
            for entry in block.entries:
                all_entries.append({
                    "block_index": block.index,
                    "block_hash": block.hash,
                    "timestamp": block.timestamp,
                    "author": entry.author,
                    "content": entry.content,
                    "intent": entry.intent,
                    "validation_status": entry.validation_status,
                    "metadata": entry.metadata
                })

        return all_entries

    def _build_embeddings_cache(self, blockchain: NatLangChain):
        """
        Build cache of entries and their embeddings.

        Args:
            blockchain: The NatLangChain instance

        Raises:
            EncodingError: If encoding fails
        """
        self._entries_cache = self._extract_all_entries(blockchain)

        # Generate embeddings for all content
        content_list = [entry["content"] for entry in self._entries_cache]

        if content_list:
            try:
                self._embeddings_cache = self.model.encode(content_list)
            except RuntimeError as e:
                # Common for out-of-memory errors
                logger.error(
                    "Failed to encode %d entries: %s. "
                    "This may be due to memory constraints.",
                    len(content_list), str(e)
                )
                raise EncodingError(
                    f"Failed to encode entries: {e!s}. "
                    f"Try reducing batch size or using a smaller model."
                ) from e
            except Exception as e:
                logger.error(
                    "Unexpected error encoding entries: %s: %s",
                    type(e).__name__, str(e)
                )
                raise EncodingError(
                    f"Encoding failed: {type(e).__name__}: {e!s}"
                ) from e
        else:
            self._embeddings_cache = np.array([])

        self._cache_valid = True

    def search(
        self,
        blockchain: NatLangChain,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0
    ) -> list[dict[str, Any]]:
        """
        Perform semantic search across all blockchain entries.

        Args:
            blockchain: The NatLangChain instance to search
            query: Natural language search query
            top_k: Number of top results to return
            min_score: Minimum similarity score (0.0-1.0) to include results

        Returns:
            List of search results sorted by relevance

        Raises:
            EncodingError: If query encoding fails
            ValueError: If query is empty or invalid
        """
        # Validate input
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")

        query = query.strip()
        if not query:
            raise ValueError("Query cannot be empty or whitespace only")

        # Rebuild cache (in production, this would be smarter)
        self._build_embeddings_cache(blockchain)

        if len(self._entries_cache) == 0:
            return []

        # Generate query embedding with error handling
        try:
            query_embedding = self.model.encode([query])
        except Exception as e:
            logger.error(
                "Failed to encode search query: %s: %s",
                type(e).__name__, str(e)
            )
            raise EncodingError(f"Failed to encode query: {e!s}") from e

        # Calculate cosine similarity with safe normalization
        # Handle potential division by zero
        embedding_norms = np.linalg.norm(self._embeddings_cache, axis=1, keepdims=True)
        # Avoid division by zero by replacing zero norms with 1
        embedding_norms = np.where(embedding_norms == 0, 1.0, embedding_norms)
        norm_embeddings = self._embeddings_cache / embedding_norms

        query_norm = np.linalg.norm(query_embedding, keepdims=True)
        if query_norm == 0:
            logger.warning("Query embedding has zero norm, returning empty results")
            return []
        norm_query = query_embedding / query_norm

        similarities = np.dot(norm_embeddings, norm_query.T).flatten()

        # Filter by minimum score
        valid_indices = np.where(similarities >= min_score)[0]

        # Sort by similarity and get top_k
        sorted_indices = valid_indices[np.argsort(similarities[valid_indices])[::-1]]
        top_indices = sorted_indices[:top_k]

        # Build results
        results = []
        for idx in top_indices:
            results.append({
                "score": round(float(similarities[idx]), 4),
                "entry": self._entries_cache[idx]
            })

        return results

    def search_by_field(
        self,
        blockchain: NatLangChain,
        query: str,
        field: str = "content",
        top_k: int = 5,
        min_score: float = 0.0
    ) -> list[dict[str, Any]]:
        """
        Perform semantic search on a specific field (content, intent, etc.).

        Args:
            blockchain: The NatLangChain instance to search
            query: Natural language search query
            field: Field to search in ("content", "intent", or "both")
            top_k: Number of top results to return
            min_score: Minimum similarity score to include results

        Returns:
            List of search results sorted by relevance

        Raises:
            EncodingError: If encoding fails
            ValueError: If query or field is invalid
        """
        # Validate input
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")

        query = query.strip()
        if not query:
            raise ValueError("Query cannot be empty or whitespace only")

        # Rebuild cache
        self._build_embeddings_cache(blockchain)

        if len(self._entries_cache) == 0:
            return []

        # Build search corpus based on field
        if field == "content":
            corpus = [entry["content"] for entry in self._entries_cache]
        elif field == "intent":
            corpus = [entry["intent"] for entry in self._entries_cache]
        elif field == "both":
            corpus = [
                f"{entry['intent']}: {entry['content']}"
                for entry in self._entries_cache
            ]
        else:
            raise ValueError(f"Invalid field: {field}. Use 'content', 'intent', or 'both'")

        # Generate embeddings for corpus with error handling
        try:
            corpus_embeddings = self.model.encode(corpus)
            query_embedding = self.model.encode([query])
        except Exception as e:
            logger.error(
                "Failed to encode during field search: %s: %s",
                type(e).__name__, str(e)
            )
            raise EncodingError(f"Encoding failed: {e!s}") from e

        # Calculate cosine similarity with safe normalization
        embedding_norms = np.linalg.norm(corpus_embeddings, axis=1, keepdims=True)
        embedding_norms = np.where(embedding_norms == 0, 1.0, embedding_norms)
        norm_embeddings = corpus_embeddings / embedding_norms

        query_norm = np.linalg.norm(query_embedding, keepdims=True)
        if query_norm == 0:
            logger.warning("Query embedding has zero norm, returning empty results")
            return []
        norm_query = query_embedding / query_norm

        similarities = np.dot(norm_embeddings, norm_query.T).flatten()

        # Filter and sort
        valid_indices = np.where(similarities >= min_score)[0]
        sorted_indices = valid_indices[np.argsort(similarities[valid_indices])[::-1]]
        top_indices = sorted_indices[:top_k]

        # Build results
        results = []
        for idx in top_indices:
            results.append({
                "score": round(float(similarities[idx]), 4),
                "entry": self._entries_cache[idx],
                "matched_field": field
            })

        return results

    def find_similar_entries(
        self,
        blockchain: NatLangChain,
        entry_content: str,
        top_k: int = 5,
        exclude_exact: bool = True
    ) -> list[dict[str, Any]]:
        """
        Find entries similar to a given entry.

        Useful for detecting duplicate or related entries.

        Args:
            blockchain: The NatLangChain instance
            entry_content: Content to find similar entries for
            top_k: Number of similar entries to return
            exclude_exact: Whether to exclude exact matches

        Returns:
            List of similar entries
        """
        results = self.search(blockchain, entry_content, top_k=top_k + 1)

        if exclude_exact and results:
            # Filter out exact or near-exact matches (score > 0.99)
            results = [r for r in results if r["score"] < 0.99]

        return results[:top_k]
