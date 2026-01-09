"""
NatLangChain API Package.

This package contains the modular Flask blueprints for the NatLangChain API.

Blueprints:
- core: Basic blockchain operations (health, chain, entries, blocks)
- search: Semantic search and drift detection
- mobile: Mobile deployment
- monitoring: Metrics and health endpoints
- boundary: Boundary protection (modes, SIEM, agent security)
- marketplace: Module marketplace with Story Protocol integration

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

from .anchoring import anchoring_bp
from .boundary import boundary_bp
from .chat import chat_bp
from .composability import composability_bp
from .contracts import contracts_bp
from .core import core_bp
from .derivatives import derivatives_bp
from .endowment import endowment_bp
from .help import help_bp
from .identity import identity_bp
from .marketplace import marketplace_bp
from .mobile import mobile_bp
from .monitoring import monitoring_bp
from .search import search_bp

# List of all blueprints for registration
# Tuple format: (blueprint, url_prefix)
ALL_BLUEPRINTS = [
    (core_bp, ""),  # Core routes at root
    (search_bp, ""),  # Search routes at root (e.g., /search/semantic)
    (mobile_bp, ""),  # Mobile routes (blueprint has /mobile prefix)
    (monitoring_bp, ""),  # Monitoring routes (/metrics, /health/*)
    (boundary_bp, ""),  # Boundary protection routes (/boundary/*)
    (marketplace_bp, ""),  # Marketplace routes (/marketplace/*)
    (help_bp, ""),  # Help routes (/api/help/*)
    (chat_bp, ""),  # Chat routes (/chat/*)
    (contracts_bp, ""),  # Contract routes (/contract/*)
    (derivatives_bp, ""),  # Derivative tracking routes (/derivatives/*)
    (endowment_bp, ""),  # Permanence endowment routes (/endowment/*)
    (anchoring_bp, ""),  # External anchoring routes (/anchoring/*)
    (identity_bp, ""),  # DID identity routes (/identity/*)
    (composability_bp, ""),  # Data composability routes (/composability/*)
]


def register_blueprints(app):
    """Register all blueprints with the Flask app."""
    for blueprint, url_prefix in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint, url_prefix=url_prefix)

    # Set up request logging middleware
    try:
        from monitoring.middleware import setup_request_logging

        setup_request_logging(app)
    except ImportError:
        pass

    # Initialize OpenAPI/Swagger documentation
    try:
        from swagger import init_swagger

        init_swagger(app)
    except ImportError as e:
        print(f"Note: Swagger UI not available ({e})")


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

    # Initialize boundary protection system
    try:
        from boundary_protection import ProtectionConfig, init_protection

        config = ProtectionConfig.from_env()
        managers.boundary_protection = init_protection(config)
        print(f"Boundary protection initialized in {config.initial_mode.value} mode")
    except Exception as e:
        print(f"Warning: Could not initialize boundary protection: {e}")

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
            from contract_matcher import ContractMatcher
            from contract_parser import ContractParser

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

    # Initialize marketplace (independent of API key)
    try:
        from marketplace import NetworkType, create_marketplace_manager

        managers.marketplace_manager = create_marketplace_manager(
            network=NetworkType.MAINNET, register_rra_module=True
        )
        print("Marketplace initialized with RRA-Module registered")
    except Exception as e:
        print(f"Warning: Could not initialize marketplace: {e}")

    # Initialize permanence endowment (Arweave-inspired pay-once-store-forever)
    try:
        from permanence_endowment import PermanenceEndowment

        managers.permanence_endowment = PermanenceEndowment()
        print("Permanence endowment initialized")
    except Exception as e:
        print(f"Warning: Could not initialize permanence endowment: {e}")

    # Initialize external anchoring service (Ethereum/Arweave anchoring)
    try:
        from external_anchoring import ExternalAnchoringService

        managers.anchoring_service = ExternalAnchoringService()
        print("External anchoring service initialized")
    except Exception as e:
        print(f"Warning: Could not initialize external anchoring: {e}")

    # Initialize DID identity service (W3C-compliant decentralized identity)
    try:
        from did_identity import IdentityService

        managers.identity_service = IdentityService()
        print("DID identity service initialized")
    except Exception as e:
        print(f"Warning: Could not initialize identity service: {e}")

    # Initialize data composability service (cross-application data sharing)
    try:
        from data_composability import ComposabilityService

        managers.composability_service = ComposabilityService()
        print("Data composability service initialized")
    except Exception as e:
        print(f"Warning: Could not initialize composability service: {e}")
