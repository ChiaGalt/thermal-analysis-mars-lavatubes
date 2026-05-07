import pandas as pd
from pathlib import Path

# =========================
# INPUT
# =========================

INPUT_CSV = "04_global_shortlist_for_thermal_analysis.csv"

# Se in futuro vuoi usare tutto il catalogo, cambia con:
# INPUT_CSV = "Mars_Extended_Cave_Catalog.csv"

OUTPUT_CSV = "07_candidates_with_themis_tiles.csv"
OUTPUT_TILE_SUMMARY = "08_required_themis_tiles_summary.csv"

df = pd.read_csv(INPUT_CSV)

# =========================
# CHECK COLUMNS
# =========================

required_columns = ["label", "longitude", "latitude"]

for col in required_columns:
    if col not in df.columns:
        raise ValueError(f"Missing required column: {col}")

df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")

df = df.dropna(subset=["longitude", "latitude"]).copy()

# =========================
# THEMIS TILE ASSIGNMENT
# =========================
# Longitudes in your catalog are 0–360 East.
# THEMIS longitude tiles are named:
# 000E, 060E, 120E, 180E, 240E, 300E
#
# The tile label is based on 60-degree longitude blocks:
# 000E: 0–60E
# 060E: 60–120E
# 120E: 120–180E
# 180E: 180–240E
# 240E: 240–300E
# 300E: 300–360E
#
# Latitude bands used here:
# 30N: 30N to 60N
# 00N: 0 to 30N
# 30S: -30 to 0
# 60S: -60 to -30
#
# If you later include polar candidates beyond ±60,
# we can extend this.

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
    else:
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
    else:
        return None


df["themis_lon_tile"] = df["longitude"].apply(get_lon_tile)
df["themis_lat_tile"] = df["latitude"].apply(get_lat_tile)

df["themis_tile"] = df["themis_lat_tile"] + df["themis_lon_tile"]

df["themis_quantitative_product_name"] = (
    "THEMIS Thermal Inertia Mosaic Quantitative "
    + df["themis_tile"]
    + " 100mpp"
)

# =========================
# SUMMARY
# =========================

tile_summary = (
    df.groupby(["themis_tile", "themis_lat_tile", "themis_lon_tile"])
    .size()
    .reset_index(name="candidate_count")
    .sort_values(by="candidate_count", ascending=False)
)

# =========================
# SAVE
# =========================

df.to_csv(OUTPUT_CSV, index=False)
tile_summary.to_csv(OUTPUT_TILE_SUMMARY, index=False)

print("\n--- THEMIS TILE ASSIGNMENT COMPLETE ---")
print(f"Input candidates: {len(df)}")
print(f"Unique required tiles: {df['themis_tile'].nunique()}")

print("\n--- REQUIRED THEMIS TILES ---")
print(tile_summary.to_string(index=False))

print("\nSaved:")
print(f"- {OUTPUT_CSV}")
print(f"- {OUTPUT_TILE_SUMMARY}")