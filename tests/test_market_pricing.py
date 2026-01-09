"""
Tests for Market-Aware Pricing Engine (src/market_pricing.py)

Tests cover:
- Market Data Oracle
- Market Analyzer
- Dynamic Pricing Engine
- Price Suggestions
"""

import sys
from datetime import datetime

import pytest

sys.path.insert(0, "src")

from market_pricing import (
    AssetClass,
    HistoricalPrice,
    MarketAnalysis,
    MarketAnalyzer,
    MarketCondition,
    MarketDataOracle,
    PriceData,
    PriceSuggestion,
    PricingStrategy,
    TrendDirection,
)

# ============================================================
# Market Data Oracle Tests
# ============================================================


class TestMarketDataOracle:
    """Tests for MarketDataOracle."""

    @pytest.fixture
    def oracle(self):
        """Create fresh oracle instance."""
        return MarketDataOracle()

    def test_initialization(self, oracle):
        """Oracle should initialize with base prices."""
        assert len(oracle.price_cache) > 0
        assert "BTC" in oracle.price_cache
        assert "ETH" in oracle.price_cache

    def test_get_price_btc(self, oracle):
        """Should return BTC price data."""
        price = oracle.get_price("BTC")

        assert price is not None
        assert isinstance(price, PriceData)
        assert price.asset == "BTC"
        assert price.asset_class == AssetClass.CRYPTO
        assert price.price > 0
        assert price.currency == "USD"

    def test_get_price_case_insensitive(self, oracle):
        """Should handle case insensitivity."""
        price1 = oracle.get_price("btc")
        price2 = oracle.get_price("BTC")
        price3 = oracle.get_price("Btc")

        assert price1 is not None
        assert price1.asset == price2.asset == price3.asset

    def test_get_price_nonexistent(self, oracle):
        """Should return None for unknown asset."""
        price = oracle.get_price("UNKNOWN_ASSET")
        assert price is None

    def test_get_price_forex(self, oracle):
        """Should return forex price data."""
        price = oracle.get_price("EUR/USD")

        assert price is not None
        assert price.asset_class == AssetClass.FOREX
        assert 0.5 < price.price < 2.0  # Reasonable forex range

    def test_get_price_commodity(self, oracle):
        """Should return commodity price data."""
        price = oracle.get_price("GOLD")

        assert price is not None
        assert price.asset_class == AssetClass.COMMODITY
        assert price.price > 1000  # Gold is > $1000/oz

    def test_get_prices_multiple(self, oracle):
        """Should return multiple prices."""
        prices = oracle.get_prices(["BTC", "ETH", "GOLD"])

        assert len(prices) == 3
        assert "BTC" in prices
        assert "ETH" in prices
        assert "GOLD" in prices

    def test_get_prices_partial(self, oracle):
        """Should return only valid assets."""
        prices = oracle.get_prices(["BTC", "INVALID", "ETH"])

        assert len(prices) == 2
        assert "INVALID" not in prices

    def test_get_historical_prices(self, oracle):
        """Should return historical price data."""
        history = oracle.get_historical_prices("BTC", hours=24)

        assert len(history) > 0
        assert len(history) <= 24
        assert all(isinstance(h, HistoricalPrice) for h in history)

    def test_get_historical_prices_nonexistent(self, oracle):
        """Should return empty list for unknown asset."""
        history = oracle.get_historical_prices("UNKNOWN")
        assert history == []

    def test_add_custom_asset(self, oracle):
        """Should add custom asset."""
        oracle.add_custom_asset(
            asset="CUSTOM", price=100.0, asset_class=AssetClass.CUSTOM, volatility=0.05
        )

        price = oracle.get_price("CUSTOM")
        assert price is not None
        assert price.price == 100.0
        assert price.asset_class == AssetClass.CUSTOM

    def test_get_available_assets(self, oracle):
        """Should list available assets."""
        assets = oracle.get_available_assets()

        assert len(assets) > 0
        assert any(a["asset"] == "BTC" for a in assets)

        # Check structure
        sample = assets[0]
        assert "asset" in sample
        assert "class" in sample
        assert "has_price" in sample

    def test_price_bid_ask_spread(self, oracle):
        """Price should have bid/ask spread."""
        price = oracle.get_price("BTC")

        assert price.bid is not None
        assert price.ask is not None
        assert price.bid < price.ask
        assert price.bid < price.price < price.ask

    def test_price_has_change_metrics(self, oracle):
        """Price should have change metrics."""
        price = oracle.get_price("BTC")

        assert price.change_24h is not None
        assert price.change_7d is not None
        # Changes should be percentages, roughly -100 to +100 range
        assert -100 <= price.change_24h <= 100


# ============================================================
# Market Analyzer Tests
# ============================================================


class TestMarketAnalyzer:
    """Tests for MarketAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        """Create fresh analyzer with oracle."""
        oracle = MarketDataOracle()
        return MarketAnalyzer(oracle)

    def test_analyze_market_btc(self, analyzer):
        """Should analyze BTC market."""
        analysis = analyzer.analyze_market("BTC")

        assert isinstance(analysis, MarketAnalysis)
        assert analysis.asset == "BTC"
        assert isinstance(analysis.condition, MarketCondition)
        assert isinstance(analysis.trend, TrendDirection)
        assert 0 <= analysis.volatility <= 1
        assert 0 <= analysis.confidence <= 1

    def test_analyze_market_unknown(self, analyzer):
        """Should handle unknown asset gracefully."""
        analysis = analyzer.analyze_market("UNKNOWN")

        assert analysis.condition == MarketCondition.NEUTRAL
        assert analysis.trend == TrendDirection.STABLE
        assert analysis.confidence < 0.5

    def test_analyze_market_caches_result(self, analyzer):
        """Should cache analysis results."""
        analysis1 = analyzer.analyze_market("ETH")

        assert "ETH" in analyzer.analysis_cache
        assert analyzer.analysis_cache["ETH"] == analysis1

    def test_volatility_calculation(self, analyzer):
        """Volatility should be reasonable."""
        analysis = analyzer.analyze_market("BTC")

        # BTC typically has moderate-high volatility
        assert 0 < analysis.volatility < 1

    def test_support_resistance_levels(self, analyzer):
        """Should calculate support/resistance levels."""
        analysis = analyzer.analyze_market("BTC")

        if analysis.support_level and analysis.resistance_level:
            assert analysis.support_level < analysis.resistance_level

    def test_trend_direction_values(self, analyzer):
        """Trend should be valid enum value."""
        analysis = analyzer.analyze_market("ETH")

        assert analysis.trend in [TrendDirection.UP, TrendDirection.DOWN, TrendDirection.STABLE]

    def test_market_condition_values(self, analyzer):
        """Condition should be valid enum value."""
        analysis = analyzer.analyze_market("GOLD")

        assert analysis.condition in [
            MarketCondition.BULLISH,
            MarketCondition.BEARISH,
            MarketCondition.NEUTRAL,
            MarketCondition.VOLATILE,
            MarketCondition.TRENDING_UP,
            MarketCondition.TRENDING_DOWN,
        ]

    def test_fair_value_estimation(self, analyzer):
        """Should estimate fair value."""
        analysis = analyzer.analyze_market("BTC")

        if analysis.fair_value:
            # Fair value should be in reasonable range of current price
            current = analyzer.oracle.get_price("BTC").price
            assert 0.5 * current <= analysis.fair_value <= 2 * current


# ============================================================
# Data Class Tests
# ============================================================


class TestPriceData:
    """Tests for PriceData dataclass."""

    def test_create_price_data(self):
        """Should create PriceData instance."""
        price = PriceData(
            asset="TEST",
            asset_class=AssetClass.CRYPTO,
            price=100.0,
            currency="USD",
            timestamp=datetime.utcnow().isoformat(),
            source="test",
        )

        assert price.asset == "TEST"
        assert price.price == 100.0

    def test_optional_fields(self):
        """Optional fields should default to None."""
        price = PriceData(
            asset="TEST",
            asset_class=AssetClass.CRYPTO,
            price=100.0,
            currency="USD",
            timestamp=datetime.utcnow().isoformat(),
            source="test",
        )

        assert price.bid is None
        assert price.ask is None
        assert price.volume_24h is None


class TestHistoricalPrice:
    """Tests for HistoricalPrice dataclass."""

    def test_create_historical_price(self):
        """Should create HistoricalPrice instance."""
        hist = HistoricalPrice(asset="BTC", price=42000.0, timestamp=datetime.utcnow().isoformat())

        assert hist.asset == "BTC"
        assert hist.price == 42000.0


class TestMarketAnalysis:
    """Tests for MarketAnalysis dataclass."""

    def test_create_market_analysis(self):
        """Should create MarketAnalysis instance."""
        analysis = MarketAnalysis(
            asset="ETH", condition=MarketCondition.BULLISH, trend=TrendDirection.UP, volatility=0.3
        )

        assert analysis.asset == "ETH"
        assert analysis.condition == MarketCondition.BULLISH
        assert analysis.confidence == 0.5  # Default


class TestPriceSuggestion:
    """Tests for PriceSuggestion dataclass."""

    def test_create_price_suggestion(self):
        """Should create PriceSuggestion instance."""
        suggestion = PriceSuggestion(
            suggestion_id="SUG-001",
            asset_or_service="Web Development",
            suggested_price=5000.0,
            currency="USD",
            price_range=(4000.0, 6000.0),
        )

        assert suggestion.suggested_price == 5000.0
        assert suggestion.price_range[0] < suggestion.suggested_price < suggestion.price_range[1]


# ============================================================
# Enum Tests
# ============================================================


class TestEnums:
    """Tests for pricing enums."""

    def test_asset_class_values(self):
        """AssetClass should have expected values."""
        assert AssetClass.CRYPTO.value == "crypto"
        assert AssetClass.FOREX.value == "forex"
        assert AssetClass.COMMODITY.value == "commodity"
        assert AssetClass.EQUITY.value == "equity"
        assert AssetClass.SERVICE.value == "service"

    def test_market_condition_values(self):
        """MarketCondition should have expected values."""
        assert MarketCondition.BULLISH.value == "bullish"
        assert MarketCondition.BEARISH.value == "bearish"
        assert MarketCondition.VOLATILE.value == "volatile"

    def test_pricing_strategy_values(self):
        """PricingStrategy should have expected values."""
        assert PricingStrategy.MARKET.value == "market"
        assert PricingStrategy.PREMIUM.value == "premium"
        assert PricingStrategy.DISCOUNT.value == "discount"

    def test_trend_direction_values(self):
        """TrendDirection should have expected values."""
        assert TrendDirection.UP.value == "up"
        assert TrendDirection.DOWN.value == "down"
        assert TrendDirection.STABLE.value == "stable"


# ============================================================
# Integration Tests
# ============================================================


class TestMarketPricingIntegration:
    """Integration tests for market pricing components."""

    def test_full_price_analysis_workflow(self):
        """Test complete price analysis workflow."""
        # 1. Create oracle with prices
        oracle = MarketDataOracle()

        # 2. Add custom asset for service pricing
        oracle.add_custom_asset(
            asset="CONSULTING_HOUR", price=150.0, asset_class=AssetClass.SERVICE, volatility=0.01
        )

        # 3. Get current prices
        btc_price = oracle.get_price("BTC")
        consulting_price = oracle.get_price("CONSULTING_HOUR")

        assert btc_price is not None
        assert consulting_price is not None

        # 4. Analyze market
        analyzer = MarketAnalyzer(oracle)
        btc_analysis = analyzer.analyze_market("BTC")

        assert btc_analysis.asset == "BTC"

        # 5. Get historical data
        history = oracle.get_historical_prices("BTC", hours=48)
        assert len(history) > 0

    def test_multi_asset_analysis(self):
        """Test analyzing multiple assets."""
        oracle = MarketDataOracle()
        analyzer = MarketAnalyzer(oracle)

        assets = ["BTC", "ETH", "GOLD", "EUR/USD"]
        analyses = {}

        for asset in assets:
            analyses[asset] = analyzer.analyze_market(asset)

        assert len(analyses) == 4
        assert all(a.asset in assets for a in analyses.values())

    def test_price_consistency(self):
        """Prices should be consistent across queries."""
        oracle = MarketDataOracle()

        # Get price multiple times quickly (should be cached)
        prices = [oracle.get_price("BTC").price for _ in range(5)]

        # Should be same value (from cache)
        assert len(set(prices)) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
