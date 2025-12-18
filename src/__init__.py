"""
NatLangChain - Natural Language Blockchain
A distributed ledger paradigm where natural language prose is the primary substrate
"""

from .blockchain import NatLangChain, NaturalLanguageEntry, Block
from .validator import ProofOfUnderstanding, HybridValidator

__version__ = "0.1.0"
__all__ = [
    "NatLangChain",
    "NaturalLanguageEntry",
    "Block",
    "ProofOfUnderstanding",
    "HybridValidator"
]
