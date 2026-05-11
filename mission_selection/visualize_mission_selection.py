import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# =========================
# INPUT / OUTPUT
# =========================

INPUT_DIR = Path("mission_selection")
OUTPUT_DIR = Path("mission_selection_visuals")
OUTPUT_DIR.mkdir(exist_ok=True)

RANKED_FILE = INPUT_DIR / "01_ranked_mission_candidates.csv"
TOP_FILE = INPUT_DIR / "02_top_mission_candidates.csv"
BY_REGION_FILE = INPUT_DIR / "03_top_candidates_by_region.csv"
BY_TYPE_FILE = INPUT_DIR / "04_top_candidates_by_type.csv"

# =========================
# LOAD DATA
# =========================

ranked = pd.read_csv(RANKED_FILE)
top = pd.read_csv(TOP_FILE)
by_region = pd.read_csv(BY_REGION_FILE)
by_type = pd.read_csv(BY_TYPE_FILE)

# Convert longitude 0–360 to -180/+180 for plotting
for df in [ranked, top, by_region, by_type]:
    df["lon_plot"] = df["longitude"].apply(lambda x: x - 360 if x > 180 else x)

# =========================
# 1. GLOBAL MAP — MISSION SCORE
# =========================

plt.figure(figsize=(14, 7))

sc = plt.scatter(
    ranked["lon_plot"],
    ranked["latitude"],
    c=ranked["mission_candidate_score"],
    s=40 + 250 * ranked["mission_candidate_score"],
    cmap="viridis",
    alpha=0.8,
    edgecolors="black",
    linewidths=0.3
)

plt.colorbar(sc, label="Mission Candidate Score")
plt.xlabel("Longitude [deg, -180 to 180]")
plt.ylabel("Latitude [deg]")
plt.title("Global Mars Lava Tube Candidates — Mission Candidate Score")
plt.xlim(-180, 180)
plt.ylim(-60, 60)
plt.grid(True, linestyle="--", alpha=0.4)

plt.text(-120, 10, "Tharsis", fontsize=10)
plt.text(140, 25, "Elysium", fontsize=10)
plt.text(-70, 30, "Kasei / NW", fontsize=10)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "01_global_mission_score_map.png", dpi=300)
plt.close()

# =========================
# 2. TOP CANDIDATES MAP
# =========================

plt.figure(figsize=(14, 7))

plt.scatter(
    ranked["lon_plot"],
    ranked["latitude"],
    s=25,
    alpha=0.25,
    label="All candidates"
)

sc = plt.scatter(
    top["lon_plot"],
    top["latitude"],
    c=top["mission_candidate_score"],
    s=160,
    cmap="viridis",
    edgecolors="black",
    linewidths=0.6,
    label="Top candidates"
)

for _, row in top.head(15).iterrows():
    plt.text(
        row["lon_plot"] + 1,
        row["latitude"] + 0.8,
        row["label"],
        fontsize=8
    )

plt.colorbar(sc, label="Mission Candidate Score")
plt.xlabel("Longitude [deg, -180 to 180]")
plt.ylabel("Latitude [deg]")
plt.title("Top Mission Lava Tube Candidates")
plt.xlim(-180, 180)
plt.ylim(-60, 60)
plt.grid(True, linestyle="--", alpha=0.4)
plt.legend()

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "02_top_candidates_map.png", dpi=300)
plt.close()

# =========================
# 3. TOP 20 BAR CHART
# =========================

top20 = top.head(20).sort_values("mission_candidate_score")

plt.figure(figsize=(10, 8))

plt.barh(
    top20["label"],
    top20["mission_candidate_score"]
)

plt.xlabel("Mission Candidate Score")
plt.ylabel("Candidate")
plt.title("Top 20 Lava Tube Candidates by Mission Score")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "03_top20_mission_score_bar.png", dpi=300)
plt.close()

# =========================
# 4. THERMAL VS MORPHOLOGY SCATTER
# =========================

plt.figure(figsize=(10, 7))

sc = plt.scatter(
    ranked["Delta_TI"],
    ranked["morphology_score"],
    c=ranked["mission_candidate_score"],
    s=80,
    cmap="viridis",
    alpha=0.8,
    edgecolors="black",
    linewidths=0.3
)

plt.colorbar(sc, label="Mission Candidate Score")
plt.xlabel("Delta_TI")
plt.ylabel("Morphology Score")
plt.title("Thermal Anomaly vs Morphological Quality")
plt.grid(True, linestyle="--", alpha=0.4)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "04_deltaTI_vs_morphology.png", dpi=300)
plt.close()

# =========================
# 5. REGION COMPARISON
# =========================

region_summary = (
    ranked.groupby("region")
    .agg(
        candidate_count=("label", "count"),
        mean_score=("mission_candidate_score", "mean"),
        max_score=("mission_candidate_score", "max"),
        mean_delta_TI=("Delta_TI", "mean"),
        max_delta_TI=("Delta_TI", "max")
    )
    .reset_index()
    .sort_values("max_score", ascending=False)
)

region_summary.to_csv(OUTPUT_DIR / "05_region_summary.csv", index=False)

plt.figure(figsize=(11, 6))

plt.bar(
    region_summary["region"],
    region_summary["max_score"]
)

plt.ylabel("Max Mission Candidate Score")
plt.title("Best Candidate Score by Region")
plt.xticks(rotation=35, ha="right")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "05_best_score_by_region.png", dpi=300)
plt.close()

# =========================
# 6. TYPE COMPARISON
# =========================

type_summary = (
    ranked.groupby("TypeCode")
    .agg(
        candidate_count=("label", "count"),
        mean_score=("mission_candidate_score", "mean"),
        max_score=("mission_candidate_score", "max"),
        mean_delta_TI=("Delta_TI", "mean"),
        max_delta_TI=("Delta_TI", "max")
    )
    .reset_index()
    .sort_values("max_score", ascending=False)
)

type_summary.to_csv(OUTPUT_DIR / "06_type_summary.csv", index=False)

plt.figure(figsize=(9, 6))

plt.bar(
    type_summary["TypeCode"],
    type_summary["max_score"]
)

plt.ylabel("Max Mission Candidate Score")
plt.xlabel("Morphological Type")
plt.title("Best Candidate Score by Morphological Type")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "06_best_score_by_type.png", dpi=300)
plt.close()

# =========================
# 7. THERMAL INERTIA VS DELTA_TI
# =========================

plt.figure(figsize=(10, 7))

sc = plt.scatter(
    ranked["TI_center_median_3x3"],
    ranked["Delta_TI"],
    c=ranked["mission_candidate_score"],
    s=80,
    cmap="viridis",
    alpha=0.8,
    edgecolors="black",
    linewidths=0.3
)

plt.colorbar(sc, label="Mission Candidate Score")
plt.xlabel("THEMIS Thermal Inertia at Candidate")
plt.ylabel("Delta_TI")
plt.title("Absolute Thermal Inertia vs Local Thermal Anomaly")
plt.grid(True, linestyle="--", alpha=0.4)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "07_TI_vs_deltaTI.png", dpi=300)
plt.close()

# =========================
# SAVE TOP CANDIDATES SUMMARY
# =========================

summary_cols = [
    "label",
    "region",
    "longitude",
    "latitude",
    "TypeCode",
    "Priority",
    "TI_center_median_3x3",
    "Delta_TI",
    "Local_TI_zscore",
    "thermal_rank_score",
    "morphology_score",
    "mission_candidate_score",
    "thermal_interpretation",
    "mission_relevance",
    "Comment"
]

summary_cols = [c for c in summary_cols if c in top.columns]

top[summary_cols].to_csv(
    OUTPUT_DIR / "08_top_candidates_visual_summary.csv",
    index=False
)

# =========================
# PRINT SUMMARY
# =========================

print("\n--- VISUALIZATION COMPLETE ---")
print(f"Saved figures in: {OUTPUT_DIR}")

print("\nGenerated files:")
for file in sorted(OUTPUT_DIR.glob("*")):
    print(f"- {file}")

print("\nTop 10 candidates:")
print(
    top[[
        "label",
        "region",
        "TypeCode",
        "mission_candidate_score",
        "Delta_TI",
        "TI_center_median_3x3",
        "mission_relevance"
    ]].head(10).to_string(index=False)
)