import time
from collections import defaultdict, deque
from collections.abc import Callable


class FailureCounter:
    """Counts events per key inside a sliding time window (in memory, per process).

    In memory is fine for a single instance. With several instances each would keep its own
    counts, and a restart clears them; a shared store such as Redis would fix both.
    """

    def __init__(
        self, max_failures: int, window_seconds: int, clock: Callable[[], float] = time.monotonic
    ):
        self.max_failures = max_failures
        self.window = window_seconds
        self.clock = clock
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str) -> deque[float]:
        events = self._events[key]
        cutoff = self.clock() - self.window
        while events and events[0] <= cutoff:
            events.popleft()
        if not events:
            self._events.pop(key, None)
        return events

    def is_blocked(self, key: str) -> bool:
        return len(self._prune(key)) >= self.max_failures

    def retry_after(self, key: str) -> int:
        events = self._prune(key)
        if not events:
            return 0
        return max(1, int(events[0] + self.window - self.clock()) + 1)

    def record(self, key: str) -> None:
        self._events[key].append(self.clock())

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self._events.clear()
        else:
            self._events.pop(key, None)


# Two limits on login, because the client IP can be spoofed behind some proxies:
#   - 5 failures per (IP, email) in 15 minutes stops simple guessing from one place.
#   - 20 failures per email in 15 minutes (from any IP) caps a spread-out attack. The cost is
#     that someone can briefly block a victim's logins, which we accept over account takeover.
per_client = FailureCounter(max_failures=5, window_seconds=15 * 60)
per_email = FailureCounter(max_failures=20, window_seconds=15 * 60)

# Registration costs a bcrypt hash and creates a row, so cap attempts per client address:
# 10 an hour. Every attempt counts, successful or not. (The address comes from
# X-Forwarded-For behind a proxy, so a determined caller can vary it; this stops casual abuse.)
register_attempts = FailureCounter(max_failures=10, window_seconds=60 * 60)
