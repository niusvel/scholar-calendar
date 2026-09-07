from pathlib import Path

from scholar_calendar.config import load_planning, save_planning


def test_day_turn_counts_and_saturday_are_loaded_without_sunday():
    planning = load_planning("examples/cycle.json")

    assert planning.day_period_counts == {1: 6, 2: 6, 3: 6, 4: 6, 5: 4, 6: 4}
    assert planning.saturday_weeks == frozenset({2})
    assert {slot.day for slot in planning.slots} == {1, 2, 3, 4, 5, 6}
    assert not any(slot.week == 1 and slot.day == 6 for slot in planning.slots)
    assert sum(slot.day == 6 for slot in planning.slots) == 4
    assert not any(slot.day == 7 for slot in planning.slots)


def test_day_turn_settings_survive_json_round_trip(tmp_path):
    planning = load_planning("examples/cycle.json")
    path = tmp_path / "cycle.json"

    save_planning(planning, path)
    restored = load_planning(path)

    assert restored.day_period_counts == planning.day_period_counts
    assert restored.saturday_weeks == planning.saturday_weeks
    assert {slot.day for slot in restored.slots} == {1, 2, 3, 4, 5, 6}


def test_custom_start_survives_save_and_reload(tmp_path):
    import json
    from dataclasses import replace
    from datetime import time

    from scholar_calendar.models import build_daily_periods, build_slots

    planning = load_planning("examples/cycle.json")
    planning = replace(
        planning,
        class_start=time(8, 30),
        slots=build_slots(
            weeks=planning.weeks,
            days=6,
            daily_periods=build_daily_periods(start=time(8, 30)),
            day_period_counts=planning.day_period_counts,
            saturday_weeks=planning.saturday_weeks,
        ),
    )
    path = tmp_path / "custom-start.json"
    save_planning(planning, path)
    assert json.loads(path.read_text())["clock"]["start"] == "08:30"
    restored = load_planning(path)
    assert restored.class_start == time(8, 30)
    assert restored.slots == planning.slots


def test_old_explicit_periods_infer_start_and_duration(tmp_path):
    import json
    from datetime import time

    data = json.loads(Path("examples/cycle.json").read_text(encoding="utf-8"))
    data["daily_periods"] = [{"start": "09:15", "end": "10:15"}, {"start": "10:20", "end": "11:20"}]
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(data))
    restored = load_planning(path)
    assert restored.class_start == time(9, 15)
    assert restored.period_duration_minutes == 60
    assert restored.transition_minutes == 5


def test_start_is_used_when_generating_periods_from_json(tmp_path):
    import json
    from datetime import time

    data = json.loads(Path("examples/cycle.json").read_text(encoding="utf-8"))
    data.pop("daily_periods")
    data["clock"] = {"start": "08:30", "periods_per_day": 6}
    path = tmp_path / "clock.json"
    path.write_text(json.dumps(data))
    restored = load_planning(path)
    assert restored.slots[0].start == time(8, 30)
