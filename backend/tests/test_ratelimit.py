from app.ratelimit import FailureCounter


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_blocks_after_max_failures():
    counter = FailureCounter(max_failures=3, window_seconds=60, clock=Clock())

    for _ in range(2):
        counter.record("k")
    assert not counter.is_blocked("k")
    counter.record("k")
    assert counter.is_blocked("k")


def test_keys_are_independent():
    counter = FailureCounter(max_failures=1, window_seconds=60, clock=Clock())
    counter.record("a")

    assert counter.is_blocked("a")
    assert not counter.is_blocked("b")


def test_failures_expire_after_the_window():
    clock = Clock()
    counter = FailureCounter(max_failures=1, window_seconds=60, clock=clock)
    counter.record("k")

    clock.now += 61

    assert not counter.is_blocked("k")


def test_retry_after_counts_down_to_the_oldest_failure_expiring():
    clock = Clock()
    counter = FailureCounter(max_failures=1, window_seconds=60, clock=clock)
    counter.record("k")
    clock.now += 20

    assert 40 <= counter.retry_after("k") <= 41


def test_reset_clears_one_key_or_all():
    counter = FailureCounter(max_failures=1, window_seconds=60, clock=Clock())
    counter.record("a")
    counter.record("b")

    counter.reset("a")
    assert not counter.is_blocked("a") and counter.is_blocked("b")
    counter.reset()
    assert not counter.is_blocked("b")
