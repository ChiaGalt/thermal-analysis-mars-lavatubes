# mission_selection_clear_visuals.py

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

INPUT = "mission_selection/01_ranked_mission_candidates.csv"
OUT = Path("mission_selection_clear_visuals")
OUT.mkdir(exist_ok=True)

df = pd.read_csv(INPUT)

# tieni solo candidati validi e top
df = df.sort_values("mission_candidate_score", ascending=False).copy()
top = df.head(15).copy()

# -------------------------
# 1. Tabella leggibile TOP 15
# -------------------------

cols = [
    "label", "region", "TypeCode", "Priority",
    "TI_center_median_3x3", "Delta_TI", "Local_TI_zscore",
    "morphology_score", "mission_candidate_score",
    "mission_relevance", "Comment"
]

top_table = top[cols].copy()
top_table.to_csv(OUT / "01_TOP15_mission_candidates_explained.csv", index=False)

# -------------------------
# 2. Bar chart score finale
# -------------------------

plot = top.sort_values("mission_candidate_score")

plt.figure(figsize=(11, 7))
plt.barh(plot["label"], plot["mission_candidate_score"])
plt.xlabel("Mission Candidate Score")
plt.title("Top 15 Mission Candidates — Final Score")
plt.tight_layout()
plt.savefig(OUT / "02_top15_final_score.png", dpi=300)
plt.close()

# -------------------------
# 3. Breakdown dei parametri usati nello score
# -------------------------

score_cols = [
    "score_TI_absolute",
    "score_Delta_TI_positive",
    "score_TI_zscore",
    "score_type_mission",
    "score_priority",
    "score_geometry"
]

available_score_cols = [c for c in score_cols if c in top.columns]

breakdown = top[["label"] + available_score_cols].set_index("label")

plt.figure(figsize=(13, 8))
breakdown.plot(kind="bar", stacked=True, figsize=(13, 8))
plt.ylabel("Score components")
plt.title("Why the Top Candidates Were Selected — Score Breakdown")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(OUT / "03_top15_score_breakdown.png", dpi=300)
plt.close()

# -------------------------
# 4. Thermal vs morphology, solo top 30, con label
# -------------------------

top30 = df.head(30).copy()

plt.figure(figsize=(11, 8))
sc = plt.scatter(
    top30["Delta_TI"],
    top30["morphology_score"],
    c=top30["mission_candidate_score"],
    s=180,
    cmap="viridis",
    edgecolors="black"
)

for _, r in top30.iterrows():
    plt.text(
        r["Delta_TI"] + 1,
        r["morphology_score"] + 0.02,
        r["label"],
        fontsize=8
    )

plt.colorbar(sc, label="Mission Candidate Score")
plt.xlabel("ΔTI = candidate thermal inertia - surrounding mean")
plt.ylabel("Morphology Score")
plt.title("Top 30 Candidates — Thermal Anomaly vs Morphology")
plt.grid(True, linestyle="--", alpha=0.4)
plt.tight_layout()
plt.savefig(OUT / "04_top30_deltaTI_vs_morphology_labeled.png", dpi=300)
plt.close()

# -------------------------
# 5. Mappe zoomate per regione, solo top candidati
# -------------------------

def lon_plot(lon):
    return lon - 360 if lon > 180 else lon

df["lon_plot"] = df["longitude"].apply(lon_plot)
top30["lon_plot"] = top30["longitude"].apply(lon_plot)

regions = top30["region"].dropna().unique()

for region in regions:
    reg = top30[top30["region"] == region].copy()
    if len(reg) == 0:
        continue

    pad_lon = 5
    pad_lat = 5

    plt.figure(figsize=(9, 7))

    sc = plt.scatter(
        reg["lon_plot"],
        reg["latitude"],
        c=reg["mission_candidate_score"],
        s=220,
        cmap="viridis",
        edgecolors="black"
    )

    for _, r in reg.iterrows():
        plt.text(
            r["lon_plot"] + 0.2,
            r["latitude"] + 0.2,
            r["label"],
            fontsize=8
        )

    plt.colorbar(sc, label="Mission Candidate Score")
    plt.xlabel("Longitude [-180, 180]")
    plt.ylabel("Latitude")
    plt.title(f"Top Mission Candidates — {region}")
    plt.xlim(reg["lon_plot"].min() - pad_lon, reg["lon_plot"].max() + pad_lon)
    plt.ylim(reg["latitude"].min() - pad_lat, reg["latitude"].max() + pad_lat)
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()

    safe_name = region.replace("/", "_").replace(" ", "_")
    plt.savefig(OUT / f"05_region_zoom_{safe_name}.png", dpi=300)
    plt.close()

# -------------------------
# 6. Mini report testuale
# -------------------------

with open(OUT / "README_visual_interpretation.txt", "w", encoding="utf-8") as f:
    f.write("MISSION CANDIDATE SELECTION VISUALS\n\n")
    f.write("The final mission score combines:\n")
    f.write("- absolute THEMIS thermal inertia\n")
    f.write("- positive local thermal anomaly Delta_TI\n")
    f.write("- local TI z-score\n")
    f.write("- morphological type usefulness\n")
    f.write("- catalog priority\n")
    f.write("- available geometry information such as diameter/depth\n\n")
    f.write("Most important files:\n")
    f.write("01_TOP15_mission_candidates_explained.csv -> readable table with reasons\n")
    f.write("03_top15_score_breakdown.png -> shows which parameters drive each candidate\n")
    f.write("04_top30_deltaTI_vs_morphology_labeled.png -> shows thermal vs morphology trade-off\n")
    f.write("05_region_zoom_*.png -> readable regional maps without point overcrowding\n")

print("Done. Clear visuals saved in:", OUT)
print(top_table[["label", "region", "TypeCode", "mission_candidate_score", "Delta_TI", "mission_relevance"]].to_string(index=False))