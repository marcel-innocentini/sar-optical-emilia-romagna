from pathlib import Path
import re
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask

BASE = Path(r"C:\\Projetos\\SAR_Optical_Perennial_Crops_Italy")
RTC = BASE / "data/processed/sentinel1/rtc"
pilots = gpd.read_file(BASE / "data/processed/pilot_polygons_core20m.gpkg", layer="core20m")
rows = []

# Expected HyP3 RTC outputs in linear power (gamma0), one VV and VH raster per acquisition.
def find_pol_files(folder, pol):
    candidates = []
    for p in folder.rglob("*.tif*"):
        name = p.name.upper()
        if pol in name and "INC" not in name and "DEM" not in name:
            candidates.append(p)
    return sorted(candidates)

for folder in sorted(p for p in RTC.glob("*") if p.is_dir()):
    vv_files = find_pol_files(folder, "VV")
    vh_files = find_pol_files(folder, "VH")
    if not vv_files or not vh_files:
        continue
    vv_path, vh_path = vv_files[0], vh_files[0]
    m = re.search(r"(20\d{6})", folder.name + "_" + vv_path.name)
    date = pd.to_datetime(m.group(1), format="%Y%m%d").date() if m else None
    with rasterio.open(vv_path) as vv_src, rasterio.open(vh_path) as vh_src:
        pg = pilots.to_crs(vv_src.crs)
        for _, row in pg.iterrows():
            vv_ma, _ = mask(vv_src, [row.geometry], crop=True, filled=False)
            vh_ma, _ = mask(vh_src, [row.geometry], crop=True, filled=False)
            if vv_ma.shape != vh_ma.shape:
                raise RuntimeError("VV/VH crop grids are not aligned")
            vv = vv_ma[0].filled(np.nan).astype("float64")
            vh = vh_ma[0].filled(np.nan).astype("float64")
            good = np.isfinite(vv) & np.isfinite(vh) & (vv > 0) & (vh > 0)
            vv, vh = vv[good], vh[good]
            if len(vv) == 0:
                continue
            vv_mean = float(vv.mean())
            vh_mean = float(vh.mean())
            rows.append({
                "date": date.isoformat() if date else "",
                "pilot_id": row["pilot_id"], "class4": row["class4"],
                "zone": row["zone"], "area_ha": float(row["area_ha_geom"]),
                "n_valid": len(vv),
                "vv_gamma0_power_mean": vv_mean,
                "vh_gamma0_power_mean": vh_mean,
                "vv_gamma0_db": 10.0 * np.log10(vv_mean),
                "vh_gamma0_db": 10.0 * np.log10(vh_mean),
                "vh_vv_ratio_power": vh_mean / vv_mean,
                "vh_vv_ratio_db": 10.0 * np.log10(vh_mean / vv_mean),
            })

df = pd.DataFrame(rows)
out = BASE / "data/processed/s1_rtc_polygon_timeseries.csv"
df.to_csv(out, index=False)
print("Rows:", len(df))
print(out)
