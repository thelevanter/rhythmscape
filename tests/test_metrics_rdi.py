"""Smoke test for ``rhythmscape.metrics.rdi``.

Builds a tiny deterministic locations frame with two vehicles of a single
route, verifies that the end-to-end ``compute_rdi`` pipeline produces
plausibly-shaped output.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from rhythmscape.metrics.rdi import compute_rdi


def test_compute_rdi_single_station_two_vehicles() -> None:
    """Two buses at the same station 10 min apart, prescribed 20 min → RDI≈0.5."""
    base = datetime(2026, 4, 23, 8, 0, tzinfo=timezone.utc)
    rows = []
    # Vehicle A at nodeX at t=0
    rows.append(
        {
            "snapshot_ts_utc": base,
            "routeid": "R1",
            "vehicleno": "A",
            "nodeid": "NX",
            "nodenm": "n1",
            "nodeord": 1,
            "gpslati": 35.2,
            "gpslong": 128.6,
        }
    )
    # Vehicle B at nodeX at t=10min
    rows.append(
        {
            "snapshot_ts_utc": base + pd.Timedelta(minutes=10),
            "routeid": "R1",
            "vehicleno": "B",
            "nodeid": "NX",
            "nodenm": "n1",
            "nodeord": 1,
            "gpslati": 35.2,
            "gpslong": 128.6,
        }
    )
    loc = pd.DataFrame(rows)
    loc["snapshot_ts_utc"] = pd.to_datetime(loc["snapshot_ts_utc"], utc=True)

    prescribed = pd.DataFrame(
        [
            {
                "route_id": "R1",
                "daytype": "weekday",
                "peak_interval_min": 20.0,
                "off_peak_interval_min": 20.0,
                "source": "test",
                "collected_at": "2026-04-23T00:00Z",
            },
            {
                "route_id": "R1",
                "daytype": "sat",
                "peak_interval_min": 20.0,
                "off_peak_interval_min": 20.0,
                "source": "test",
                "collected_at": "2026-04-23T00:00Z",
            },
            {
                "route_id": "R1",
                "daytype": "sun",
                "peak_interval_min": 20.0,
                "off_peak_interval_min": 20.0,
                "source": "test",
                "collected_at": "2026-04-23T00:00Z",
            },
        ]
    )

    rdi = compute_rdi(loc, prescribed, tz="UTC", bin_minutes=30)

    assert not rdi.empty
    assert set(
        [
            "route_id",
            "station_id",
            "time_bin",
            "observed_interval",
            "prescribed_interval",
            "rdi_magnitude",
            "rdi_variance",
            "n_observations",
        ]
    ).issubset(set(rdi.columns))
    # Exactly one interval produced (10 min), prescribed 20 → |10-20|/20 = 0.5.
    assert len(rdi) == 1
    row = rdi.iloc[0]
    assert row["route_id"] == "R1"
    assert row["station_id"] == "NX"
    assert abs(row["observed_interval"] - 10.0) < 1e-6
    assert abs(row["prescribed_interval"] - 20.0) < 1e-6
    assert abs(row["rdi_magnitude"] - 0.5) < 1e-6
    assert row["n_observations"] == 1
