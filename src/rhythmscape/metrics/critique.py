"""critique_flag — RDI post-processing following ``docs/analysis/critique_flag_spec.md``.

Adds two interpretive flags to the RDI DataFrame:

- ``dressage_alert`` — RDI magnitude near zero (**perfect synchronization
  with the prescribed schedule**), sustained over consecutive bins. Named
  after Lefebvre's *dressage*: the subordination of bodies to
  industrial/state time.
- ``vitality_query`` — RDI magnitude in the top decile **and** variance
  in the top decile. Empirical proxy for polyrhythmia — collision of
  multiple living rhythms.

Design constraints (from spec §3, §7):

- Thresholds are **posterior** to the data — no spatial tags
  (``industrial_zone``, ``cbd`` etc.) are allowed, per Red Team's
  rejection of spatial prejudice.
- Flag messages are fixed **interrogative** — the device calls questions,
  not judgments (spec §2.1/§2.2 text).
- Flag rationale stores the concrete rule evaluated, to support later
  audit and revision.
- Unflagged rows are ``None`` across all four output columns, signifying
  *judgment suspended*, not *normal*.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import structlog
import yaml

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Message templates (spec §2.1, §2.2 — interrogative form, frozen Day 2)
# ---------------------------------------------------------------------------

DRESSAGE_MESSAGE_KO = (
    "이 격자·시간대의 리듬은 처방된 시간표와 거의 완벽히 일치하고 있다. "
    "이 동기화는 다음 중 무엇인가?\n"
    "(1) 산업 교대조·통학·출퇴근 리듬에 대한 체계적 종속의 징후(dressage)인가?\n"
    "(2) 이용자 편의를 위한 정당한 안정성인가?\n"
    "(3) 배차 간격이 실제 수요와 무관하게 설정된 결과로 우연히 만들어진 일치인가?\n"
    "이 구분은 수치 내부에서 결정되지 않는다. "
    "공간적·역사적 맥락의 조회를 요구한다."
)

VITALITY_MESSAGE_KO = (
    "이 격자·시간대에서 리듬이 크게 이탈하고, 그 이탈 자체도 불규칙하다. "
    "이것은 다음 중 무엇인가?\n"
    "(1) 시스템 실패(사고·정체·결행)의 징후인가?\n"
    "(2) 생활세계의 자율적 리듬(장날, 시장 영업, 지역 행사, 종교 의례, 집회)과 "
    "대중교통 처방의 접합점인가?\n"
    "(3) 측정 노이즈의 누적인가?\n"
    "이 구분은 현장 관찰 또는 공간적 맥락 조회를 요구한다."
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CritiqueConfig:
    """Knobs exposed to the caller. All defaults come from spec §2, §3."""

    dressage_magnitude_absolute: float = 0.05
    dressage_decile: float = 0.10  # lowest decile
    dressage_persistence_bins: int = 3  # 30 min × 3 = 1.5 h (Day-2 empirical)
    vitality_magnitude_decile: float = 0.90  # highest decile
    vitality_variance_decile: float = 0.90
    bin_minutes: int = 30


# ---------------------------------------------------------------------------
# Thresholds (spec §3 — posterior to the data)
# ---------------------------------------------------------------------------


def compute_thresholds(
    rdi_df: pd.DataFrame,
    config: CritiqueConfig | None = None,
) -> dict[str, Any]:
    """Compute dressage / vitality thresholds from the RDI distribution.

    Stored alongside the RDI window metadata in ``config/critique_flag.yaml``
    so that a repeat computation over the same slice yields identical
    thresholds (no randomness involved — purely quantile-based).
    """
    cfg = config or CritiqueConfig()
    mag = rdi_df["rdi_magnitude"]
    var = rdi_df["rdi_variance"]

    t = {
        "computed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_window": [
            pd.Timestamp(rdi_df["time_bin"].min()).isoformat(),
            pd.Timestamp(rdi_df["time_bin"].max()).isoformat(),
        ],
        "routes": sorted(rdi_df["route_id"].unique().tolist()),
        "n_observations": int(len(rdi_df)),
        "bin_minutes": cfg.bin_minutes,
        "thresholds": {
            "dressage": {
                "magnitude_absolute": cfg.dressage_magnitude_absolute,
                "magnitude_decile_cutoff": float(mag.quantile(cfg.dressage_decile)),
                "persistence_bins": cfg.dressage_persistence_bins,
            },
            "vitality": {
                "magnitude_decile_cutoff": float(
                    mag.quantile(cfg.vitality_magnitude_decile)
                ),
                "variance_decile_cutoff": float(
                    var.quantile(cfg.vitality_variance_decile)
                ),
            },
        },
        "config": asdict(cfg),
    }
    return t


def save_thresholds(thresholds: dict[str, Any], path: Path) -> Path:
    """Persist thresholds YAML and archive any previous value under ``.YYYYMMDD.yaml``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d")
        archive = path.with_name(f"{path.stem}.{stamp}{path.suffix}")
        if not archive.exists():
            archive.write_bytes(path.read_bytes())
            log.info("thresholds_archived", previous=str(archive))
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(thresholds, fh, allow_unicode=True, sort_keys=False)
    log.info("thresholds_written", path=str(path))
    return path


# ---------------------------------------------------------------------------
# Flag application (spec §2, §4, §8)
# ---------------------------------------------------------------------------


def _dressage_mask(
    rdi_df: pd.DataFrame,
    thresholds: dict[str, Any],
) -> pd.Series:
    """Boolean mask for rows satisfying the three dressage conditions."""
    d = thresholds["thresholds"]["dressage"]
    abs_floor = d["magnitude_absolute"]
    decile_cutoff = d["magnitude_decile_cutoff"]
    persist = int(d["persistence_bins"])

    # Rule 1 & 2: below absolute floor AND within lowest decile.
    base = (rdi_df["rdi_magnitude"] < abs_floor) & (
        rdi_df["rdi_magnitude"] <= decile_cutoff
    )

    # Rule 3: persistence — within each (route_id, station_id), require
    # ``persist`` consecutive bins to also satisfy ``base``.
    if persist <= 1:
        return base

    df = rdi_df[["route_id", "station_id", "time_bin"]].copy()
    df["base"] = base.values
    df = df.sort_values(["route_id", "station_id", "time_bin"]).reset_index()
    # Rolling count of base-trues over the last ``persist`` bins, per group.
    df["streak"] = (
        df.groupby(["route_id", "station_id"])["base"]
        .rolling(window=persist, min_periods=persist)
        .sum()
        .reset_index(level=[0, 1], drop=True)
    )
    df["is_dressage"] = df["streak"] == persist
    # Map back to the original index order.
    return df.set_index("index")["is_dressage"].reindex(rdi_df.index).fillna(False)


def _vitality_mask(
    rdi_df: pd.DataFrame,
    thresholds: dict[str, Any],
) -> pd.Series:
    """Boolean mask for rows with both magnitude and variance in their top decile."""
    v = thresholds["thresholds"]["vitality"]
    return (rdi_df["rdi_magnitude"] >= v["magnitude_decile_cutoff"]) & (
        rdi_df["rdi_variance"] >= v["variance_decile_cutoff"]
    ) & (rdi_df["rdi_variance"] > 0)


def _rationale_row(row: pd.Series, flag: str, thresholds: dict[str, Any]) -> dict:
    """Build the per-row rationale dict recorded in ``flag_rationale``."""
    if flag == "dressage_alert":
        d = thresholds["thresholds"]["dressage"]
        return {
            "rule": (
                f"magnitude<{d['magnitude_absolute']} "
                f"AND magnitude<=p{int(100*0.10)} ({d['magnitude_decile_cutoff']:.4f}) "
                f"AND persistence>={d['persistence_bins']} bins"
            ),
            "values": {
                "rdi_magnitude": float(row["rdi_magnitude"]),
                "rdi_variance": float(row["rdi_variance"]),
                "n_observations": int(row["n_observations"]),
            },
            "reference": "Lefebvre 1992/2004, Éléments de rythmanalyse, Ch. 4",
        }
    v = thresholds["thresholds"]["vitality"]
    return {
        "rule": (
            f"magnitude>=p{int(100*0.90)} ({v['magnitude_decile_cutoff']:.4f}) "
            f"AND variance>=p{int(100*0.90)} ({v['variance_decile_cutoff']:.4f}) "
            f"AND variance>0"
        ),
        "values": {
            "rdi_magnitude": float(row["rdi_magnitude"]),
            "rdi_variance": float(row["rdi_variance"]),
            "n_observations": int(row["n_observations"]),
        },
        "reference": "Lefebvre 1992/2004, Éléments de rythmanalyse, Ch. 2 (polyrhythmia)",
    }


def apply_critique_flags(
    rdi_df: pd.DataFrame,
    thresholds: dict[str, Any],
) -> pd.DataFrame:
    """Return the RDI DataFrame with four critique columns appended.

    Added columns: ``critique_flag``, ``flag_message_ko``, ``flag_message_en``,
    ``flag_rationale``. ``flag_message_en`` is None for Day 2; English draft
    is Day-4 work per spec §9.
    """
    out = rdi_df.copy().reset_index(drop=True)
    dressage = _dressage_mask(out, thresholds)
    vitality = _vitality_mask(out, thresholds)

    # If a row satisfies both, dressage wins (impossible in practice because
    # dressage requires lowest decile and vitality requires highest, but we
    # guard the precedence explicitly).
    flag = pd.Series([None] * len(out), dtype=object)
    flag.loc[vitality.values] = "vitality_query"
    flag.loc[dressage.values] = "dressage_alert"
    out["critique_flag"] = flag

    out["flag_message_ko"] = out["critique_flag"].map(
        {"dressage_alert": DRESSAGE_MESSAGE_KO, "vitality_query": VITALITY_MESSAGE_KO}
    )
    out["flag_message_en"] = None
    out["flag_rationale"] = [
        _rationale_row(out.iloc[i], out.iloc[i]["critique_flag"], thresholds)
        if out.iloc[i]["critique_flag"] is not None
        else None
        for i in range(len(out))
    ]
    log.info(
        "critique_flags_applied",
        dressage=int(dressage.sum()),
        vitality=int(vitality.sum()),
        total_rows=len(out),
    )
    return out


def extract_flagged_rows(rdi_df: pd.DataFrame) -> pd.DataFrame:
    """Return only the rows where ``critique_flag`` is set."""
    return rdi_df[rdi_df["critique_flag"].notna()].reset_index(drop=True)


def save_flagged(df: pd.DataFrame, out_path: Path) -> Path:
    """Write flagged rows to parquet. Pyarrow serializes the rationale dict column as JSON-like struct."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Parquet cannot store arbitrary Python dicts; serialize rationale to JSON string.
    df_write = df.copy()
    if "flag_rationale" in df_write.columns:
        df_write["flag_rationale"] = df_write["flag_rationale"].apply(
            lambda x: None if x is None else __import__("json").dumps(x, ensure_ascii=False)
        )
    df_write.to_parquet(out_path, compression="snappy", index=False)
    log.info("critique_flags_written", path=str(out_path), rows=len(df_write))
    return out_path
