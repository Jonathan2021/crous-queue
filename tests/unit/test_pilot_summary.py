from datetime import date, timedelta

import pytest

from crous_queue.services.pilot_records import (
    FrictionObservation,
    PilotPlan,
    ScheduledCheck,
    Snapshot,
    append_record,
    summarize,
)


def plan():
    return PilotPlan(
        pilot_id="synthetic-five-lunch",
        environment="test",
        data_mode="synthetic",
        store_id="a" * 64,
        days=[date(2026, 10, 12) + timedelta(days=i) for i in range(5)],
    )


def check(p, slot="d1-1145"):
    return ScheduledCheck(
        pilot_id=p.pilot_id,
        slot_id=slot,
        snapshot=Snapshot(
            environment=p.environment,
            data_mode=p.data_mode,
            store_id=p.store_id,
            checked_at=p.slots()[slot],
            returning_devices_7d=1,
            fresh_checks=1,
            venues=[
                dict(
                    venue_id="paris:r177",
                    state="single",
                    report_count=1,
                    newest_age_seconds=0,
                ),
                dict(
                    venue_id="paris:r175",
                    state="unknown",
                    report_count=0,
                    newest_age_seconds=None,
                ),
            ],
        ),
    )


def test_planned_denominator_missingness_zero_and_friction_are_distinct():
    p = plan()
    record = check(p)
    frictions = [
        FrictionObservation(
            **p.model_dump(exclude={"days"}),
            venue_id="paris:r177",
            outcome="completed",
            duration_seconds=8,
            interactions=3,
        ),
        FrictionObservation(
            **p.model_dump(exclude={"days"}), venue_id="paris:r175", outcome="abandoned"
        ),
    ]
    summary = summarize(p, [record], frictions)
    assert (
        summary["planned_checks"] == 40
        and summary["actual_checks"] == 2
        and summary["missing_checks"] == 38
    )
    assert summary["states"] == {
        "unknown": 1,
        "single": 1,
        "recent": 0,
        "conflicting": 0,
    }
    assert summary["fresh_over_actual"] == dict(numerator=1, denominator=2, rate=0.5)
    assert summary["fresh_over_planned"] == dict(
        numerator=1, denominator=40, rate=0.025
    )
    assert (
        summary["friction"]["timed_attempts"] == 1
        and summary["friction"]["median_seconds"] == 8
    )
    empty = summarize(p, [], [])
    assert (
        empty["fresh_over_actual"]["rate"] is None and empty["states"]["unknown"] == 0
    )


def test_duplicate_wrong_day_and_mixed_trials_rejected(tmp_path):
    p = plan()
    record = check(p)
    with pytest.raises(ValueError, match="Duplicate"):
        summarize(p, [record, record], [])
    wrong = record.model_copy(
        update={"snapshot": record.snapshot.model_copy(update={"store_id": "b" * 64})}
    )
    with pytest.raises(ValueError, match="provenance"):
        summarize(p, [wrong], [])
    wrong_day = record.model_copy(
        update={
            "snapshot": record.snapshot.model_copy(
                update={"checked_at": record.snapshot.checked_at + timedelta(days=1)}
            )
        }
    )
    with pytest.raises(ValueError, match="another lunch day"):
        summarize(p, [wrong_day], [])
    file = tmp_path / "records.jsonl"
    append_record(file, record)
    before = file.read_bytes()
    append_record(file, record)
    assert file.read_bytes() == before
    with pytest.raises(ValueError, match="mismatch"):
        append_record(file, wrong)
    assert file.read_bytes() == before
    legacy = tmp_path / "legacy.jsonl"
    legacy.write_text('{"environment":"test"}\n')
    with pytest.raises(ValueError, match="Legacy"):
        append_record(legacy, record.snapshot)
    assert legacy.read_text() == '{"environment":"test"}\n'
