"""
NatLangChain - Semantic Search
Performs semantic search across blockchain entries using embeddings
Integrated version with correct data structures
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional

from blockchain import NatLangChain


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
        """
        self.model = SentenceTransformer(model_name)
        self._entries_cache = []
        self._embeddings_cache = None
        self._cache_valid = False

    def _extract_all_entries(self, blockchain: NatLangChain) -> List[Dict[str, Any]]:
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
        """
        self._entries_cache = self._extract_all_entries(blockchain)

        # Generate embeddings for all content
        content_list = [entry["content"] for entry in self._entries_cache]

        if content_list:
            self._embeddings_cache = self.model.encode(content_list)
        else:
            self._embeddings_cache = np.array([])

        self._cache_valid = True

    def search(
        self,
        blockchain: NatLangChain,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search across all blockchain entries.

        Args:
            blockchain: The NatLangChain instance to search
            query: Natural language search query
            top_k: Number of top results to return
            min_score: Minimum similarity score (0.0-1.0) to include results

        Returns:
            List of search results sorted by relevance
        """
        # Rebuild cache (in production, this would be smarter)
        self._build_embeddings_cache(blockchain)

        if len(self._entries_cache) == 0:
            return []

        # Generate query embedding
        query_embedding = self.model.encode([query])

        # Calculate cosine similarity
        # Normalize for proper cosine similarity
        norm_embeddings = self._embeddings_cache / np.linalg.norm(
            self._embeddings_cache, axis=1, keepdims=True
        )
        norm_query = query_embedding / np.linalg.norm(query_embedding, keepdims=True)

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
    ) -> List[Dict[str, Any]]:
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
        """
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

        # Generate embeddings for corpus
        corpus_embeddings = self.model.encode(corpus)
        query_embedding = self.model.encode([query])

        # Calculate cosine similarity
        norm_embeddings = corpus_embeddings / np.linalg.norm(
            corpus_embeddings, axis=1, keepdims=True
        )
        norm_query = query_embedding / np.linalg.norm(query_embedding, keepdims=True)

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
    ) -> List[Dict[str, Any]]:
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
