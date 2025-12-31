"""
NatLangChain API Package.

This package contains the modular Flask blueprints for the NatLangChain API.

Blueprints:
- core: Basic blockchain operations (health, chain, entries, blocks)
- search: Semantic search and drift detection
- mobile: Mobile deployment

Future blueprints (to be extracted from api.py):
- contracts: Contract parsing, matching, and management
- disputes: Dispute filing and resolution
- forks: Escalation fork management
- burns: Observance burn operations
- harassment: Anti-harassment protections
- treasury: Treasury management
- auth: FIDO2 authentication
- privacy: ZK privacy operations
- negotiation: Automated negotiation
- mediation: Mediator reputation and matching
- market: Market pricing
- chat: Chat interface
- p2p: Peer-to-peer network operations
"""

from api.core import core_bp
from api.mobile import mobile_bp
from api.search import search_bp

# List of all blueprints for registration
# Tuple format: (blueprint, url_prefix)
ALL_BLUEPRINTS = [
    (core_bp, ''),      # Core routes at root
    (search_bp, ''),    # Search routes at root (e.g., /search/semantic)
    (mobile_bp, ''),    # Mobile routes (blueprint has /mobile prefix)
]


def register_blueprints(app):
    """Register all blueprints with the Flask app."""
    for blueprint, url_prefix in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint, url_prefix=url_prefix)


def init_managers(api_key: str = None):
    """
    Initialize all managers and validators.

    This function populates the shared ManagerRegistry with
    initialized instances of all optional features.

    Args:
        api_key: Anthropic API key for LLM features
    """
    from api.utils import managers

    # Initialize features that don't require API key
    try:
        from temporal_fixity import TemporalFixity
        managers.temporal_fixity = TemporalFixity()
        print("Temporal fixity initialized")
    except Exception as e:
        print(f"Warning: Could not initialize temporal fixity: {e}")

    try:
        from semantic_search import SemanticSearchEngine
        managers.search_engine = SemanticSearchEngine()
        print("Semantic search engine initialized")
    except Exception as e:
        print(f"Warning: Could not initialize semantic search: {e}")

    # Initialize LLM-based features if API key available
    if api_key and api_key != "your_api_key_here":
        try:
            from validator import HybridValidator, ProofOfUnderstanding
            managers.llm_validator = ProofOfUnderstanding(api_key)
            managers.hybrid_validator = HybridValidator(managers.llm_validator)
            print("LLM validators initialized")
        except Exception as e:
            print(f"Warning: Could not initialize LLM validators: {e}")

        try:
            from semantic_diff import SemanticDriftDetector
            managers.drift_detector = SemanticDriftDetector(api_key)
        except Exception:
            pass

        try:
            from dialectic_consensus import DialecticConsensus
            managers.dialectic_validator = DialecticConsensus(api_key)
        except Exception:
            pass

        try:
            from contract_parser import ContractParser
            from contract_matcher import ContractMatcher
            managers.contract_parser = ContractParser(api_key)
            managers.contract_matcher = ContractMatcher(api_key)
        except Exception:
            pass

        try:
            from dispute import DisputeManager
            managers.dispute_manager = DisputeManager(api_key)
        except Exception:
            pass

        try:
            from mobile_deployment import MobileDeploymentManager
            managers.mobile_deployment = MobileDeploymentManager()
        except Exception:
            pass

        print("LLM-based features initialized")
