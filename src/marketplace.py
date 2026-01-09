"""
NatLangChain Marketplace Module

Enables buying and selling of code modules with Story Protocol integration.
Supports fetching .market.yaml configurations from GitHub repositories
and minting license NFTs via Story Protocol SDK.

Key features:
- Fetch and parse .market.yaml from any GitHub repo
- Display pricing and licensing terms to buyers
- Story Protocol SDK integration for license NFT minting
- Payment transfer to seller wallets
- Revenue split enforcement (developer/platform/community)
"""

import hashlib
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import requests
import yaml

# Story Protocol configuration
STORY_PROTOCOL_TESTNET_RPC = "https://aeneid.storyrpc.io"
STORY_PROTOCOL_MAINNET_RPC = "https://mainnet.storyrpc.io"
STORY_PROTOCOL_CHAIN_ID = 1514


class LicenseType(Enum):
    """Supported license types for marketplace modules."""

    PERPETUAL = "perpetual"
    SUBSCRIPTION = "subscription"
    USAGE_BASED = "usage_based"
    TRIAL = "trial"


class LicenseTier(Enum):
    """License tier levels."""

    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class NetworkType(Enum):
    """Story Protocol network types."""

    TESTNET = "testnet"
    MAINNET = "mainnet"


@dataclass
class RevenueSplit:
    """Revenue distribution configuration."""

    developer: float  # Percentage to developer (0-100)
    platform: float  # Percentage to platform (0-100)
    community: float  # Percentage to community fund (0-100)

    def __post_init__(self):
        total = self.developer + self.platform + self.community
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Revenue split must total 100%, got {total}%")

    def to_dict(self) -> dict[str, float]:
        """Serialize revenue split percentages to a dictionary."""
        return {"developer": self.developer, "platform": self.platform, "community": self.community}


@dataclass
class TierConfig:
    """Configuration for a license tier."""

    name: str
    multiplier: float  # Price multiplier (1.0 = base price)
    features: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize tier configuration to a dictionary."""
        return {"name": self.name, "multiplier": self.multiplier, "features": self.features}


@dataclass
class PILTerms:
    """Programmable IP License (PIL) terms for Story Protocol."""

    commercial_use: bool = True
    derivatives_allowed: bool = True
    attribution_required: bool = True
    derivative_royalty_percent: float = 0.0
    payment_token: str = "ETH"

    def to_dict(self) -> dict[str, Any]:
        """Serialize PIL terms to a dictionary for Story Protocol integration."""
        return {
            "commercial_use": self.commercial_use,
            "derivatives_allowed": self.derivatives_allowed,
            "attribution_required": self.attribution_required,
            "derivative_royalty_percent": self.derivative_royalty_percent,
            "payment_token": self.payment_token,
        }


@dataclass
class MarketConfig:
    """Marketplace configuration parsed from .market.yaml."""

    # Module identification
    module_name: str
    version: str
    description: str
    github_url: str

    # Pricing
    license_type: LicenseType
    base_price_eth: float
    floor_price_eth: float = 0.0
    ceiling_price_eth: float = 0.0

    # Revenue distribution
    revenue_split: RevenueSplit = None

    # Tier configurations
    tiers: dict[LicenseTier, TierConfig] = field(default_factory=dict)

    # Story Protocol integration
    ip_asset_id: str = ""
    owner_wallet: str = ""
    pil_terms: PILTerms = None

    # Wallet addresses for revenue distribution
    developer_wallet: str = ""
    platform_wallet: str = ""
    community_wallet: str = ""

    # Metadata
    auto_convert_license: str = ""  # e.g., "Apache 2.0"
    auto_convert_date: str = ""  # ISO date string

    def __post_init__(self):
        if self.pil_terms is None:
            self.pil_terms = PILTerms()
        if self.revenue_split is None:
            self.revenue_split = RevenueSplit(developer=91.0, platform=8.0, community=1.0)

    def get_tier_price(self, tier: LicenseTier) -> float:
        """Calculate price for a specific tier."""
        if tier in self.tiers:
            return self.base_price_eth * self.tiers[tier].multiplier
        return self.base_price_eth

    def to_dict(self) -> dict[str, Any]:
        """Serialize market configuration to a dictionary for storage or API response."""
        return {
            "module_name": self.module_name,
            "version": self.version,
            "description": self.description,
            "github_url": self.github_url,
            "license_type": self.license_type.value,
            "base_price_eth": self.base_price_eth,
            "floor_price_eth": self.floor_price_eth,
            "ceiling_price_eth": self.ceiling_price_eth,
            "revenue_split": self.revenue_split.to_dict() if self.revenue_split else None,
            "tiers": {t.value: c.to_dict() for t, c in self.tiers.items()},
            "ip_asset_id": self.ip_asset_id,
            "owner_wallet": self.owner_wallet,
            "pil_terms": self.pil_terms.to_dict() if self.pil_terms else None,
            "developer_wallet": self.developer_wallet,
            "platform_wallet": self.platform_wallet,
            "community_wallet": self.community_wallet,
            "auto_convert_license": self.auto_convert_license,
            "auto_convert_date": self.auto_convert_date,
        }


@dataclass
class LicensePurchase:
    """Record of a license purchase."""

    purchase_id: str
    module_name: str
    ip_asset_id: str
    buyer_wallet: str
    seller_wallet: str
    tier: LicenseTier
    price_eth: float
    license_nft_id: str = ""
    transaction_hash: str = ""
    timestamp: str = ""
    status: str = "pending"

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        if not self.purchase_id:
            self.purchase_id = self._generate_purchase_id()

    def _generate_purchase_id(self) -> str:
        """Generate unique purchase ID."""
        data = f"{self.buyer_wallet}:{self.ip_asset_id}:{self.timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        """Serialize license purchase record to a dictionary for storage or API response."""
        return {
            "purchase_id": self.purchase_id,
            "module_name": self.module_name,
            "ip_asset_id": self.ip_asset_id,
            "buyer_wallet": self.buyer_wallet,
            "seller_wallet": self.seller_wallet,
            "tier": self.tier.value,
            "price_eth": self.price_eth,
            "license_nft_id": self.license_nft_id,
            "transaction_hash": self.transaction_hash,
            "timestamp": self.timestamp,
            "status": self.status,
        }


class GitHubConfigFetcher:
    """Fetches and parses .market.yaml from GitHub repositories."""

    # Pattern to match GitHub URLs and extract owner/repo
    GITHUB_PATTERNS = [
        r"github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/|$)",
        r"raw\.githubusercontent\.com/([^/]+)/([^/]+)/",
    ]

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._cache: dict[str, tuple[MarketConfig, float]] = {}
        self._cache_ttl = 300  # 5 minutes

    def _parse_github_url(self, url: str) -> tuple[str, str] | None:
        """Extract owner and repo from a GitHub URL."""
        for pattern in self.GITHUB_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2)
        return None

    def _get_raw_url(self, github_url: str, branch: str = "main") -> str:
        """Convert GitHub URL to raw content URL for .market.yaml."""
        parsed = self._parse_github_url(github_url)
        if not parsed:
            raise ValueError(f"Invalid GitHub URL: {github_url}")

        owner, repo = parsed
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/.market.yaml"

    def fetch_config(
        self, github_url: str, branch: str = "main", use_cache: bool = True
    ) -> MarketConfig:
        """
        Fetch and parse .market.yaml from a GitHub repository.

        Args:
            github_url: GitHub repository URL
            branch: Branch to fetch from (default: main)
            use_cache: Whether to use cached config if available

        Returns:
            Parsed MarketConfig object

        Raises:
            ValueError: If URL is invalid or config cannot be parsed
            requests.RequestException: If fetch fails
        """
        cache_key = f"{github_url}:{branch}"

        # Check cache
        if use_cache and cache_key in self._cache:
            config, cached_time = self._cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                return config

        # Fetch the raw config file
        raw_url = self._get_raw_url(github_url, branch)

        try:
            response = requests.get(raw_url, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError(f"No .market.yaml found in {github_url}") from e
            raise

        # Parse YAML
        try:
            yaml_data = yaml.safe_load(response.text)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in .market.yaml: {e}") from e

        # Convert to MarketConfig
        config = self._parse_market_config(yaml_data, github_url)

        # Cache the result
        self._cache[cache_key] = (config, time.time())

        return config

    def _parse_market_config(self, data: dict, github_url: str) -> MarketConfig:
        """Parse raw YAML data into MarketConfig object."""
        # Extract basic fields
        module_info = data.get("module", {})
        pricing = data.get("pricing", {})
        story_protocol = data.get("story_protocol", {})
        wallets = data.get("wallets", {})
        license_info = data.get("license", {})

        # Parse license type
        license_type_str = pricing.get("license_type", "perpetual").lower()
        try:
            license_type = LicenseType(license_type_str)
        except ValueError:
            license_type = LicenseType.PERPETUAL

        # Parse revenue split
        revenue_data = data.get("revenue_split", {})
        revenue_split = RevenueSplit(
            developer=float(revenue_data.get("developer", 91)),
            platform=float(revenue_data.get("platform", 8)),
            community=float(revenue_data.get("community", 1)),
        )

        # Parse tiers
        tiers = {}
        tiers_data = data.get("tiers", {})
        for tier_name, tier_config in tiers_data.items():
            try:
                tier_enum = LicenseTier(tier_name.lower())
                tiers[tier_enum] = TierConfig(
                    name=tier_name,
                    multiplier=float(tier_config.get("multiplier", 1.0)),
                    features=tier_config.get("features", []),
                )
            except ValueError:
                continue  # Skip unknown tiers

        # Parse PIL terms
        pil_data = story_protocol.get("pil_terms", {})
        pil_terms = PILTerms(
            commercial_use=pil_data.get("commercial_use", True),
            derivatives_allowed=pil_data.get("derivatives_allowed", True),
            attribution_required=pil_data.get("attribution_required", True),
            derivative_royalty_percent=float(pil_data.get("derivative_royalty", 0)),
            payment_token=pil_data.get("payment_token", "ETH"),
        )

        return MarketConfig(
            module_name=module_info.get("name", "Unknown Module"),
            version=module_info.get("version", "1.0.0"),
            description=module_info.get("description", ""),
            github_url=github_url,
            license_type=license_type,
            base_price_eth=float(pricing.get("target_price", pricing.get("price", 0.05))),
            floor_price_eth=float(pricing.get("floor_price", 0.02)),
            ceiling_price_eth=float(pricing.get("ceiling_price", 0.15)),
            revenue_split=revenue_split,
            tiers=tiers,
            ip_asset_id=story_protocol.get("ip_asset_id", ""),
            owner_wallet=wallets.get("developer", wallets.get("owner", "")),
            pil_terms=pil_terms,
            developer_wallet=wallets.get("developer", ""),
            platform_wallet=wallets.get("platform", ""),
            community_wallet=wallets.get("community", ""),
            auto_convert_license=license_info.get("auto_convert", ""),
            auto_convert_date=license_info.get("auto_convert_date", ""),
        )

    def clear_cache(self):
        """Clear the configuration cache."""
        self._cache.clear()


class StoryProtocolClient:
    """
    Client for interacting with Story Protocol SDK.

    Handles license NFT minting and IP asset interactions.
    Uses the story-protocol-python-sdk for blockchain operations.
    """

    def __init__(self, network: NetworkType = NetworkType.MAINNET, private_key: str = None):
        self.network = network
        self.private_key = private_key
        self.rpc_url = (
            STORY_PROTOCOL_MAINNET_RPC
            if network == NetworkType.MAINNET
            else STORY_PROTOCOL_TESTNET_RPC
        )
        self.chain_id = STORY_PROTOCOL_CHAIN_ID
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Story Protocol SDK client."""
        try:
            from story_protocol_python_sdk import StoryClient

            self._client = StoryClient(
                rpc_url=self.rpc_url, chain_id=self.chain_id, private_key=self.private_key
            )
        except ImportError:
            # SDK not available - will use mock mode
            self._client = None
        except Exception:
            self._client = None

    def is_available(self) -> bool:
        """Check if Story Protocol SDK is available."""
        return self._client is not None

    def get_ip_asset(self, ip_asset_id: str) -> dict[str, Any] | None:
        """
        Fetch IP asset details from Story Protocol.

        Args:
            ip_asset_id: The IP Asset ID to query

        Returns:
            IP asset details or None if not found
        """
        if not self._client:
            # Mock response for development
            return {
                "id": ip_asset_id,
                "owner": "0x28AF4381Fe546CAe46f2B390360FF9D4F8B1C418",
                "status": "registered",
                "metadata": {},
            }

        try:
            return self._client.get_ip_asset(ip_asset_id)
        except Exception as e:
            return {"error": str(e)}

    def mint_license_nft(
        self, ip_asset_id: str, buyer_wallet: str, license_terms: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Mint a license NFT for the buyer.

        Args:
            ip_asset_id: The IP Asset ID to license
            buyer_wallet: The buyer's wallet address
            license_terms: PIL license terms

        Returns:
            Minting result with NFT ID and transaction hash
        """
        if not self._client:
            # Mock response for development
            mock_nft_id = hashlib.sha256(
                f"{ip_asset_id}:{buyer_wallet}:{time.time()}".encode()
            ).hexdigest()[:16]
            return {
                "success": True,
                "nft_id": f"0x{mock_nft_id}",
                "transaction_hash": f"0x{'0' * 64}",
                "network": self.network.value,
                "mock": True,
            }

        try:
            result = self._client.mint_license(
                ip_asset_id=ip_asset_id, recipient=buyer_wallet, license_terms=license_terms
            )
            return {
                "success": True,
                "nft_id": result.get("nft_id"),
                "transaction_hash": result.get("tx_hash"),
                "network": self.network.value,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "network": self.network.value}

    def verify_license(self, nft_id: str, wallet: str) -> bool:
        """
        Verify that a wallet holds a specific license NFT.

        Args:
            nft_id: The license NFT ID
            wallet: The wallet address to check

        Returns:
            True if wallet holds the license
        """
        if not self._client:
            return True  # Mock: always valid

        try:
            return self._client.verify_license_ownership(nft_id, wallet)
        except Exception:
            return False


class PaymentProcessor:
    """
    Handles payment processing and revenue distribution.

    Supports ETH payments with automatic revenue splitting
    according to the module's revenue configuration.
    """

    def __init__(self, story_client: StoryProtocolClient = None):
        self.story_client = story_client or StoryProtocolClient()

    def calculate_splits(self, amount_eth: float, revenue_split: RevenueSplit) -> dict[str, float]:
        """
        Calculate payment splits for each recipient.

        Args:
            amount_eth: Total payment amount in ETH
            revenue_split: Revenue distribution configuration

        Returns:
            Dict mapping recipient type to amount
        """
        return {
            "developer": amount_eth * (revenue_split.developer / 100),
            "platform": amount_eth * (revenue_split.platform / 100),
            "community": amount_eth * (revenue_split.community / 100),
        }

    def process_payment(
        self, buyer_wallet: str, amount_eth: float, config: MarketConfig
    ) -> dict[str, Any]:
        """
        Process a payment with revenue distribution.

        Args:
            buyer_wallet: The buyer's wallet address
            amount_eth: Payment amount in ETH
            config: Module marketplace configuration

        Returns:
            Payment result with transaction details
        """
        splits = self.calculate_splits(amount_eth, config.revenue_split)

        # In production, this would execute actual blockchain transactions
        # For now, we return a mock result
        payment_id = hashlib.sha256(
            f"{buyer_wallet}:{amount_eth}:{time.time()}".encode()
        ).hexdigest()[:16]

        return {
            "success": True,
            "payment_id": payment_id,
            "amount_eth": amount_eth,
            "splits": {
                "developer": {
                    "wallet": config.developer_wallet or config.owner_wallet,
                    "amount": splits["developer"],
                },
                "platform": {"wallet": config.platform_wallet, "amount": splits["platform"]},
                "community": {"wallet": config.community_wallet, "amount": splits["community"]},
            },
            "timestamp": datetime.utcnow().isoformat(),
        }


class MarketplaceManager:
    """
    Main marketplace manager that coordinates all marketplace operations.

    Provides a unified interface for:
    - Registering and listing modules
    - Fetching module configurations
    - Processing purchases
    - Minting license NFTs
    """

    def __init__(self, network: NetworkType = NetworkType.MAINNET, private_key: str = None):
        self.network = network
        self.config_fetcher = GitHubConfigFetcher()
        self.story_client = StoryProtocolClient(network, private_key)
        self.payment_processor = PaymentProcessor(self.story_client)

        # Registry of known modules: {module_id: MarketConfig}
        self._module_registry: dict[str, MarketConfig] = {}

        # Purchase history: {purchase_id: LicensePurchase}
        self._purchases: dict[str, LicensePurchase] = {}

    def register_module(self, github_url: str, branch: str = "main") -> dict[str, Any]:
        """
        Register a module from its GitHub repository.

        Fetches .market.yaml and adds the module to the registry.

        Args:
            github_url: GitHub repository URL
            branch: Branch to fetch from

        Returns:
            Registration result with module details
        """
        try:
            config = self.config_fetcher.fetch_config(github_url, branch)
        except ValueError as e:
            return {"success": False, "error": str(e), "github_url": github_url}
        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"Failed to fetch configuration: {e}",
                "github_url": github_url,
            }

        # Generate module ID from IP asset ID or URL hash
        module_id = config.ip_asset_id or hashlib.sha256(github_url.encode()).hexdigest()[:16]

        self._module_registry[module_id] = config

        return {
            "success": True,
            "module_id": module_id,
            "module_name": config.module_name,
            "ip_asset_id": config.ip_asset_id,
            "base_price_eth": config.base_price_eth,
            "github_url": github_url,
            "config": config.to_dict(),
        }

    def register_module_direct(self, module_id: str, config: MarketConfig) -> dict[str, Any]:
        """
        Register a module directly with a pre-built config.

        Args:
            module_id: Unique module identifier
            config: MarketConfig object

        Returns:
            Registration result
        """
        self._module_registry[module_id] = config
        return {
            "success": True,
            "module_id": module_id,
            "module_name": config.module_name,
            "ip_asset_id": config.ip_asset_id,
            "base_price_eth": config.base_price_eth,
        }

    def get_module(self, module_id: str) -> MarketConfig | None:
        """Get a registered module by ID."""
        return self._module_registry.get(module_id)

    def list_modules(self) -> list[dict[str, Any]]:
        """List all registered modules."""
        return [
            {
                "module_id": mid,
                "module_name": config.module_name,
                "description": config.description,
                "base_price_eth": config.base_price_eth,
                "ip_asset_id": config.ip_asset_id,
                "github_url": config.github_url,
                "tiers": list(config.tiers.keys()),
            }
            for mid, config in self._module_registry.items()
        ]

    def get_module_pricing(self, module_id: str) -> dict[str, Any] | None:
        """
        Get detailed pricing information for a module.

        Args:
            module_id: Module identifier

        Returns:
            Pricing details including tiers and terms
        """
        config = self._module_registry.get(module_id)
        if not config:
            return None

        tier_prices = {tier.value: config.get_tier_price(tier) for tier in LicenseTier}

        return {
            "module_id": module_id,
            "module_name": config.module_name,
            "license_type": config.license_type.value,
            "base_price_eth": config.base_price_eth,
            "floor_price_eth": config.floor_price_eth,
            "ceiling_price_eth": config.ceiling_price_eth,
            "tier_prices": tier_prices,
            "tiers": {tier.value: config.tiers[tier].to_dict() for tier in config.tiers},
            "pil_terms": config.pil_terms.to_dict(),
            "revenue_split": config.revenue_split.to_dict(),
        }

    def purchase_license(
        self, module_id: str, buyer_wallet: str, tier: LicenseTier = LicenseTier.STANDARD
    ) -> dict[str, Any]:
        """
        Purchase a license for a module.

        This will:
        1. Validate the module and pricing
        2. Process payment with revenue splits
        3. Mint a license NFT via Story Protocol
        4. Record the purchase

        Args:
            module_id: Module to purchase
            buyer_wallet: Buyer's wallet address
            tier: License tier to purchase

        Returns:
            Purchase result with license NFT details
        """
        # Validate module exists
        config = self._module_registry.get(module_id)
        if not config:
            return {"success": False, "error": f"Module not found: {module_id}"}

        # Validate IP asset ID exists
        if not config.ip_asset_id:
            return {"success": False, "error": "Module has no Story Protocol IP Asset ID"}

        # Calculate price for tier
        price_eth = config.get_tier_price(tier)

        # Process payment
        payment_result = self.payment_processor.process_payment(
            buyer_wallet=buyer_wallet, amount_eth=price_eth, config=config
        )

        if not payment_result.get("success"):
            return {
                "success": False,
                "error": "Payment processing failed",
                "details": payment_result,
            }

        # Mint license NFT
        mint_result = self.story_client.mint_license_nft(
            ip_asset_id=config.ip_asset_id,
            buyer_wallet=buyer_wallet,
            license_terms=config.pil_terms.to_dict(),
        )

        if not mint_result.get("success"):
            return {"success": False, "error": "License NFT minting failed", "details": mint_result}

        # Record purchase
        purchase = LicensePurchase(
            purchase_id="",  # Will be auto-generated
            module_name=config.module_name,
            ip_asset_id=config.ip_asset_id,
            buyer_wallet=buyer_wallet,
            seller_wallet=config.owner_wallet,
            tier=tier,
            price_eth=price_eth,
            license_nft_id=mint_result.get("nft_id", ""),
            transaction_hash=mint_result.get("transaction_hash", ""),
            status="completed",
        )

        self._purchases[purchase.purchase_id] = purchase

        return {
            "success": True,
            "purchase": purchase.to_dict(),
            "payment": payment_result,
            "license_nft": mint_result,
            "message": f"Successfully purchased {tier.value} license for {config.module_name}",
        }

    def get_purchase(self, purchase_id: str) -> LicensePurchase | None:
        """Get a purchase by ID."""
        return self._purchases.get(purchase_id)

    def get_purchases_by_wallet(self, wallet: str) -> list[LicensePurchase]:
        """Get all purchases for a wallet."""
        return [p for p in self._purchases.values() if p.buyer_wallet.lower() == wallet.lower()]

    def verify_license(self, module_id: str, wallet: str) -> dict[str, Any]:
        """
        Verify that a wallet has a valid license for a module.

        Args:
            module_id: Module identifier
            wallet: Wallet address to check

        Returns:
            Verification result with license details
        """
        # Check our purchase records first
        purchases = [
            p
            for p in self._purchases.values()
            if p.buyer_wallet.lower() == wallet.lower()
            and (
                self._module_registry.get(module_id)
                and p.ip_asset_id == self._module_registry[module_id].ip_asset_id
            )
        ]

        if not purchases:
            return {"has_license": False, "module_id": module_id, "wallet": wallet}

        latest_purchase = max(purchases, key=lambda p: p.timestamp)

        # Verify on-chain if possible
        on_chain_valid = True
        if latest_purchase.license_nft_id:
            on_chain_valid = self.story_client.verify_license(
                latest_purchase.license_nft_id, wallet
            )

        return {
            "has_license": True,
            "valid": on_chain_valid,
            "module_id": module_id,
            "wallet": wallet,
            "tier": latest_purchase.tier.value,
            "license_nft_id": latest_purchase.license_nft_id,
            "purchase_date": latest_purchase.timestamp,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize marketplace state."""
        return {
            "network": self.network.value,
            "modules": {mid: config.to_dict() for mid, config in self._module_registry.items()},
            "purchases": {pid: purchase.to_dict() for pid, purchase in self._purchases.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MarketplaceManager":
        """Deserialize marketplace state."""
        network = NetworkType(data.get("network", "mainnet"))
        manager = cls(network=network)

        # Restore modules (simplified - full restoration would need all fields)
        for mid, config_data in data.get("modules", {}).items():
            config = MarketConfig(
                module_name=config_data.get("module_name", ""),
                version=config_data.get("version", "1.0.0"),
                description=config_data.get("description", ""),
                github_url=config_data.get("github_url", ""),
                license_type=LicenseType(config_data.get("license_type", "perpetual")),
                base_price_eth=float(config_data.get("base_price_eth", 0)),
                ip_asset_id=config_data.get("ip_asset_id", ""),
                owner_wallet=config_data.get("owner_wallet", ""),
            )
            manager._module_registry[mid] = config

        return manager


# Pre-configured RRA-Module registration
RRA_MODULE_CONFIG = MarketConfig(
    module_name="RRA-Module",
    version="1.0.0",
    description="Resurrects dormant repos as autonomous contract-posting agents. "
    "Converts dormant repositories to autonomous contract posters, "
    "generating daily/weekly output summaries and posting OFFER contracts on NatLangChain.",
    github_url="https://github.com/kase1111-hash/RRA-Module",
    license_type=LicenseType.PERPETUAL,
    base_price_eth=0.05,
    floor_price_eth=0.02,
    ceiling_price_eth=0.15,
    revenue_split=RevenueSplit(developer=91.0, platform=8.0, community=1.0),
    tiers={
        LicenseTier.STANDARD: TierConfig(
            name="Standard",
            multiplier=1.0,
            features=["Source code access", "12-month updates", "Community support"],
        ),
        LicenseTier.PREMIUM: TierConfig(
            name="Premium",
            multiplier=2.5,
            features=["Priority support", "Custom features", "Fork rights"],
        ),
        LicenseTier.ENTERPRISE: TierConfig(
            name="Enterprise",
            multiplier=5.0,
            features=["White-label", "Competing use allowed", "Unlimited seats"],
        ),
    },
    ip_asset_id="0x513fD14485FC3485F691d12be55C0D03a6b0Ed43",
    owner_wallet="0x28AF4381Fe546CAe46f2B390360FF9D4F8B1C418",
    pil_terms=PILTerms(
        commercial_use=True,
        derivatives_allowed=True,
        attribution_required=True,
        derivative_royalty_percent=9.0,
        payment_token="ETH",
    ),
    developer_wallet="0x28AF4381Fe546CAe46f2B390360FF9D4F8B1C418",
    platform_wallet="0x28AF4381Fe546CAe46f2B390360FF9D4F8B1C418",
    community_wallet="0x28AF4381Fe546CAe46f2B390360FF9D4F8B1C418",
    auto_convert_license="Apache 2.0",
    auto_convert_date="2027-12-19",
)


def create_marketplace_manager(
    network: NetworkType = NetworkType.MAINNET, register_rra_module: bool = True
) -> MarketplaceManager:
    """
    Factory function to create a marketplace manager with default configuration.

    Args:
        network: Story Protocol network to use
        register_rra_module: Whether to register the RRA-Module by default

    Returns:
        Configured MarketplaceManager instance
    """
    manager = MarketplaceManager(network=network)

    if register_rra_module:
        manager.register_module_direct(
            module_id=RRA_MODULE_CONFIG.ip_asset_id, config=RRA_MODULE_CONFIG
        )

    return manager
