import pandas as pd
from pathlib import Path

# =========================
# INPUT FILES
# =========================

EXTENDED_CATALOG = "Mars_Extended_Cave_Catalog.csv"
BASE_CATALOG = "Mars_Cave_Catalog.csv"

if Path(EXTENDED_CATALOG).exists():
    input_file = EXTENDED_CATALOG
else:
    input_file = BASE_CATALOG

print(f"Using catalog: {input_file}")

df = pd.read_csv(input_file)

# =========================
# BASIC CLEANING
# =========================

df["TypeCode"] = df["TypeCode"].astype(str).str.strip()
df["Priority"] = pd.to_numeric(df["Priority"], errors="coerce")
df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")

df["APC_Diameter_numeric"] = pd.to_numeric(df["APC_Diameter"], errors="coerce")
df["APC_Depth_numeric"] = pd.to_numeric(df["APC_Depth"], errors="coerce")

# Remove records without coordinates
df = df.dropna(subset=["longitude", "latitude"]).copy()

# Normalize longitude to 0–360 East
df["longitude"] = df["longitude"] % 360

# =========================
# GLOBAL MORPHOLOGICAL FILTER
# =========================

good_types = ["sky", "APC", "pit", "end", "lat"]

global_good_types = df[
    df["TypeCode"].isin(good_types)
].copy()

# =========================
# PRIORITY FILTER
# =========================

global_high_priority = global_good_types[
    global_good_types["Priority"].isin([0, 1])
].copy()

# =========================
# MORPHOLOGY SCORE
# =========================

type_score = {
    "sky": 5,
    "APC": 4,
    "pit": 3,
    "end": 3,
    "lat": 3
}

priority_score = {
    0: 5,
    1: 4,
    2: 2,
    3: 1
}

global_high_priority["type_score"] = global_high_priority["TypeCode"].map(type_score)
global_high_priority["priority_score"] = global_high_priority["Priority"].map(priority_score)

global_high_priority["morphology_score"] = (
    0.6 * global_high_priority["type_score"] +
    0.4 * global_high_priority["priority_score"]
)

# =========================
# THEMIS TILE ASSIGNMENT
# =========================

def get_lon_tile(lon):
    lon = lon % 360

    if 0 <= lon < 60:
        return "000E"
    elif 60 <= lon < 120:
        return "060E"
    elif 120 <= lon < 180:
        return "120E"
    elif 180 <= lon < 240:
        return "180E"
    elif 240 <= lon < 300:
        return "240E"
    elif 300 <= lon < 360:
        return "300E"
    return None


def get_lat_tile(lat):
    if 30 <= lat < 60:
        return "30N"
    elif 0 <= lat < 30:
        return "00N"
    elif -30 <= lat < 0:
        return "30S"
    elif -60 <= lat < -30:
        return "60S"
    elif lat >= 60:
        return "POLAR_N"
    elif lat < -60:
        return "POLAR_S"
    return None


global_high_priority["themis_lon_tile"] = global_high_priority["longitude"].apply(get_lon_tile)
global_high_priority["themis_lat_tile"] = global_high_priority["latitude"].apply(get_lat_tile)
global_high_priority["themis_tile"] = (
    global_high_priority["themis_lat_tile"] +
    global_high_priority["themis_lon_tile"]
)

global_high_priority["themis_quantitative_product_name"] = (
    "THEMIS Thermal Inertia Mosaic Quantitative "
    + global_high_priority["themis_tile"].astype(str)
    + " 100mpp"
)

# =========================
# SORT RESULTS
# =========================

global_high_priority = global_high_priority.sort_values(
    by=["morphology_score", "Priority", "TypeCode", "label"],
    ascending=[False, True, True, True]
)

# =========================
# SAVE OUTPUTS
# =========================

df.to_csv("01_global_all_candidates_clean.csv", index=False)
global_good_types.to_csv("02_global_good_morphology.csv", index=False)
global_high_priority.to_csv("03_global_high_priority_candidates.csv", index=False)

columns_to_export = [
    "label",
    "longitude",
    "latitude",
    "TypeCode",
    "Priority",
    "APC_Diameter",
    "APC_Depth",
    "APC_Diameter_numeric",
    "APC_Depth_numeric",
    "morphology_score",
    "themis_tile",
    "themis_quantitative_product_name",
    "Comment"
]

if "elevation" in global_high_priority.columns:
    columns_to_export.insert(8, "elevation")

short_table = global_high_priority[columns_to_export].copy()
short_table.to_csv("04_global_shortlist_for_thermal_analysis.csv", index=False)

tile_summary = (
    global_high_priority.groupby("themis_tile")
    .size()
    .reset_index(name="candidate_count")
    .sort_values(by="candidate_count", ascending=False)
)

tile_summary.to_csv("05_required_themis_tiles_summary.csv", index=False)

# =========================
# PRINT SUMMARY
# =========================

print("\n--- SUMMARY ---")
print(f"Total catalog candidates: {len(df)}")
print(f"Global good morphology candidates: {len(global_good_types)}")
print(f"Final global high-priority shortlist: {len(global_high_priority)}")

print("\n--- TYPE COUNTS ---")
print(global_high_priority["TypeCode"].value_counts())

print("\n--- PRIORITY COUNTS ---")
print(global_high_priority["Priority"].value_counts())

print("\n--- REQUIRED THEMIS TILES ---")
print(tile_summary.to_string(index=False))

print("\n--- FIRST 30 FINAL CANDIDATES ---")
print(short_table.head(30).to_string(index=False))