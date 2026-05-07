import pandas as pd
import numpy as np
from pathlib import Path

# =========================
# INPUT / OUTPUT
# =========================

INPUT_CSV = "09_global_thermal_analysis_results.csv"
OUTPUT_DIR = Path("mission_selection")
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_ALL_RANKED = OUTPUT_DIR / "01_ranked_mission_candidates.csv"
OUTPUT_TOP = OUTPUT_DIR / "02_top_mission_candidates.csv"
OUTPUT_BY_REGION = OUTPUT_DIR / "03_top_candidates_by_region.csv"
OUTPUT_BY_TYPE = OUTPUT_DIR / "04_top_candidates_by_type.csv"

TOP_N = 30

# =========================
# LOAD
# =========================

df = pd.read_csv(INPUT_CSV)

df = df[df["thermal_status"] == "ok"].copy()

numeric_cols = [
    "longitude",
    "latitude",
    "Priority",
    "morphology_score",
    "APC_Diameter_numeric",
    "APC_Depth_numeric",
    "elevation",
    "TI_center_median_3x3",
    "TI_surrounding_mean",
    "Delta_TI",
    "Local_TI_zscore",
    "thermal_rank_score",
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# =========================
# REGION CLASSIFICATION
# =========================

def lon_to_plot(lon):
    return lon - 360 if lon > 180 else lon

df["lon_plot"] = df["longitude"].apply(lon_to_plot)

def classify_region(row):
    lon = row["longitude"]
    lat = row["latitude"]

    # Tharsis / Arsia / Pavonis / Ascraeus area
    if 230 <= lon <= 260 and -25 <= lat <= 30:
        if -20 <= lat <= -5:
            return "Arsia / South Tharsis"
        elif -5 < lat <= 8:
            return "Pavonis / Central Tharsis"
        elif 8 < lat <= 30:
            return "Ascraeus / North Tharsis"
        else:
            return "Tharsis"

    # Elysium / Cerberus
    if 120 <= lon <= 170 and 0 <= lat <= 35:
        return "Elysium / Cerberus"

    # Kasei / NW volcanic terrains
    if 270 <= lon <= 310 and 20 <= lat <= 50:
        return "Kasei / NW"

    # Olympus / western Tharsis
    if 220 <= lon <= 235 and -5 <= lat <= 25:
        return "Olympus / Western Tharsis"

    return "Other"

df["region"] = df.apply(classify_region, axis=1)

# =========================
# NORMALIZATION HELPERS
# =========================

def percentile_score(series):
    return series.rank(pct=True)

def safe_abs_positive_delta(delta):
    """
    For mission selection we prefer positive Delta_TI,
    but we do not completely discard negative anomalies.
    """
    return np.maximum(delta, 0)

# =========================
# FEATURE SCORES
# =========================

df["score_TI_absolute"] = percentile_score(df["TI_center_median_3x3"])
df["score_Delta_TI_positive"] = percentile_score(safe_abs_positive_delta(df["Delta_TI"]))
df["score_TI_zscore"] = percentile_score(df["Local_TI_zscore"])
df["score_morphology"] = percentile_score(df["morphology_score"])

# Priority: lower is better
df["score_priority"] = 1 - (df["Priority"].fillna(3) / 3)
df["score_priority"] = df["score_priority"].clip(0, 1)

# Geometry score only available mainly for APC
df["score_diameter"] = percentile_score(df["APC_Diameter_numeric"].fillna(0))
df["score_depth"] = percentile_score(df["APC_Depth_numeric"].fillna(0))

# Penalize very small or unknown geometry only slightly,
# because skylights often have no APC diameter/depth.
df["score_geometry"] = (
    0.55 * df["score_diameter"] +
    0.45 * df["score_depth"]
)

# Type score for mission usefulness
type_mission_score = {
    "sky": 1.00,   # direct skylight access
    "APC": 0.90,   # large collapse/cavity candidate
    "lat": 0.85,   # lateral access candidate
    "pit": 0.75,
    "end": 0.70
}

df["score_type_mission"] = df["TypeCode"].map(type_mission_score).fillna(0.5)

# =========================
# FINAL MISSION SCORE
# =========================
# This is not purely thermal.
# It balances thermal stability, local anomaly, morphology, and mission usefulness.

df["mission_candidate_score"] = (
    0.25 * df["score_TI_absolute"] +
    0.25 * df["score_Delta_TI_positive"] +
    0.15 * df["score_TI_zscore"] +
    0.15 * df["score_type_mission"] +
    0.10 * df["score_priority"] +
    0.10 * df["score_geometry"]
)

# =========================
# FLAGS / INTERPRETATION
# =========================

def thermal_interpretation(row):
    delta = row["Delta_TI"]
    ti = row["TI_center_median_3x3"]
    z = row["Local_TI_zscore"]

    if delta > 30 and z > 0.5:
        return "Strong positive local thermal anomaly"
    elif delta > 10:
        return "Moderate positive local thermal anomaly"
    elif delta < -20:
        return "Negative local thermal anomaly / possible shadow or low-inertia material"
    elif ti > df["TI_center_median_3x3"].quantile(0.80):
        return "High absolute thermal inertia"
    else:
        return "Thermally average but morphologically relevant"

df["thermal_interpretation"] = df.apply(thermal_interpretation, axis=1)

def mission_relevance(row):
    t = row["TypeCode"]
    delta = row["Delta_TI"]
    depth = row.get("APC_Depth_numeric", np.nan)
    diam = row.get("APC_Diameter_numeric", np.nan)

    reasons = []

    if t == "sky":
        reasons.append("direct skylight/access candidate")
    elif t == "APC":
        reasons.append("large collapse/cavity candidate")
    elif t == "lat":
        reasons.append("possible lateral access")

    if pd.notna(delta) and delta > 10:
        reasons.append("positive thermal anomaly")

    if pd.notna(diam) and diam >= 150:
        reasons.append("large aperture/structure")

    if pd.notna(depth) and depth >= 80:
        reasons.append("deep candidate")

    if not reasons:
        reasons.append("candidate retained by combined score")

    return "; ".join(reasons)

df["mission_relevance"] = df.apply(mission_relevance, axis=1)

# =========================
# SORT AND SAVE
# =========================

df_ranked = df.sort_values(
    by="mission_candidate_score",
    ascending=False
).copy()

cols = [
    "label",
    "region",
    "longitude",
    "latitude",
    "TypeCode",
    "Priority",
    "APC_Diameter",
    "APC_Depth",
    "elevation",
    "TI_center_median_3x3",
    "TI_surrounding_mean",
    "Delta_TI",
    "Local_TI_zscore",
    "thermal_rank_score",
    "morphology_score",

    "score_TI_absolute",
    "score_Delta_TI_positive",
    "score_TI_zscore",
    "score_type_mission",
    "score_priority",
    "score_geometry",

    "mission_candidate_score",
    "thermal_interpretation",
    "mission_relevance",
    "Comment",
]
cols = [c for c in cols if c in df_ranked.columns]

df_ranked[cols].to_csv(OUTPUT_ALL_RANKED, index=False)

top = df_ranked[cols].head(TOP_N)
top.to_csv(OUTPUT_TOP, index=False)

# Top by region
top_by_region = (
    df_ranked
    .groupby("region")
    .head(10)
    [cols]
)

top_by_region.to_csv(OUTPUT_BY_REGION, index=False)

# Top by morphology type
top_by_type = (
    df_ranked
    .groupby("TypeCode")
    .head(10)
    [cols]
)

top_by_type.to_csv(OUTPUT_BY_TYPE, index=False)

# =========================
# PRINT SUMMARY
# =========================

print("\n--- MISSION SELECTION COMPLETE ---")
print(f"Valid candidates used: {len(df_ranked)}")

print("\nSaved:")
print(f"- {OUTPUT_ALL_RANKED}")
print(f"- {OUTPUT_TOP}")
print(f"- {OUTPUT_BY_REGION}")
print(f"- {OUTPUT_BY_TYPE}")

print("\n--- TOP 20 MISSION CANDIDATES ---")
print(top.head(20).to_string(index=False))

print("\n--- TOP CANDIDATES BY REGION ---")
for region, group in df_ranked.groupby("region"):
    print(f"\n{region}")
    print(group[["label", "TypeCode", "mission_candidate_score", "Delta_TI", "TI_center_median_3x3", "Comment"]].head(5).to_string(index=False))