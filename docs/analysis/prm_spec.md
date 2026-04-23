# PRM — Pedestrian Residue Map — Design Spec

**Status**: 설계 v0. 구현은 Day 4 오전 예정.
**작성**: 2026-04-24 (Day 3 오후).
**Binds**: RQ3 (자동차 잔여 텍스처) 핵심 장치. RQ1(공간 지표 보강) 부속.
**Upstream**: `rhythmscape-spec.md` §3.2 수식 + `sentinel_rationale.md`의 "contrastive baseline" 프레임 + `route_selection_rationale.md`의 삼중 구조.
**Downstream**: `metrics/friction.py` (friction zone 식별, Day 4), HTML 리포트 렌더 (Day 5).

---

## 1. PRM이란 무엇인가 — 음의 지표로서의 잔여

PRM(Pedestrian Residue Map)은 **자동차 리듬이 포획하지 못한 보행자 시공간의 잔여**를 공간적으로 지도화한다. 세 지표(ARDI, PRM, RDI) 중 유일한 *음의 지표* — 다른 지표가 자동차 체제의 **존재**를 측정한다면 PRM은 그 체제의 **외부**를 측정한다.

이론적 위상:
- ARDI = 자동차 리듬의 지배 강도 (positive presence)
- RDI = 대중교통 약속의 파열 (disruption within governance)
- **PRM = 자동차 체제가 완전히 포획하지 못한 자리 (residue / negativity)**

이 "잔여"는 두 가지 의미로 해석된다:
1. **기하학적 잔여** — 도로망이 완전히 덮지 못한 공간적 간극. 보행 네트워크의 연결성이 자동차 네트워크의 점유를 초과하는 격자.
2. **리듬적 잔여** — Lefebvre(1992/2004)가 *"arrhythmia의 해방적 측면"*으로 기록한 것: 강제된 동기화를 거부하는 신체들이 재집결하는 자리. *dressage의 외부*.

Day 3-4 브리프에서 PRM은 "자동차가 놓친 곳"이 아니라 **"자동차가 들어오지 못한/못할 곳"**의 위상학적 경계로 프레임된다 (Day 2 `sentinel_rationale.md` §3의 contrastive baseline 원칙과 동형).

---

## 2. 수식 (spec §3.2 확장)

```
PRM(g, t) = walk_connectivity(g) × inverse_car_dominance(g, t) × settlement_density(g)
```

세 인자가 **곱해진다** — 하나가 0에 가까우면 PRM은 0으로 수렴. 즉 잔여가 잔여로 성립하려면 세 조건 모두 충족:

1. **보행 네트워크가 존재**하고 (walk_connectivity > 0)
2. **자동차 점유가 낮고** (inverse_car_dominance > 0, 즉 ARDI < 1)
3. **사람이 산다** (settlement_density > 0)

공간적 해석: "아파트 단지 내부 보행자 공간"은 3조건 모두 충족 → 높은 PRM. "무인 차량기지"는 (3) 결여 → 0. "자동차 전용 고속도로 격자"는 (1)(2) 결여 → 0.

### 2.1 walk_connectivity(g)

격자 `g` 내부의 보행 네트워크 연결도. 베타 중심성(β-centrality) 또는 단순 length-based proxy.

**v0 정의 (단순)**:
```
walk_connectivity(g) = total_walkable_length_m(g) / cell_area_m²
                     → 정규화하여 [0, 1]로 clip
```

**v1 정의 (네트워크 지표)** (Day 4 이후):
```
walk_connectivity(g) = β-centrality(walkable_edges ∩ g)
```

v0에서는 단순 밀도로 시작. OSM `highway IN (footway, path, pedestrian, living_street, residential, steps, track)` 중 보행 접근 가능 분류 (service 제외, motorway 계열 제외).

### 2.2 inverse_car_dominance(g, t)

```
inverse_car_dominance(g, t) = 1 - ARDI_normalized(g, t)
```

ARDI를 0-1로 정규화해야 함 (현 v0는 0-0.4 범위). 정규화 방식:
- **방법 A**: 관측 분포의 max로 나눔 (city-scoped normalization)
- **방법 B**: 이론적 max = sum of weights (w1..w5 = 1.0이면 1.0)로 나눔
- **방법 C**: percentile-based (상위 5% 점수를 1.0으로 치환)

**선택**: 방법 A (city-scoped normalization). 도시 간 비교를 위해서는 각 도시의 ARDI_max로 나눠 0-1 정규화. 이는 "이 도시 안에서 자동차 지배의 상대적 강도"를 측정.

```
ARDI_norm(g, t) = ARDI(g, t) / ARDI_max(city)
inverse_car_dominance(g, t) = 1 - ARDI_norm(g, t) ∈ [0, 1]
```

### 2.3 settlement_density(g)

SGIS 인구 격자 (100m 또는 500m) 기반. 격자 `g`에 포함된 SGIS 셀의 인구 합 / g 면적.

**v0 제약**: SGIS 격자 수집이 Day 4 오전 예정이므로 PRM v0는 `settlement_density = 1` (상수) 으로 가동 가능. 이 경우 PRM = walk_connectivity × inverse_car_dominance (인구 조건 가정). v1에서 SGIS 격자 결합.

### 2.4 시간 차원 (t)

원안 `PRM(g, t)`는 시간 의존. 실제로는:
- `walk_connectivity(g)`: 정적 (도로망은 하루 내 변하지 않음)
- `inverse_car_dominance(g, t)`: 시간 의존 (ARDI의 car_throughput_norm 컴포넌트가 시간 의존)
- `settlement_density(g)`: 정적 (SGIS 격자 거주인구)

**v0**: 시간 의존 생략. 정적 PRM만. 시간 확장은 ARDI 5-component 완성 후.

---

## 3. v0 알고리즘 (Day 4 오전 구현)

```python
def compute_prm_v0(
    city: str,
    ardi_parquet: Path,           # data/processed/osm/ardi_v0_{city}.parquet
    osm_pbf: Path,                # data/processed/osm/{city}.pbf
    cell_size_m: int = 500,
    processed_base: Path = Path("data/processed/osm"),
) -> pd.DataFrame:
    """Compute PRM v0 per cell. Returns DataFrame matching ARDI grid."""
    ardi_df = load_ardi(ardi_parquet)     # cell_id, ardi_v0, geometry_wkt
    walk_gdf = load_walk_network(osm_pbf) # footway/path/pedestrian/residential
    grid = ardi_df_to_gdf(ardi_df)
    
    # Component 1: walk_connectivity
    walk_len_per_cell = compute_walk_length(grid, walk_gdf)
    grid["walk_connectivity"] = (walk_len_per_cell / grid.geometry.area).clip(upper=<threshold>) / <threshold>
    
    # Component 2: inverse_car_dominance
    ardi_max = grid["ardi_v0"].max()
    grid["inverse_car_dominance"] = 1.0 - (grid["ardi_v0"] / ardi_max)
    
    # Component 3: settlement_density (v0 = 1)
    grid["settlement_density"] = 1.0
    
    grid["prm_v0"] = (
        grid["walk_connectivity"]
        * grid["inverse_car_dominance"]
        * grid["settlement_density"]
    )
    return grid
```

---

## 4. 출력 스키마

`data/processed/osm/prm_v0_{city}.parquet`:

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `cell_id` | int | ARDI 격자와 1:1 매핑 |
| `geometry_wkt` | str | 500m cell polygon, EPSG:5186 |
| `walk_connectivity` | float | 0-1, v0는 보행 네트워크 밀도 기반 |
| `inverse_car_dominance` | float | 0-1, 1-ARDI_norm |
| `settlement_density` | float | v0 고정 1.0, v1부터 SGIS 결합 |
| `prm_v0` | float | 세 인자 곱, 0-1 범위 |
| `walk_length_m` | float | 격자 내 보행로 총 길이 (debug용) |
| `n_walk_ways` | int | 격자 내 보행 way 개수 |
| `crs_epsg` | int | 5186 (Korea TM) |

---

## 5. critique_flag 연계 (설계 원칙, 구현은 Day 5)

PRM도 RDI처럼 해석적 비판 장치가 붙어야 한다 (`critique_flag_spec.md`의 프레임 확장). 제안되는 두 플래그:

### 5.1 `enclosure_alert` — 잔여의 소멸

**조건**: PRM < 하위 10분위 AND ARDI > 상위 10분위.

**해석적 메시지**:
> 이 격자에서 보행자 잔여는 거의 없다. 자동차 체제가 이 공간을 **완결적으로 포획**했다. 이것은 다음 중 무엇인가?
> (1) 산업단지·교통 인프라 밀집 지역으로서의 *설계된 비보행*인가?
> (2) 과거 보행 공간이 개발 압력으로 **둘러싸인(enclosed)** 결과인가?
> (3) 애초에 보행 맥락이 없었던 변두리 공백인가?

Day 4 브리프에서 "enclosure"는 공간 점유가 아닌 *보행 가능성의 소실*을 뜻하는 비판적 카테고리로 사용된다.

### 5.2 `refugium_query` — 저항하는 잔여

**조건**: PRM > 상위 10분위 AND 주변 8개 격자 평균 ARDI > 상위 25분위 (즉, *자동차 지배 지역에 둘러싸인 보행 잔여*).

**해석적 메시지**:
> 이 격자는 자동차 리듬으로 포위된 **보행자 피난처(refugium)** 처럼 작동한다. 이것은 다음 중 무엇인가?
> (1) 학교·공원·전통시장처럼 *행정적으로 보호된 비자동차 공간*인가?
> (2) 재개발을 견딘 *근린 주거 블록*의 잔여인가?
> (3) 물리적으로 자동차가 접근 불가한 *지형적 단절*(경사·하천)인가?

`refugium`은 생태학·포스트콜로니얼 도시연구에서 차용 (Tsing 2015 *Mushroom at the End of the World*의 *refugia* 개념). 자동차 체제의 외부가 아니라 *체제 안에서 체제를 견뎌내는 자리*.

---

## 6. 이론적 함의 — 왜 PRM인가

1. **리듬분석의 비대칭**: Lefebvre *Éléments de rythmanalyse*는 *dressage의 완성*이 *arrhythmia의 가능성*과 짝을 이룬다고 읽는다. PRM은 후자의 공간화.
2. **Red Team 방어선**: ARDI 단독은 "자동차 있는 곳에 자동차가 많다"는 tautology 위험. PRM이 *bounded negativity*를 제공함으로써 분석이 자동차의 현존을 단순 기술하는 데서 *잔여의 경계선*을 추적하는 데로 이동.
3. **공간적 기초**: 사실적 측정 단위가 없으면 "보행자가 살아남은 공간"이라는 언어는 비유에 머무른다. PRM은 그 언어를 *감사 가능한 수치*로 번역한다.
4. **4도시 비교 축**: 창원(기획된 자동차 도시)·분당(자본 신도시)·세종(행정 BRT 통합)·영도(비기획 반도) — 네 도시의 PRM 분포 자체가 각자의 **자동차 포획 이후 잔여 구조**를 드러낸다. Day 4 브리프의 *두 번째 4변주*.

---

## 7. 구현 순서 (Day 4 오전)

1. **Block J-1** (30분): walk network OSM 추출 + 격자 기반 보행 밀도 계산 — 창원 단일
2. **Block J-2** (30분): ARDI 정규화 + inverse_car_dominance 결합 — 창원 PRM v0 산출
3. **Block J-3** (30분): PRM 히트맵 시각화 (ARDI와 나란히 비교 패널)
4. **Block J-4** (30분): `compute_prm_v0` 4도시 일반화 (성남/세종/영도)
5. **Block J-5** (60분): PRM + ARDI 기반 friction zone v0 식별 — *frictional_gradient* = |ARDI - (1-PRM)|
6. **Block J-6** (시간 여유 시): SGIS 인구 격자 수집 → v0.5에서 settlement_density 실측 결합

---

## 8. 아카이브

- ARDI v0 산출: `data/processed/osm/ardi_v0_changwon.parquet` (2,444 cells, 1,203 with roads)
- OSM PBF: `data/processed/osm/{city}.pbf`
- 관련 문서: `rhythmscape-spec.md §3.2`, `sentinel_rationale.md`, `route_selection_rationale.md`
- 참조문헌:
  - Lefebvre, H. (1992/2004) *Éléments de rythmanalyse*, Ch. 4 "Dressage"
  - Tsing, A. (2015) *The Mushroom at the End of the World*, Princeton UP — *refugia*
  - Sheller, M. & Urry, J. (2000) "The City and the Car" — automobility 포획 프레임
  - Whitehand, J.W.R. (2007) "Conzenian Urban Morphology and Urban Landscapes" — "morphological residue"

---

**End of spec. 구현 시작: Day 4 오전 07:00~.**
