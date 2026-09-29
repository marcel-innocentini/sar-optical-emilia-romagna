from pathlib import Path
import re
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
ROOT = BASE / "data/processed/sentinel1/rtc_2023_full"
pilots = gpd.read_file(
    BASE / "data/processed/pilot_polygons_core20m.gpkg", layer="core20m"
)

rows = []
for day_dir in sorted(p for p in ROOT.glob("20*") if p.is_dir()):
    vv_files = sorted(day_dir.glob("*_VV_gamma0_rtc.tif"))
    vh_files = sorted(day_dir.glob("*_VH_gamma0_rtc.tif"))
    if len(vv_files) != 1 or len(vh_files) != 1:
        print("SKIP incomplete", day_dir.name, len(vv_files), len(vh_files))
        continue
    vv_path, vh_path = vv_files[0], vh_files[0]
    date = pd.to_datetime(day_dir.name, format="%Y%m%d").date()

    with rasterio.open(vv_path) as vv_src, rasterio.open(vh_path) as vh_src:
        if vv_src.crs != vh_src.crs or vv_src.transform != vh_src.transform:
            raise RuntimeError(f"Grid mismatch on {date}")
        pg = pilots.to_crs(vv_src.crs)
        for _, row in pg.iterrows():
            vv_ma, _ = mask(vv_src, [row.geometry], crop=True, filled=False)
            vh_ma, _ = mask(vh_src, [row.geometry], crop=True, filled=False)
            vv = vv_ma[0].filled(np.nan).astype("float64")
            vh = vh_ma[0].filled(np.nan).astype("float64")
            good = np.isfinite(vv) & np.isfinite(vh) & (vv > 0) & (vh > 0)
            vv, vh = vv[good], vh[good]
            if len(vv) == 0:
                continue

            vv_mean = float(vv.mean())
            vh_mean = float(vh.mean())
            rows.append({
                "date": date.isoformat(),
                "pilot_id": row["pilot_id"],
                "class4": row["class4"],
                "zone": row["zone"],
                "core_area_ha": float(row["core_area_ha"]),
                "n_valid": len(vv),
                "vv_gamma0_power_mean": vv_mean,
                "vh_gamma0_power_mean": vh_mean,
                "vv_gamma0_db": 10.0 * np.log10(vv_mean),
                "vh_gamma0_db": 10.0 * np.log10(vh_mean),
                "vh_vv_ratio_power": vh_mean / vv_mean,
                "vh_vv_ratio_db": 10.0 * np.log10(vh_mean / vv_mean),
            })
df = pd.DataFrame(rows)
n_dates = df["date"].nunique() if len(df) else 0
if n_dates != 30:
    raise RuntimeError(f"Full-year extraction requires 30 complete RTC dates; found {n_dates}.")
out = BASE / "data/processed/s1_rtc_polygon_timeseries_full2023.csv"
df.to_csv(out, index=False)

print("Dates:", n_dates)
print("Polygons:", df["pilot_id"].nunique() if len(df) else 0)
print("Rows:", len(df))
if len(df):
    print(df.groupby("date")["pilot_id"].nunique().tail().to_string())
print(out)
