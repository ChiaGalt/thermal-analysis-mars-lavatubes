import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# =========================
# INPUT / OUTPUT
# =========================

INPUT_CSV = "09_global_thermal_analysis_results.csv"
OUTPUT_DIR = Path("thermal_maps")
OUTPUT_DIR.mkdir(exist_ok=True)

df = pd.read_csv(INPUT_CSV)

# Keep only valid thermal extractions
df = df[df["thermal_status"] == "ok"].copy()

# Numeric cleaning
numeric_cols = [
    "longitude", "latitude",
    "TI_center_median_3x3",
    "TI_surrounding_mean",
    "Delta_TI",
    "Local_TI_zscore",
    "thermal_rank_score",
    "morphology_score"
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["longitude", "latitude"]).copy()

print(f"Valid candidates: {len(df)}")

# Convert longitude 0-360 to -180/+180 for easier plotting
df["lon_plot"] = df["longitude"].apply(lambda x: x - 360 if x > 180 else x)

# =========================
# HELPER FUNCTION
# =========================

def save_scatter_map(
    data,
    color_col,
    title,
    filename,
    size_col=None,
    cmap="viridis",
    vmin=None,
    vmax=None
):
    plt.figure(figsize=(14, 7))

    if size_col and size_col in data.columns:
        sizes = 30 + 250 * data[size_col].fillna(0)
    else:
        sizes = 60

    sc = plt.scatter(
        data["lon_plot"],
        data["latitude"],
        c=data[color_col],
        s=sizes,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        alpha=0.8,
        edgecolors="black",
        linewidths=0.3
    )

    plt.colorbar(sc, label=color_col)

    plt.xlabel("Longitude [deg, -180 to 180]")
    plt.ylabel("Latitude [deg]")
    plt.title(title)

    plt.xlim(-180, 180)
    plt.ylim(-60, 60)

    plt.grid(True, linestyle="--", alpha=0.4)

    # Useful region labels
    plt.text(-120, 10, "Tharsis", fontsize=10)
    plt.text(140, 25, "Elysium", fontsize=10)
    plt.text(-70, 30, "Kasei / NW", fontsize=10)

    plt.tight_layout()

    out_path = OUTPUT_DIR / filename
    plt.savefig(out_path, dpi=300)
    plt.close()

    print(f"Saved: {out_path}")


# =========================
# MAP 1 — Thermal rank score
# =========================

save_scatter_map(
    data=df,
    color_col="thermal_rank_score",
    size_col="thermal_rank_score",
    title="Mars Lava Tube Candidates — Thermal Rank Score",
    filename="01_global_thermal_rank_score.png",
    cmap="viridis"
)

# =========================
# MAP 2 — Delta thermal inertia
# =========================

delta_abs = np.nanpercentile(np.abs(df["Delta_TI"]), 95)

save_scatter_map(
    data=df,
    color_col="Delta_TI",
    size_col="thermal_rank_score",
    title="Mars Lava Tube Candidates — Local Thermal Inertia Anomaly ΔTI",
    filename="02_global_delta_TI.png",
    cmap="coolwarm",
    vmin=-delta_abs,
    vmax=delta_abs
)

# =========================
# MAP 3 — Thermal inertia absolute value
# =========================

save_scatter_map(
    data=df,
    color_col="TI_center_median_3x3",
    size_col="thermal_rank_score",
    title="Mars Lava Tube Candidates — THEMIS Thermal Inertia",
    filename="03_global_TI_center.png",
    cmap="plasma"
)

# =========================
# MAP 4 — Top 20% candidates only
# =========================

threshold = df["thermal_rank_score"].quantile(0.80)
top = df[df["thermal_rank_score"] >= threshold].copy()

save_scatter_map(
    data=top,
    color_col="thermal_rank_score",
    size_col="thermal_rank_score",
    title="Top 20% Lava Tube Candidates by Thermal Rank Score",
    filename="04_top20_thermal_candidates.png",
    cmap="viridis"
)

# =========================
# MAP 5 — By morphology type
# =========================

plt.figure(figsize=(14, 7))

type_colors = {
    "sky": "tab:blue",
    "APC": "tab:orange",
    "pit": "tab:green",
    "end": "tab:red",
    "lat": "tab:purple"
}

for t, group in df.groupby("TypeCode"):
    plt.scatter(
        group["lon_plot"],
        group["latitude"],
        s=70,
        alpha=0.8,
        label=t,
        edgecolors="black",
        linewidths=0.3
    )

plt.xlabel("Longitude [deg, -180 to 180]")
plt.ylabel("Latitude [deg]")
plt.title("Mars Lava Tube Candidates — Morphological Type")

plt.xlim(-180, 180)
plt.ylim(-60, 60)
plt.grid(True, linestyle="--", alpha=0.4)
plt.legend(title="TypeCode")

plt.tight_layout()
out_path = OUTPUT_DIR / "05_global_candidates_by_type.png"
plt.savefig(out_path, dpi=300)
plt.close()

print(f"Saved: {out_path}")

# =========================
# TOP TABLE
# =========================

top_table_cols = [
    "label", "longitude", "latitude", "TypeCode", "Priority",
    "TI_center_median_3x3",
    "TI_surrounding_mean",
    "Delta_TI",
    "Local_TI_zscore",
    "thermal_rank_score",
    "morphology_score",
    "Comment"
]

top_table_cols = [c for c in top_table_cols if c in df.columns]

top_table = df.sort_values(
    by="thermal_rank_score",
    ascending=False
)[top_table_cols].head(50)

top_table.to_csv(OUTPUT_DIR / "06_top50_thermal_candidates.csv", index=False)

print("Saved: thermal_maps/06_top50_thermal_candidates.csv")
print("\nTop 20 candidates:")
print(top_table.head(20).to_string(index=False))