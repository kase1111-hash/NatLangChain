"""
NatLangChain - Natural Language Blockchain
A distributed ledger paradigm where natural language prose is the primary substrate
"""

from .blockchain import Block, NatLangChain, NaturalLanguageEntry
from .validator import HybridValidator, ProofOfUnderstanding

__version__ = "0.1.0"
__all__ = [
    "Block",
    "HybridValidator",
    "NatLangChain",
    "NaturalLanguageEntry",
    "ProofOfUnderstanding"
]
