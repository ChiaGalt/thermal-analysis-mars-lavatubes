import re
import numpy as np
import pandas as pd
import rasterio
from pathlib import Path

# =========================
# INPUT / OUTPUT
# =========================

INPUT_CSV = "04_global_shortlist_for_thermal_analysis.csv"
OUTPUT_CSV = "09_global_thermal_analysis_results.csv"

RASTER_FOLDER = Path(".")
TIF_PATTERN = "THEMIS_TI_Mosaic_Quant_*_100mpp.tif"

# Mars radius used by THEMIS simple cylindrical projection
MARS_RADIUS_M = 3396190.0
M_PER_DEG = 2 * np.pi * MARS_RADIUS_M / 360.0

# Window settings
CENTER_RADIUS_PX = 1       # 3x3 around candidate
SURROUNDING_INNER_PX = 5   # exclude central area
SURROUNDING_OUTER_PX = 20  # about 2 km if 100 m/pixel


# =========================
# THEMIS TILE FUNCTIONS
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


def lonlat_to_mars_xy(lon, lat):
    """
    Converts longitude/latitude degrees to simple cylindrical projected meters.

    The catalog uses 0–360 East longitudes.
    GDAL/THEMIS projected rasters usually represent longitudes >180E
    as negative longitudes:
        240E = -120
        300E = -60
    """

    lon = lon % 360

    if lon > 180:
        lon = lon - 360

    x = lon * M_PER_DEG
    y = lat * M_PER_DEG

    return x, y

def build_raster_dict():
    raster_dict = {}

    for tif in RASTER_FOLDER.glob(TIF_PATTERN):
        match = re.search(r"Quant_(.*?)_100mpp", tif.name)
        if match:
            tile = match.group(1)
            raster_dict[tile] = tif

    return raster_dict


def clean_array(arr, nodata=None):
    arr = arr.astype("float64")

    if nodata is not None:
        arr[arr == nodata] = np.nan

    # Remove extreme ISIS/GDAL NoData-like values
    arr[arr < -1e20] = np.nan

    return arr


def extract_window_stats(src, row, col):
    """
    Extracts:
    - center value
    - 3x3 median around candidate
    - surrounding annulus mean/std
    - delta between center and surrounding
    """

    height = src.height
    width = src.width

    r0 = max(row - SURROUNDING_OUTER_PX, 0)
    r1 = min(row + SURROUNDING_OUTER_PX + 1, height)
    c0 = max(col - SURROUNDING_OUTER_PX, 0)
    c1 = min(col + SURROUNDING_OUTER_PX + 1, width)

    window = rasterio.windows.Window(
        col_off=c0,
        row_off=r0,
        width=c1 - c0,
        height=r1 - r0
    )

    arr = src.read(1, window=window)
    arr = clean_array(arr, src.nodata)

    local_row = row - r0
    local_col = col - c0

    # Candidate center pixel
    center_value = arr[local_row, local_col]

    # Small 3x3 median around candidate
    cr0 = max(local_row - CENTER_RADIUS_PX, 0)
    cr1 = min(local_row + CENTER_RADIUS_PX + 1, arr.shape[0])
    cc0 = max(local_col - CENTER_RADIUS_PX, 0)
    cc1 = min(local_col + CENTER_RADIUS_PX + 1, arr.shape[1])

    center_patch = arr[cr0:cr1, cc0:cc1]
    center_median = np.nanmedian(center_patch)
    center_mean = np.nanmean(center_patch)

    # Surrounding annulus
    yy, xx = np.indices(arr.shape)
    dist = np.sqrt((yy - local_row) ** 2 + (xx - local_col) ** 2)

    annulus_mask = (
        (dist >= SURROUNDING_INNER_PX) &
        (dist <= SURROUNDING_OUTER_PX)
    )

    surrounding = arr[annulus_mask]

    surrounding_mean = np.nanmean(surrounding)
    surrounding_median = np.nanmedian(surrounding)
    surrounding_std = np.nanstd(surrounding)

    delta_ti = center_median - surrounding_mean

    if surrounding_std > 0:
        local_zscore = delta_ti / surrounding_std
    else:
        local_zscore = np.nan

    return {
        "TI_center_pixel": center_value,
        "TI_center_mean_3x3": center_mean,
        "TI_center_median_3x3": center_median,
        "TI_surrounding_mean": surrounding_mean,
        "TI_surrounding_median": surrounding_median,
        "TI_surrounding_std": surrounding_std,
        "Delta_TI": delta_ti,
        "Local_TI_zscore": local_zscore,
        "valid_surrounding_pixels": np.sum(~np.isnan(surrounding))
    }


# =========================
# MAIN
# =========================

def main():
    df = pd.read_csv(INPUT_CSV)

    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df = df.dropna(subset=["longitude", "latitude"]).copy()

    # Add THEMIS tile if missing
    if "themis_tile" not in df.columns:
        df["themis_lon_tile"] = df["longitude"].apply(get_lon_tile)
        df["themis_lat_tile"] = df["latitude"].apply(get_lat_tile)
        df["themis_tile"] = df["themis_lat_tile"] + df["themis_lon_tile"]

    raster_dict = build_raster_dict()

    print("\n--- AVAILABLE THEMIS RASTERS ---")
    for tile, path in sorted(raster_dict.items()):
        print(f"{tile}: {path.name}")

    results = []

    # Open rasters only when needed
    opened = {}

    for idx, row in df.iterrows():
        label = row.get("label", f"candidate_{idx}")
        lon = row["longitude"]
        lat = row["latitude"]
        tile = row["themis_tile"]

        result = row.to_dict()

        if tile not in raster_dict:
            result.update({
                "thermal_status": "missing_raster",
                "TI_center_pixel": np.nan,
                "TI_center_mean_3x3": np.nan,
                "TI_center_median_3x3": np.nan,
                "TI_surrounding_mean": np.nan,
                "TI_surrounding_median": np.nan,
                "TI_surrounding_std": np.nan,
                "Delta_TI": np.nan,
                "Local_TI_zscore": np.nan,
                "valid_surrounding_pixels": 0
            })
            results.append(result)
            continue

        if tile not in opened:
            opened[tile] = rasterio.open(raster_dict[tile])

        src = opened[tile]

        try:
            x, y = lonlat_to_mars_xy(lon, lat)
            row_px, col_px = src.index(x, y)

            if not (0 <= row_px < src.height and 0 <= col_px < src.width):
                result.update({"thermal_status": "outside_raster"})
            else:
                stats = extract_window_stats(src, row_px, col_px)
                result.update(stats)
                result.update({
                    "thermal_status": "ok",
                    "pixel_row": row_px,
                    "pixel_col": col_px,
                    "raster_file": raster_dict[tile].name
                })

        except Exception as e:
            result.update({
                "thermal_status": f"error: {e}",
                "TI_center_pixel": np.nan,
                "TI_center_mean_3x3": np.nan,
                "TI_center_median_3x3": np.nan,
                "TI_surrounding_mean": np.nan,
                "TI_surrounding_median": np.nan,
                "TI_surrounding_std": np.nan,
                "Delta_TI": np.nan,
                "Local_TI_zscore": np.nan,
                "valid_surrounding_pixels": 0
            })

        results.append(result)

    for src in opened.values():
        src.close()

    out = pd.DataFrame(results)

    # Ranking: higher TI and positive anomaly are potentially more thermally stable
    out["thermal_rank_score"] = (
        out["TI_center_median_3x3"].rank(pct=True) * 0.5 +
        out["Delta_TI"].rank(pct=True) * 0.3 +
        out["Local_TI_zscore"].rank(pct=True) * 0.2
    )

    out = out.sort_values(
        by=["thermal_rank_score", "Delta_TI", "TI_center_median_3x3"],
        ascending=[False, False, False]
    )

    out.to_csv(OUTPUT_CSV, index=False)

    print("\n--- EXTRACTION COMPLETE ---")
    print(f"Input candidates: {len(df)}")
    print(f"Output file: {OUTPUT_CSV}")

    print("\n--- STATUS COUNTS ---")
    print(out["thermal_status"].value_counts())

    print("\n--- TOP 20 THERMAL CANDIDATES ---")
    cols = [
        "label", "longitude", "latitude", "TypeCode", "Priority",
        "themis_tile", "TI_center_median_3x3",
        "TI_surrounding_mean", "Delta_TI",
        "Local_TI_zscore", "thermal_rank_score", "Comment"
    ]
    existing_cols = [c for c in cols if c in out.columns]
    print(out[existing_cols].head(20).to_string(index=False))


if __name__ == "__main__":
    main()