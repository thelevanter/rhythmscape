"""TAGO (국토교통부 교통빅데이터센터) batch ingest for Changwon Lived layer.

Maps Lefebvre rhythmanalysis 3-layer (Prescribed / Expected / Lived) onto
data.go.kr TAGO endpoints:

    Prescribed  → BusRouteInfoInqireService / getRouteInfoIem
    Expected    → ArvlInfoInqireService / getSttnAcctoArvlPrearngeInfoList
    Lived       → BusLcInfoInqireService / getRouteAcctoBusLcList

See docs/tago-batch-spec.md for the complete design.
"""

from rhythmscape.ingest.tago.client import (
    TagoAPIError,
    TagoClient,
    TagoKeyUnregistered,
    TagoQuotaExceeded,
    TagoRateLimited,
)

__all__ = [
    "TagoClient",
    "TagoAPIError",
    "TagoQuotaExceeded",
    "TagoKeyUnregistered",
    "TagoRateLimited",
]
