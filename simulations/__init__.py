"""Long-horizon operational simulations for NatLangChain.

These are not unit tests. They drive the real blockchain engine through a
compressed but continuous span of simulated operation (default: 365 days) to
surface behaviour that only appears with time, volume, and accumulated state:
rate-limit windows, deduplication expiry, registry growth, persistence
round-trips, restart recovery, and proof-of-work rewrite resistance.
"""

__all__ = ["virtual_clock", "workload", "year_simulation"]
