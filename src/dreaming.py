"""
NatLangChain - Dreaming Status Tracker

A lightweight status tracker that records what the system is doing.
Updates are throttled to reduce overhead - only the most recent
activity is tracked and returned.

Usage:
    from dreaming import dream, get_dream_status

    # Record an activity
    dream("Processing blockchain entry")

    # Later, mark it complete
    dream("Blockchain entry processed", completed=True)

    # Get current status
    status = get_dream_status()
"""

import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DreamState:
    """Current dreaming state."""
    message: str
    started_at: float
    completed: bool
    completed_at: Optional[float] = None


class DreamingTracker:
    """
    Tracks system activity with minimal overhead.

    Only stores the most recent activity to keep memory usage low.
    Thread-safe for concurrent access.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._current: Optional[DreamState] = None
        self._last_completed: Optional[DreamState] = None
        self._idle_messages = [
            "Watching the chain grow...",
            "Listening for new entries...",
            "Guarding the boundaries...",
            "Dreaming of consensus...",
            "Waiting for natural language...",
            "Monitoring security perimeter...",
            "Indexing semantic patterns...",
            "Validating trust relationships...",
        ]
        self._idle_index = 0
        self._startup_time = time.time()

    def dream(self, message: str, completed: bool = False) -> None:
        """
        Record a dreaming activity.

        Args:
            message: What the system is doing
            completed: True if this completes an activity
        """
        now = time.time()

        with self._lock:
            if completed:
                # Mark current as completed
                if self._current:
                    self._current.completed = True
                    self._current.completed_at = now
                    self._last_completed = self._current
                    self._current = None
                else:
                    # No current activity, just record completion
                    self._last_completed = DreamState(
                        message=message,
                        started_at=now,
                        completed=True,
                        completed_at=now
                    )
            else:
                # New activity starting
                self._current = DreamState(
                    message=message,
                    started_at=now,
                    completed=False
                )

    def get_status(self) -> dict:
        """
        Get current dreaming status.

        Returns a dict with:
        - message: Current status message
        - state: 'active', 'completed', or 'idle'
        - duration: How long the current activity has been running
        - timestamp: ISO timestamp
        """
        now = time.time()

        with self._lock:
            if self._current and not self._current.completed:
                # Active operation
                duration = now - self._current.started_at
                return {
                    "message": self._current.message,
                    "state": "active",
                    "duration": round(duration, 1),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }

            if self._last_completed and (now - self._last_completed.completed_at) < 5:
                # Recently completed (within 5 seconds)
                return {
                    "message": f"✓ {self._last_completed.message}",
                    "state": "completed",
                    "duration": 0,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }

            # Idle - cycle through idle messages
            self._idle_index = (self._idle_index + 1) % len(self._idle_messages)
            uptime = round(now - self._startup_time)

            return {
                "message": self._idle_messages[self._idle_index],
                "state": "idle",
                "duration": 0,
                "uptime": uptime,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }


# Global tracker instance
_tracker = DreamingTracker()


def dream(message: str, completed: bool = False) -> None:
    """
    Record a dreaming activity.

    Args:
        message: What the system is doing
        completed: True if this completes an activity

    Example:
        dream("Mining new block")
        # ... do work ...
        dream("Block mined successfully", completed=True)
    """
    _tracker.dream(message, completed)


def get_dream_status() -> dict:
    """
    Get current dreaming status.

    Returns:
        dict with message, state, duration, timestamp
    """
    return _tracker.get_status()


def get_tracker() -> DreamingTracker:
    """Get the global tracker instance."""
    return _tracker
