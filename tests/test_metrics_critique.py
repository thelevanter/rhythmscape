"""Smoke test for ``rhythmscape.metrics.critique``.

Builds a tiny RDI frame with known magnitude / variance distributions and
verifies that ``compute_thresholds`` + ``apply_critique_flags`` attach the
expected flags and messages.
"""

from __future__ import annotations

import pandas as pd

from rhythmscape.metrics.critique import (
    CritiqueConfig,
    DRESSAGE_MESSAGE_KO,
    VITALITY_MESSAGE_KO,
    apply_critique_flags,
    compute_thresholds,
    extract_flagged_rows,
)


def _make_rdi_fixture() -> pd.DataFrame:
    # 20 rows: 10 with magnitude ~0 (dressage candidates), 10 with magnitude 1.0
    # (vitality candidates); the second set also has high variance. A single
    # station-route pair is used so dressage persistence of 1 can fire.
    rows = []
    for i in range(10):
        rows.append(
            {
                "route_id": "R1",
                "station_id": "NA",
                "time_bin": pd.Timestamp("2026-04-23 08:00", tz="Asia/Seoul")
                + pd.Timedelta(minutes=30 * i),
                "observed_interval": 20.0,
                "prescribed_interval": 20.0,
                "rdi_magnitude": 0.01,  # way below 0.05 floor
                "rdi_variance": 0.0,
                "n_observations": 1,
            }
        )
    for i in range(10):
        rows.append(
            {
                "route_id": "R2",
                "station_id": "NB",
                "time_bin": pd.Timestamp("2026-04-23 08:00", tz="Asia/Seoul")
                + pd.Timedelta(minutes=30 * i),
                "observed_interval": 40.0,
                "prescribed_interval": 20.0,
                "rdi_magnitude": 1.0,  # way above any likely top-decile cutoff
                "rdi_variance": 5.0,  # nonzero, high
                "n_observations": 3,
            }
        )
    return pd.DataFrame(rows)


def test_critique_pipeline_tags_both_flags() -> None:
    rdi = _make_rdi_fixture()
    cfg = CritiqueConfig(
        dressage_magnitude_absolute=0.05,
        dressage_persistence_bins=1,
    )
    thresholds = compute_thresholds(rdi, cfg)
    flagged = apply_critique_flags(rdi, thresholds)

    assert "critique_flag" in flagged.columns
    assert "flag_message_ko" in flagged.columns
    assert "flag_message_en" in flagged.columns
    assert "flag_rationale" in flagged.columns

    dressage_rows = flagged[flagged["critique_flag"] == "dressage_alert"]
    vitality_rows = flagged[flagged["critique_flag"] == "vitality_query"]
    assert len(dressage_rows) >= 1, "at least one dressage_alert must fire"
    assert len(vitality_rows) >= 1, "at least one vitality_query must fire"

    # Messages are the exact interrogative templates (interrogative form is a spec requirement).
    for msg in dressage_rows["flag_message_ko"]:
        assert msg == DRESSAGE_MESSAGE_KO
    for msg in vitality_rows["flag_message_ko"]:
        assert msg == VITALITY_MESSAGE_KO

    # flag_message_en is None on Day 2 (draft is deferred to Day 4).
    assert flagged.loc[flagged["critique_flag"].notna(), "flag_message_en"].isna().all()

    # Rationale carries the rule string and numeric values.
    for rat in dressage_rows["flag_rationale"]:
        assert isinstance(rat, dict)
        assert "rule" in rat and "values" in rat

    # Extract helper returns only flagged rows.
    only = extract_flagged_rows(flagged)
    assert len(only) == len(dressage_rows) + len(vitality_rows)


def test_thresholds_have_metadata() -> None:
    rdi = _make_rdi_fixture()
    thresholds = compute_thresholds(rdi)
    assert "computed_at" in thresholds
    assert "source_window" in thresholds
    assert "routes" in thresholds and set(thresholds["routes"]) == {"R1", "R2"}
    assert "n_observations" in thresholds and thresholds["n_observations"] == 20
    assert "thresholds" in thresholds
    assert "dressage" in thresholds["thresholds"]
    assert "vitality" in thresholds["thresholds"]
