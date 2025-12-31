"""
NatLangChain - Market-Aware Pricing Engine
Dynamic pricing with oracle integration for market-informed negotiations.

"The market is a voting machine in the short run,
 and a weighing machine in the long run."
 - Benjamin Graham

This module implements:
- Oracle integration for real-time market data
- Dynamic offer/counteroffer generation based on market conditions
- Price suggestion during negotiation prompts
- Historical pricing analysis
"""

import math
import os
import random
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


# ============================================================
# Enums and Constants
# ============================================================

class AssetClass(Enum):
    """Asset classes for pricing."""
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"
    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    SERVICE = "service"
    CUSTOM = "custom"


class MarketCondition(Enum):
    """Market condition states."""
    BULLISH = "bullish"          # Strong upward trend
    BEARISH = "bearish"          # Strong downward trend
    NEUTRAL = "neutral"          # Sideways/stable
    VOLATILE = "volatile"        # High volatility, no clear direction
    TRENDING_UP = "trending_up"  # Moderate upward
    TRENDING_DOWN = "trending_down"  # Moderate downward


class PricingStrategy(Enum):
    """Pricing strategies for negotiations."""
    MARKET = "market"            # Follow market price
    PREMIUM = "premium"          # Above market
    DISCOUNT = "discount"        # Below market
    ANCHORED = "anchored"        # Based on anchor price
    COMPETITIVE = "competitive"  # Based on competitor pricing
    VALUE_BASED = "value_based"  # Based on value analysis


class TrendDirection(Enum):
    """Price trend direction."""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


# ============================================================
# Data Classes
# ============================================================

@dataclass
class PriceData:
    """Real-time price data point."""
    asset: str
    asset_class: AssetClass
    price: float
    currency: str
    timestamp: str
    source: str
    bid: float | None = None
    ask: float | None = None
    volume_24h: float | None = None
    change_24h: float | None = None
    change_7d: float | None = None
    market_cap: float | None = None


@dataclass
class HistoricalPrice:
    """Historical price entry."""
    asset: str
    price: float
    timestamp: str
    volume: float | None = None


@dataclass
class MarketAnalysis:
    """Market analysis result."""
    asset: str
    condition: MarketCondition
    trend: TrendDirection
    volatility: float  # 0-1 scale
    support_level: float | None = None
    resistance_level: float | None = None
    fair_value: float | None = None
    confidence: float = 0.5
    analysis_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class PriceSuggestion:
    """Price suggestion for negotiation."""
    suggestion_id: str
    asset_or_service: str
    suggested_price: float
    currency: str
    price_range: tuple[float, float]  # (min, max)
    market_price: float | None = None
    strategy: PricingStrategy = PricingStrategy.MARKET
    confidence: float = 0.5
    reasoning: str = ""
    valid_until: str = field(default_factory=lambda: (datetime.utcnow() + timedelta(hours=1)).isoformat())


# ============================================================
# Market Data Oracle
# ============================================================

class MarketDataOracle:
    """
    Oracle for real-time market data.

    In production, this would integrate with:
    - Chainlink price feeds
    - CoinGecko/CoinMarketCap APIs
    - Traditional market data providers (Bloomberg, Reuters)
    - DEX aggregators for on-chain pricing

    This implementation provides a simulation layer with
    realistic market behavior for development and testing.
    """

    # Simulated base prices (would come from real APIs in production)
    BASE_PRICES = {
        # Crypto
        "BTC": {"price": 42000.0, "class": AssetClass.CRYPTO, "volatility": 0.03},
        "ETH": {"price": 2200.0, "class": AssetClass.CRYPTO, "volatility": 0.04},
        "SOL": {"price": 95.0, "class": AssetClass.CRYPTO, "volatility": 0.05},
        "MATIC": {"price": 0.85, "class": AssetClass.CRYPTO, "volatility": 0.04},

        # Forex
        "EUR/USD": {"price": 1.08, "class": AssetClass.FOREX, "volatility": 0.005},
        "GBP/USD": {"price": 1.26, "class": AssetClass.FOREX, "volatility": 0.006},
        "USD/JPY": {"price": 148.5, "class": AssetClass.FOREX, "volatility": 0.004},

        # Commodities
        "GOLD": {"price": 2050.0, "class": AssetClass.COMMODITY, "volatility": 0.01},
        "SILVER": {"price": 23.5, "class": AssetClass.COMMODITY, "volatility": 0.02},
        "OIL": {"price": 78.0, "class": AssetClass.COMMODITY, "volatility": 0.025},

        # Equities (indices as proxy)
        "SPX": {"price": 4780.0, "class": AssetClass.EQUITY, "volatility": 0.012},
        "NDX": {"price": 16800.0, "class": AssetClass.EQUITY, "volatility": 0.015},
    }

    def __init__(self):
        """Initialize market data oracle."""
        self.price_cache: dict[str, PriceData] = {}
        self.historical_data: dict[str, list[HistoricalPrice]] = {}
        self.last_update: dict[str, datetime] = {}
        self.subscriptions: list[str] = []

        # Initialize with base prices
        self._initialize_prices()

    def _initialize_prices(self):
        """Initialize price cache with base prices."""
        for asset, data in self.BASE_PRICES.items():
            price = self._simulate_price_movement(data["price"], data["volatility"])
            self.price_cache[asset] = PriceData(
                asset=asset,
                asset_class=data["class"],
                price=price,
                currency="USD",
                timestamp=datetime.utcnow().isoformat(),
                source="simulated_oracle",
                bid=price * 0.999,
                ask=price * 1.001,
                change_24h=random.uniform(-5, 5),
                change_7d=random.uniform(-10, 10)
            )
            self.last_update[asset] = datetime.utcnow()

            # Initialize historical data
            self._generate_historical_data(asset, data["price"], data["volatility"])

    def _simulate_price_movement(self, base_price: float, volatility: float) -> float:
        """Simulate realistic price movement."""
        # Random walk with mean reversion
        change = random.gauss(0, volatility)
        return base_price * (1 + change)

    def _generate_historical_data(self, asset: str, base_price: float, volatility: float):
        """Generate simulated historical price data."""
        self.historical_data[asset] = []
        current_price = base_price

        # Generate 30 days of hourly data
        for hours_ago in range(30 * 24, 0, -1):
            timestamp = (datetime.utcnow() - timedelta(hours=hours_ago)).isoformat()
            current_price = self._simulate_price_movement(current_price, volatility / 10)
            self.historical_data[asset].append(HistoricalPrice(
                asset=asset,
                price=current_price,
                timestamp=timestamp,
                volume=random.uniform(1000000, 10000000)
            ))

    def get_price(self, asset: str) -> PriceData | None:
        """
        Get current price for an asset.

        Args:
            asset: Asset symbol (e.g., "BTC", "EUR/USD")

        Returns:
            Current price data or None if not found
        """
        asset = asset.upper()

        if asset not in self.price_cache:
            return None

        # Update price if stale (> 1 minute)
        if asset in self.last_update:
            elapsed = (datetime.utcnow() - self.last_update[asset]).total_seconds()
            if elapsed > 60:
                self._refresh_price(asset)

        return self.price_cache.get(asset)

    def _refresh_price(self, asset: str):
        """Refresh price for an asset."""
        if asset not in self.BASE_PRICES:
            return

        base_data = self.BASE_PRICES[asset]
        old_price = self.price_cache[asset].price if asset in self.price_cache else base_data["price"]

        # Simulate price movement from current price
        new_price = self._simulate_price_movement(old_price, base_data["volatility"] / 10)

        self.price_cache[asset] = PriceData(
            asset=asset,
            asset_class=base_data["class"],
            price=new_price,
            currency="USD",
            timestamp=datetime.utcnow().isoformat(),
            source="simulated_oracle",
            bid=new_price * 0.999,
            ask=new_price * 1.001,
            change_24h=((new_price / self._get_price_24h_ago(asset)) - 1) * 100 if self._get_price_24h_ago(asset) else 0,
            change_7d=((new_price / self._get_price_7d_ago(asset)) - 1) * 100 if self._get_price_7d_ago(asset) else 0
        )
        self.last_update[asset] = datetime.utcnow()

    def _get_price_24h_ago(self, asset: str) -> float | None:
        """Get price from 24 hours ago."""
        if asset not in self.historical_data:
            return None
        hist = self.historical_data[asset]
        if len(hist) >= 24:
            return hist[-24].price
        return hist[0].price if hist else None

    def _get_price_7d_ago(self, asset: str) -> float | None:
        """Get price from 7 days ago."""
        if asset not in self.historical_data:
            return None
        hist = self.historical_data[asset]
        if len(hist) >= 168:  # 7 * 24
            return hist[-168].price
        return hist[0].price if hist else None

    def get_prices(self, assets: list[str]) -> dict[str, PriceData]:
        """Get prices for multiple assets."""
        return {
            asset: self.get_price(asset)
            for asset in assets
            if self.get_price(asset) is not None
        }

    def get_historical_prices(
        self,
        asset: str,
        hours: int = 24
    ) -> list[HistoricalPrice]:
        """
        Get historical prices for an asset.

        Args:
            asset: Asset symbol
            hours: Number of hours of history

        Returns:
            List of historical prices
        """
        asset = asset.upper()
        if asset not in self.historical_data:
            return []

        return self.historical_data[asset][-hours:]

    def add_custom_asset(
        self,
        asset: str,
        price: float,
        asset_class: AssetClass,
        currency: str = "USD",
        volatility: float = 0.02
    ):
        """
        Add a custom asset for pricing.

        Args:
            asset: Asset symbol
            price: Current price
            asset_class: Asset class
            currency: Price currency
            volatility: Expected volatility
        """
        asset = asset.upper()
        self.BASE_PRICES[asset] = {
            "price": price,
            "class": asset_class,
            "volatility": volatility
        }

        self.price_cache[asset] = PriceData(
            asset=asset,
            asset_class=asset_class,
            price=price,
            currency=currency,
            timestamp=datetime.utcnow().isoformat(),
            source="custom"
        )
        self.last_update[asset] = datetime.utcnow()
        self._generate_historical_data(asset, price, volatility)

    def get_available_assets(self) -> list[dict[str, Any]]:
        """Get list of available assets."""
        return [
            {
                "asset": asset,
                "class": data["class"].value,
                "has_price": asset in self.price_cache
            }
            for asset, data in self.BASE_PRICES.items()
        ]


# ============================================================
# Market Analyzer
# ============================================================

class MarketAnalyzer:
    """
    Analyzes market conditions and trends.

    Provides:
    - Trend analysis
    - Volatility calculation
    - Support/resistance levels
    - Market condition assessment
    """

    def __init__(self, oracle: MarketDataOracle, client=None):
        """
        Initialize market analyzer.

        Args:
            oracle: Market data oracle
            client: Anthropic client for LLM analysis
        """
        self.oracle = oracle
        self.client = client
        self.model = "claude-3-5-sonnet-20241022"
        self.analysis_cache: dict[str, MarketAnalysis] = {}

    def analyze_market(self, asset: str) -> MarketAnalysis:
        """
        Perform comprehensive market analysis.

        Args:
            asset: Asset to analyze

        Returns:
            Market analysis result
        """
        asset = asset.upper()
        historical = self.oracle.get_historical_prices(asset, hours=168)  # 7 days

        if not historical:
            return MarketAnalysis(
                asset=asset,
                condition=MarketCondition.NEUTRAL,
                trend=TrendDirection.STABLE,
                volatility=0.5,
                confidence=0.1
            )

        # Calculate metrics
        prices = [h.price for h in historical]
        volatility = self._calculate_volatility(prices)
        trend = self._determine_trend(prices)
        condition = self._assess_condition(prices, volatility, trend)
        support, resistance = self._find_support_resistance(prices)

        analysis = MarketAnalysis(
            asset=asset,
            condition=condition,
            trend=trend,
            volatility=volatility,
            support_level=support,
            resistance_level=resistance,
            fair_value=self._estimate_fair_value(prices),
            confidence=0.7
        )

        self.analysis_cache[asset] = analysis
        return analysis

    def _calculate_volatility(self, prices: list[float]) -> float:
        """Calculate price volatility (0-1 scale)."""
        if len(prices) < 2:
            return 0.5

        # Calculate returns
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]

        # Standard deviation of returns
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)

        # Normalize to 0-1 scale (typical crypto volatility ~0.03-0.10 daily)
        normalized = min(std_dev * 10, 1.0)
        return normalized

    def _determine_trend(self, prices: list[float]) -> TrendDirection:
        """Determine price trend direction."""
        if len(prices) < 10:
            return TrendDirection.STABLE

        # Compare recent average to older average
        recent = sum(prices[-10:]) / 10
        older = sum(prices[:10]) / 10

        change_pct = (recent - older) / older

        if change_pct > 0.02:
            return TrendDirection.UP
        elif change_pct < -0.02:
            return TrendDirection.DOWN
        else:
            return TrendDirection.STABLE

    def _assess_condition(
        self,
        prices: list[float],
        volatility: float,
        trend: TrendDirection
    ) -> MarketCondition:
        """Assess overall market condition."""
        if volatility > 0.7:
            return MarketCondition.VOLATILE

        if trend == TrendDirection.UP:
            if volatility > 0.4:
                return MarketCondition.TRENDING_UP
            else:
                return MarketCondition.BULLISH
        elif trend == TrendDirection.DOWN:
            if volatility > 0.4:
                return MarketCondition.TRENDING_DOWN
            else:
                return MarketCondition.BEARISH
        else:
            return MarketCondition.NEUTRAL

    def _find_support_resistance(self, prices: list[float]) -> tuple[float, float]:
        """Find support and resistance levels."""
        if not prices:
            return (0.0, 0.0)

        # Simple: min and max of recent prices
        recent = prices[-48:] if len(prices) >= 48 else prices  # Last 48 hours
        support = min(recent)
        resistance = max(recent)

        return (support, resistance)

    def _estimate_fair_value(self, prices: list[float]) -> float:
        """Estimate fair value using moving average."""
        if not prices:
            return 0.0

        # Simple moving average
        return sum(prices) / len(prices)

    def get_market_summary(self, assets: list[str]) -> dict[str, Any]:
        """
        Get market summary for multiple assets.

        Args:
            assets: List of assets

        Returns:
            Summary with analysis for each asset
        """
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "assets": {}
        }

        for asset in assets:
            analysis = self.analyze_market(asset)
            price_data = self.oracle.get_price(asset)

            summary["assets"][asset] = {
                "price": price_data.price if price_data else None,
                "condition": analysis.condition.value,
                "trend": analysis.trend.value,
                "volatility": analysis.volatility,
                "support": analysis.support_level,
                "resistance": analysis.resistance_level
            }

        return summary


# ============================================================
# Dynamic Pricing Engine
# ============================================================

class DynamicPricingEngine:
    """
    Generates market-aware prices for negotiations.

    Features:
    - Market-adjusted pricing
    - Strategy-based price generation
    - Price range calculation
    - Volatility-aware adjustments
    """

    def __init__(self, oracle: MarketDataOracle, analyzer: MarketAnalyzer, client=None):
        """
        Initialize pricing engine.

        Args:
            oracle: Market data oracle
            analyzer: Market analyzer
            client: Anthropic client for LLM-based pricing
        """
        self.oracle = oracle
        self.analyzer = analyzer
        self.client = client
        self.model = "claude-3-5-sonnet-20241022"

    def generate_price_suggestion(
        self,
        asset_or_service: str,
        base_amount: float,
        currency: str = "USD",
        strategy: PricingStrategy = PricingStrategy.MARKET,
        context: str | None = None
    ) -> PriceSuggestion:
        """
        Generate a price suggestion for a negotiation.

        Args:
            asset_or_service: What is being priced
            base_amount: Base amount/quantity
            currency: Pricing currency
            strategy: Pricing strategy to use
            context: Optional negotiation context

        Returns:
            Price suggestion with range
        """
        suggestion_id = f"PRICE-{secrets.token_hex(6).upper()}"

        # Try to get market price
        market_price = self._get_market_price(asset_or_service, base_amount, currency)
        analysis = self.analyzer.analyze_market(asset_or_service) if market_price else None

        # Calculate suggested price based on strategy
        suggested_price, price_range = self._calculate_price(
            base_amount=base_amount,
            market_price=market_price,
            analysis=analysis,
            strategy=strategy
        )

        # Generate reasoning
        reasoning = self._generate_reasoning(
            asset_or_service=asset_or_service,
            suggested_price=suggested_price,
            market_price=market_price,
            strategy=strategy,
            analysis=analysis,
            context=context
        )

        return PriceSuggestion(
            suggestion_id=suggestion_id,
            asset_or_service=asset_or_service,
            suggested_price=suggested_price,
            currency=currency,
            price_range=price_range,
            market_price=market_price,
            strategy=strategy,
            confidence=0.7 if market_price else 0.4,
            reasoning=reasoning
        )

    def _get_market_price(
        self,
        asset_or_service: str,
        amount: float,
        currency: str
    ) -> float | None:
        """Get market price for asset or service."""
        # Try direct price lookup
        price_data = self.oracle.get_price(asset_or_service.upper())
        if price_data:
            return price_data.price * amount

        # For services, return None (need LLM estimation)
        return None

    def _calculate_price(
        self,
        base_amount: float,
        market_price: float | None,
        analysis: MarketAnalysis | None,
        strategy: PricingStrategy
    ) -> tuple[float, tuple[float, float]]:
        """Calculate suggested price and range."""
        if market_price is None:
            # No market price, use base amount with buffer
            suggested = base_amount
            range_buffer = 0.15
            return suggested, (suggested * (1 - range_buffer), suggested * (1 + range_buffer))

        # Adjust based on strategy
        if strategy == PricingStrategy.MARKET:
            suggested = market_price
        elif strategy == PricingStrategy.PREMIUM:
            suggested = market_price * 1.10  # 10% premium
        elif strategy == PricingStrategy.DISCOUNT:
            suggested = market_price * 0.90  # 10% discount
        elif strategy == PricingStrategy.COMPETITIVE:
            suggested = market_price * 0.95  # Slightly below market
        elif strategy == PricingStrategy.ANCHORED:
            suggested = base_amount  # Use the anchor
        else:  # VALUE_BASED
            if analysis and analysis.fair_value:
                suggested = analysis.fair_value * base_amount / market_price
            else:
                suggested = market_price

        # Calculate range based on volatility
        volatility = analysis.volatility if analysis else 0.1
        range_buffer = max(0.05, min(0.25, volatility * 2))

        return suggested, (suggested * (1 - range_buffer), suggested * (1 + range_buffer))

    def _generate_reasoning(
        self,
        asset_or_service: str,
        suggested_price: float,
        market_price: float | None,
        strategy: PricingStrategy,
        analysis: MarketAnalysis | None,
        context: str | None
    ) -> str:
        """Generate reasoning for price suggestion."""
        parts = []

        if market_price:
            parts.append(f"Market price for {asset_or_service}: {market_price:.2f}")

        if analysis:
            parts.append(f"Market condition: {analysis.condition.value}")
            parts.append(f"Trend: {analysis.trend.value}")
            parts.append(f"Volatility: {analysis.volatility:.1%}")

        parts.append(f"Strategy applied: {strategy.value}")

        if strategy == PricingStrategy.PREMIUM:
            parts.append("Premium pricing applied for value positioning")
        elif strategy == PricingStrategy.DISCOUNT:
            parts.append("Discount applied for competitive positioning")

        return ". ".join(parts)

    def adjust_price_for_conditions(
        self,
        base_price: float,
        asset: str,
        adjustment_type: str = "auto"
    ) -> tuple[float, str]:
        """
        Adjust a price based on current market conditions.

        Args:
            base_price: Starting price
            asset: Asset for context
            adjustment_type: "auto", "conservative", "aggressive"

        Returns:
            Tuple of (adjusted_price, adjustment_reason)
        """
        analysis = self.analyzer.analyze_market(asset)

        adjustment = 1.0
        reason = "No adjustment needed"

        # Apply condition-based adjustments
        if analysis.condition == MarketCondition.BULLISH:
            if adjustment_type in ["auto", "aggressive"]:
                adjustment = 1.05
                reason = "Bullish market - slight premium applied"
        elif analysis.condition == MarketCondition.BEARISH:
            if adjustment_type in ["auto", "aggressive"]:
                adjustment = 0.95
                reason = "Bearish market - slight discount applied"
        elif analysis.condition == MarketCondition.VOLATILE:
            if adjustment_type == "conservative":
                adjustment = 0.97
                reason = "Volatile market - conservative pricing"
            else:
                adjustment = 1.0
                reason = "Volatile market - holding steady"

        # Apply volatility buffer
        if analysis.volatility > 0.5 and adjustment_type == "conservative":
            adjustment *= 0.98
            reason += " with volatility buffer"

        adjusted_price = base_price * adjustment
        return adjusted_price, reason

    def generate_counteroffer_price(
        self,
        their_offer: float,
        your_target: float,
        asset: str,
        round_number: int,
        max_rounds: int = 10
    ) -> tuple[float, str]:
        """
        Generate a counter-offer price based on market conditions.

        Args:
            their_offer: Their proposed price
            your_target: Your target price
            asset: Asset being negotiated
            round_number: Current negotiation round
            max_rounds: Maximum rounds

        Returns:
            Tuple of (counter_price, reasoning)
        """
        analysis = self.analyzer.analyze_market(asset)

        # Calculate progress factor (how much to concede based on round)
        progress = round_number / max_rounds
        concession_rate = min(0.8, progress * 0.6)  # Max 80% concession at end

        # Direction of concession
        if your_target > their_offer:
            # They offered less than we want, counter higher
            gap = your_target - their_offer
            concession = gap * concession_rate

            # Adjust based on market
            if analysis.condition == MarketCondition.BULLISH:
                concession *= 0.8  # Less concession in bull market
            elif analysis.condition == MarketCondition.BEARISH:
                concession *= 1.2  # More concession in bear market

            counter_price = their_offer + (gap - concession)
            reasoning = f"Round {round_number}: Conceding {concession_rate:.0%} of gap"
        else:
            # They offered more than we want (rare), accept closer to their offer
            gap = their_offer - your_target
            counter_price = your_target + (gap * 0.5)
            reasoning = f"Round {round_number}: Meeting in favorable middle"

        # Add market context
        if analysis.condition != MarketCondition.NEUTRAL:
            reasoning += f" ({analysis.condition.value} market considered)"

        return counter_price, reasoning


# ============================================================
# Historical Pricing Analyzer
# ============================================================

class HistoricalPricingAnalyzer:
    """
    Analyzes historical pricing data.

    Provides:
    - Historical price lookup
    - Trend analysis
    - Volatility patterns
    - Price benchmarking
    """

    def __init__(self, oracle: MarketDataOracle):
        """Initialize historical analyzer."""
        self.oracle = oracle
        self.benchmark_cache: dict[str, dict[str, Any]] = {}

    def get_price_history(
        self,
        asset: str,
        period_hours: int = 168
    ) -> dict[str, Any]:
        """
        Get price history with statistics.

        Args:
            asset: Asset symbol
            period_hours: Hours of history

        Returns:
            History with statistics
        """
        historical = self.oracle.get_historical_prices(asset, hours=period_hours)

        if not historical:
            return {"error": "No historical data available"}

        prices = [h.price for h in historical]

        return {
            "asset": asset,
            "period_hours": period_hours,
            "data_points": len(historical),
            "statistics": {
                "current": prices[-1] if prices else None,
                "high": max(prices),
                "low": min(prices),
                "average": sum(prices) / len(prices),
                "median": sorted(prices)[len(prices) // 2],
                "std_dev": self._calculate_std_dev(prices),
                "change_percent": ((prices[-1] - prices[0]) / prices[0] * 100) if prices else 0
            },
            "prices": [
                {"timestamp": h.timestamp, "price": h.price}
                for h in historical[-24:]  # Last 24 entries
            ]
        }

    def _calculate_std_dev(self, prices: list[float]) -> float:
        """Calculate standard deviation."""
        if len(prices) < 2:
            return 0.0
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        return math.sqrt(variance)

    def calculate_price_benchmark(
        self,
        asset: str,
        benchmark_period_days: int = 30
    ) -> dict[str, Any]:
        """
        Calculate price benchmark against historical data.

        Args:
            asset: Asset to benchmark
            benchmark_period_days: Days of history for benchmark

        Returns:
            Benchmark analysis
        """
        hours = benchmark_period_days * 24
        historical = self.oracle.get_historical_prices(asset, hours=hours)
        current = self.oracle.get_price(asset)

        if not historical or not current:
            return {"error": "Insufficient data"}

        prices = [h.price for h in historical]
        avg_price = sum(prices) / len(prices)

        percentile = sum(1 for p in prices if p <= current.price) / len(prices) * 100

        return {
            "asset": asset,
            "current_price": current.price,
            "benchmark_average": avg_price,
            "vs_average_percent": ((current.price - avg_price) / avg_price) * 100,
            "percentile": percentile,
            "interpretation": self._interpret_percentile(percentile),
            "period_days": benchmark_period_days
        }

    def _interpret_percentile(self, percentile: float) -> str:
        """Interpret price percentile."""
        if percentile < 10:
            return "Near historical lows - potentially undervalued"
        elif percentile < 30:
            return "Below average - value opportunity"
        elif percentile < 50:
            return "Slightly below average"
        elif percentile < 70:
            return "Above average"
        elif percentile < 90:
            return "Near historical highs - premium territory"
        else:
            return "At historical highs - caution advised"

    def find_similar_price_periods(
        self,
        asset: str,
        target_price: float,
        tolerance: float = 0.05
    ) -> list[dict[str, Any]]:
        """
        Find historical periods with similar prices.

        Args:
            asset: Asset to search
            target_price: Price to match
            tolerance: Price tolerance (e.g., 0.05 = 5%)

        Returns:
            List of matching periods
        """
        historical = self.oracle.get_historical_prices(asset, hours=720)  # 30 days

        if not historical:
            return []

        matches = []
        lower_bound = target_price * (1 - tolerance)
        upper_bound = target_price * (1 + tolerance)

        for h in historical:
            if lower_bound <= h.price <= upper_bound:
                matches.append({
                    "timestamp": h.timestamp,
                    "price": h.price,
                    "difference_percent": ((h.price - target_price) / target_price) * 100
                })

        return matches[-10:]  # Return last 10 matches


# ============================================================
# Main Market-Aware Pricing Manager
# ============================================================

class MarketAwarePricingManager:
    """
    Main manager for market-aware pricing.

    Coordinates oracle, analysis, and pricing components.
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize pricing manager.

        Args:
            api_key: Anthropic API key for LLM features
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = None

        if self.api_key and HAS_ANTHROPIC:
            self.client = Anthropic(api_key=self.api_key)

        # Initialize components
        self.oracle = MarketDataOracle()
        self.analyzer = MarketAnalyzer(self.oracle, self.client)
        self.pricing_engine = DynamicPricingEngine(self.oracle, self.analyzer, self.client)
        self.historical_analyzer = HistoricalPricingAnalyzer(self.oracle)

        self.audit_trail: list[dict[str, Any]] = []

    # ===== Price Data =====

    def get_price(self, asset: str) -> dict[str, Any] | None:
        """Get current price for an asset."""
        price_data = self.oracle.get_price(asset)
        if not price_data:
            return None

        return {
            "asset": price_data.asset,
            "price": price_data.price,
            "currency": price_data.currency,
            "bid": price_data.bid,
            "ask": price_data.ask,
            "change_24h": price_data.change_24h,
            "change_7d": price_data.change_7d,
            "timestamp": price_data.timestamp,
            "source": price_data.source
        }

    def get_prices(self, assets: list[str]) -> dict[str, Any]:
        """Get prices for multiple assets."""
        result = {}
        for asset in assets:
            price = self.get_price(asset)
            if price:
                result[asset] = price
        return result

    # ===== Market Analysis =====

    def analyze_market(self, asset: str) -> dict[str, Any]:
        """Get market analysis for an asset."""
        analysis = self.analyzer.analyze_market(asset)

        return {
            "asset": analysis.asset,
            "condition": analysis.condition.value,
            "trend": analysis.trend.value,
            "volatility": analysis.volatility,
            "support_level": analysis.support_level,
            "resistance_level": analysis.resistance_level,
            "fair_value": analysis.fair_value,
            "confidence": analysis.confidence,
            "timestamp": analysis.analysis_timestamp
        }

    def get_market_summary(self, assets: list[str]) -> dict[str, Any]:
        """Get market summary for multiple assets."""
        return self.analyzer.get_market_summary(assets)

    # ===== Pricing =====

    def suggest_price(
        self,
        asset_or_service: str,
        base_amount: float,
        currency: str = "USD",
        strategy: str = "market",
        context: str | None = None
    ) -> dict[str, Any]:
        """
        Get a price suggestion.

        Args:
            asset_or_service: What to price
            base_amount: Base amount
            currency: Currency
            strategy: Pricing strategy
            context: Optional context

        Returns:
            Price suggestion
        """
        try:
            pricing_strategy = PricingStrategy(strategy)
        except ValueError:
            pricing_strategy = PricingStrategy.MARKET

        suggestion = self.pricing_engine.generate_price_suggestion(
            asset_or_service=asset_or_service,
            base_amount=base_amount,
            currency=currency,
            strategy=pricing_strategy,
            context=context
        )

        self._log_audit("price_suggested", {
            "suggestion_id": suggestion.suggestion_id,
            "asset": asset_or_service,
            "suggested_price": suggestion.suggested_price
        })

        return {
            "suggestion_id": suggestion.suggestion_id,
            "asset_or_service": suggestion.asset_or_service,
            "suggested_price": suggestion.suggested_price,
            "currency": suggestion.currency,
            "price_range": {
                "min": suggestion.price_range[0],
                "max": suggestion.price_range[1]
            },
            "market_price": suggestion.market_price,
            "strategy": suggestion.strategy.value,
            "confidence": suggestion.confidence,
            "reasoning": suggestion.reasoning,
            "valid_until": suggestion.valid_until
        }

    def adjust_price(
        self,
        base_price: float,
        asset: str,
        adjustment_type: str = "auto"
    ) -> dict[str, Any]:
        """
        Adjust a price based on market conditions.

        Args:
            base_price: Starting price
            asset: Asset for context
            adjustment_type: Type of adjustment

        Returns:
            Adjusted price with reasoning
        """
        adjusted, reason = self.pricing_engine.adjust_price_for_conditions(
            base_price, asset, adjustment_type
        )

        return {
            "original_price": base_price,
            "adjusted_price": adjusted,
            "adjustment_percent": ((adjusted - base_price) / base_price) * 100,
            "reason": reason,
            "asset_context": asset
        }

    def generate_counteroffer(
        self,
        their_offer: float,
        your_target: float,
        asset: str,
        round_number: int,
        max_rounds: int = 10
    ) -> dict[str, Any]:
        """
        Generate a market-aware counter-offer price.

        Args:
            their_offer: Their offer
            your_target: Your target
            asset: Asset context
            round_number: Current round
            max_rounds: Maximum rounds

        Returns:
            Counter-offer with reasoning
        """
        counter, reasoning = self.pricing_engine.generate_counteroffer_price(
            their_offer, your_target, asset, round_number, max_rounds
        )

        self._log_audit("counteroffer_generated", {
            "their_offer": their_offer,
            "counter": counter,
            "round": round_number
        })

        return {
            "their_offer": their_offer,
            "your_target": your_target,
            "counter_offer": counter,
            "reasoning": reasoning,
            "round": round_number,
            "max_rounds": max_rounds,
            "gap_remaining": abs(counter - their_offer)
        }

    # ===== Historical Analysis =====

    def get_price_history(
        self,
        asset: str,
        period_hours: int = 168
    ) -> dict[str, Any]:
        """Get price history with statistics."""
        return self.historical_analyzer.get_price_history(asset, period_hours)

    def get_price_benchmark(
        self,
        asset: str,
        benchmark_days: int = 30
    ) -> dict[str, Any]:
        """Get price benchmark analysis."""
        return self.historical_analyzer.calculate_price_benchmark(asset, benchmark_days)

    def find_similar_prices(
        self,
        asset: str,
        target_price: float,
        tolerance: float = 0.05
    ) -> dict[str, Any]:
        """Find historical periods with similar prices."""
        matches = self.historical_analyzer.find_similar_price_periods(
            asset, target_price, tolerance
        )

        return {
            "asset": asset,
            "target_price": target_price,
            "tolerance_percent": tolerance * 100,
            "matches_found": len(matches),
            "matches": matches
        }

    # ===== Custom Assets =====

    def add_custom_asset(
        self,
        asset: str,
        price: float,
        asset_class: str = "custom",
        currency: str = "USD",
        volatility: float = 0.02
    ) -> dict[str, Any]:
        """Add a custom asset for pricing."""
        try:
            ac = AssetClass(asset_class)
        except ValueError:
            ac = AssetClass.CUSTOM

        self.oracle.add_custom_asset(asset, price, ac, currency, volatility)

        return {
            "status": "added",
            "asset": asset.upper(),
            "price": price,
            "asset_class": ac.value,
            "currency": currency
        }

    def get_available_assets(self) -> list[dict[str, Any]]:
        """Get list of available assets."""
        return self.oracle.get_available_assets()

    # ===== Statistics =====

    def get_statistics(self) -> dict[str, Any]:
        """Get pricing manager statistics."""
        return {
            "available_assets": len(self.oracle.BASE_PRICES),
            "cached_prices": len(self.oracle.price_cache),
            "cached_analyses": len(self.analyzer.analysis_cache),
            "pricing_strategies": [s.value for s in PricingStrategy],
            "asset_classes": [c.value for c in AssetClass]
        }

    def get_audit_trail(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get audit trail."""
        return self.audit_trail[-limit:]

    def _log_audit(self, action: str, details: dict[str, Any]):
        """Log audit trail entry."""
        self.audit_trail.append({
            "action": action,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })
