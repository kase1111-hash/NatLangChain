"""A virtual clock for long-horizon simulation.

`src/blockchain.py` reads wall-clock time from two places:

* the module-level ``time`` import (rate limiter windows, dedup fingerprint
  expiry, ``Block.timestamp``, asset transfer history)
* the module-level ``datetime`` import (``NaturalLanguageEntry.timestamp`` and
  the backdating/future-drift checks in ``_validate_timestamp``)

To simulate a year in seconds of real runtime we replace both with a clock we
control. Patching both together keeps the engine internally consistent: an
entry stamped at virtual T is checked against a virtual "now" of T, so the
±300s drift window behaves exactly as it would in production.

Nothing else about the engine is stubbed. Hashing, proof-of-work, validation,
the registries, and persistence all run for real.
"""

from __future__ import annotations

import time as _real_time
from contextlib import contextmanager
from datetime import datetime, timezone


class VirtualClock:
    """A monotonic clock the simulation advances explicitly."""

    def __init__(self, start_epoch: float):
        self._now = float(start_epoch)
        self.advance_count = 0

    # -- reading -----------------------------------------------------------
    def time(self) -> float:
        """Drop-in replacement for ``time.time()``."""
        return self._now

    def utcnow(self) -> datetime:
        """Drop-in replacement for ``datetime.utcnow()``."""
        # timezone.utc, not datetime.UTC: this project supports Python 3.9+.
        return datetime.fromtimestamp(self._now, tz=timezone.utc).replace(tzinfo=None)  # noqa: UP017

    def isoformat(self) -> str:
        return self.utcnow().isoformat()

    def date_str(self) -> str:
        return self.utcnow().strftime("%Y-%m-%d")

    # -- writing -----------------------------------------------------------
    def advance(self, seconds: float) -> float:
        """Move the clock forward. Time never runs backwards."""
        if seconds < 0:
            raise ValueError("VirtualClock only moves forward")
        self._now += seconds
        self.advance_count += 1
        return self._now

    def set(self, epoch: float) -> None:
        """Jump to an absolute epoch (used only for adversarial clock tests)."""
        self._now = float(epoch)


def _make_virtual_datetime(clock: VirtualClock):
    """Build a ``datetime`` subclass whose ``utcnow()`` reads the virtual clock.

    Subclassing keeps ``fromisoformat``, arithmetic, and comparison intact, so
    the engine's timestamp math is unchanged.
    """

    class VirtualDatetime(datetime):
        @classmethod
        def utcnow(cls) -> datetime:  # type: ignore[override]
            return clock.utcnow()

        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            if tz is None:
                return clock.utcnow()
            return datetime.fromtimestamp(clock.time(), tz=tz)

    VirtualDatetime.__name__ = "VirtualDatetime"
    return VirtualDatetime


class _TimeModuleShim:
    """Proxies the real ``time`` module but serves ``time()`` from the clock."""

    def __init__(self, clock: VirtualClock):
        self._clock = clock

    def time(self) -> float:
        return self._clock.time()

    def __getattr__(self, name):  # pragma: no cover - passthrough
        return getattr(_real_time, name)


@contextmanager
def virtual_time(module, clock: VirtualClock):
    """Temporarily point ``module``'s time sources at ``clock``.

    Usage::

        import blockchain
        with virtual_time(blockchain, clock):
            ...  # engine now runs on simulated time
    """
    original_time = getattr(module, "time", None)
    original_datetime = getattr(module, "datetime", None)

    module.time = _TimeModuleShim(clock)
    module.datetime = _make_virtual_datetime(clock)
    try:
        yield clock
    finally:
        if original_time is not None:
            module.time = original_time
        if original_datetime is not None:
            module.datetime = original_datetime
