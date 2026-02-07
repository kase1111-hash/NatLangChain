"""
NatLangChain API Package.

This package contains the modular Flask blueprints for the NatLangChain API.

Blueprints:
- core: Basic blockchain operations (health, chain, entries, blocks)
- search: Semantic search and drift detection
- contracts: Contract parsing, matching, and management
- derivatives: Derivative tracking routes
- monitoring: Metrics and health endpoints
"""

from .contracts import contracts_bp
from .core import core_bp
from .derivatives import derivatives_bp
from .monitoring import monitoring_bp
from .search import search_bp

# List of all blueprints for registration
# Tuple format: (blueprint, url_prefix)
ALL_BLUEPRINTS = [
    (core_bp, ""),  # Core routes at root
    (search_bp, ""),  # Search routes at root (e.g., /search/semantic)
    (monitoring_bp, ""),  # Monitoring routes (/metrics, /health/*)
    (contracts_bp, ""),  # Contract routes (/contract/*)
    (derivatives_bp, ""),  # Derivative tracking routes (/derivatives/*)
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

    # Initialize semantic search (doesn't require API key)
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
            from contract_matcher import ContractMatcher
            from contract_parser import ContractParser

            managers.contract_parser = ContractParser(api_key)
            managers.contract_matcher = ContractMatcher(api_key)
        except Exception:
            pass

        print("LLM-based features initialized")
