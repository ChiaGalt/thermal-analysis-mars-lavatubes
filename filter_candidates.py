import pandas as pd
from pathlib import Path

# =========================
# INPUT FILES
# =========================

EXTENDED_CATALOG = "Mars_Extended_Cave_Catalog.csv"
BASE_CATALOG = "Mars_Cave_Catalog.csv"

# Usa il catalogo esteso se esiste, perché contiene anche elevation
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

# Converte diametro/profondità quando possibile
df["APC_Diameter_numeric"] = pd.to_numeric(df["APC_Diameter"], errors="coerce")
df["APC_Depth_numeric"] = pd.to_numeric(df["APC_Depth"], errors="coerce")

# =========================
# FILTER 1: THARSIS REGION
# =========================

tharsis = df[
    (df["longitude"] >= 230) &
    (df["longitude"] <= 260) &
    (df["latitude"] >= -25) &
    (df["latitude"] <= 30)
].copy()

# =========================
# FILTER 2: GOOD MORPHOLOGICAL TYPES
# =========================

good_types = ["sky", "APC", "pit", "end", "lat"]

tharsis_good_types = tharsis[
    tharsis["TypeCode"].isin(good_types)
].copy()

# =========================
# FILTER 3: HIGH PRIORITY ONLY
# =========================

tharsis_high_priority = tharsis_good_types[
    tharsis_good_types["Priority"].isin([0, 1])
].copy()

# =========================
# OPTIONAL: CREATE A SIMPLE MORPHOLOGY SCORE
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

tharsis_high_priority["type_score"] = tharsis_high_priority["TypeCode"].map(type_score)
tharsis_high_priority["priority_score"] = tharsis_high_priority["Priority"].map(priority_score)

tharsis_high_priority["morphology_score"] = (
    0.6 * tharsis_high_priority["type_score"] +
    0.4 * tharsis_high_priority["priority_score"]
)

# =========================
# SORT RESULTS
# =========================

sort_columns = ["morphology_score", "Priority", "TypeCode", "label"]

tharsis_high_priority = tharsis_high_priority.sort_values(
    by=sort_columns,
    ascending=[False, True, True, True]
)

# =========================
# SAVE OUTPUTS
# =========================

tharsis.to_csv("01_tharsis_all_candidates.csv", index=False)
tharsis_good_types.to_csv("02_tharsis_good_morphology.csv", index=False)
tharsis_high_priority.to_csv("03_tharsis_high_priority_shortlist.csv", index=False)

# Short printable version
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
    "Comment"
]

if "elevation" in tharsis_high_priority.columns:
    columns_to_export.insert(8, "elevation")

short_table = tharsis_high_priority[columns_to_export].copy()
short_table.to_csv("04_tharsis_shortlist_for_thermal_analysis.csv", index=False)

# =========================
# PRINT SUMMARY
# =========================

print("\n--- SUMMARY ---")
print(f"Total catalog candidates: {len(df)}")
print(f"Tharsis candidates: {len(tharsis)}")
print(f"Tharsis good morphology candidates: {len(tharsis_good_types)}")
print(f"Final high-priority shortlist: {len(tharsis_high_priority)}")

print("\n--- TYPE COUNTS IN FINAL SHORTLIST ---")
print(tharsis_high_priority["TypeCode"].value_counts())

print("\n--- PRIORITY COUNTS IN FINAL SHORTLIST ---")
print(tharsis_high_priority["Priority"].value_counts())

print("\n--- FIRST 30 FINAL CANDIDATES ---")
print(short_table.head(30).to_string(index=False))