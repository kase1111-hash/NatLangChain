import json
import numpy as np
from sentence_transformers import SentenceTransformer # Standard for 2025 semantic tasks
from typing import List, Dict

class NatLangSearch:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # In a production 2025 environment, this would be an LNI-specialized model
        self.model = SentenceTransformer(model_name)
        self.chain_data = []

    def load_chain(self, file_path: str):
        with open(file_path, 'r') as f:
            self.chain_data = json.load(f)

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Performs semantic search across all prose entries in the blockchain.
        """
        all_entries = []
        for block in self.chain_data:
            for entry in block.get("entries", []):
                all_entries.append({
                    "block_index": block["block_index"],
                    "author": entry["author"],
                    "prose": entry["prose"],
                    "timestamp": block["timestamp"]
                })

        # Generate embeddings for the query and all prose segments
        prose_list = [e["prose"] for e in all_entries]
        prose_embeddings = self.model.encode(prose_list)
        query_embedding = self.model.encode([query])

        # Calculate Cosine Similarity
        similarities = np.dot(prose_embeddings, query_embedding.T).flatten()
        
        # Sort and return the top_k results
        results = []
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        for idx in top_indices:
            results.append({
                "score": round(float(similarities[idx]), 4),
                "data": all_entries[idx]
            })
            
        return results

# --- EXECUTION EXAMPLE ---
if __name__ == "__main__":
    search_engine = NatLangSearch()
    search_engine.load_chain("data/chain.json")

    # Example Query: Searching for "worker unrest"
    # Note: The prose says "labor disputes," but semantic search finds the match!
    query = "Are there any trades influenced by worker unrest or mining strikes?"
    matches = search_engine.search(query)

    print(f"--- Semantic Search Results for: '{query}' ---")
    for m in matches:
        print(f"\n[Score: {m['score']}] | Block #{m['data']['block_index']}")
        print(f"Author: {m['data']['author']}")
        print(f"Intent Prose: {m['data']['prose']}")
