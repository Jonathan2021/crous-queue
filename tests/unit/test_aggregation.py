from datetime import timedelta

from crous_queue.models import WaitReport
from crous_queue.services.waits import aggregate
from tests.conftest import NOW


def sample(device, minutes, age=0, received_age=None):
    return WaitReport(
        id=f"{device}-{age}",
        venue_id="paris:r177",
        queue_kind="student",
        kind="estimate",
        minutes=minutes,
        observed_at=NOW - timedelta(minutes=age),
        received_at=NOW
        - timedelta(minutes=age if received_age is None else received_age),
        device_hash=device,
        idempotency_key=f"{device}-{age}",
        payload_digest="f" * 64,
        visibility="visible",
        source_window_start=None,
    )


def test_median_range_earliest_expiry_and_future_clamped():
    state = aggregate(
        [sample("a", 5, 14), sample("b", 10, 2), sample("c", 15, -2, 0)], NOW
    )
    assert state.minutes == 10 and state.range == [5, 15] and state.count == 3
    assert state.expires_at == NOW + timedelta(minutes=1)
    assert state.newest_at == NOW
    assert aggregate([sample("a", 0, 15)], NOW).state == "unknown"


def test_latest_device_does_not_resurrect_after_hiding():
    old = sample("a", 0, 3)
    newest = sample("a", 10)
    newest.visibility = "hidden"
    assert aggregate([old, newest], NOW).state == "unknown"
