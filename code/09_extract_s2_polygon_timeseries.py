from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask

BASE = Path(r"C:\\Projetos\\SAR_Optical_Perennial_Crops_Italy")
pilots = gpd.read_file(BASE / "data/processed/pilot_polygons_core20m.gpkg", layer="core20m")
s2root = BASE / "data/processed/sentinel2"
rows = []

for date_dir in sorted(p for p in s2root.glob("20*") if p.is_dir()):
    date = pd.to_datetime(date_dir.name, format="%Y%m%d").date()
    for metric in ["ndvi", "ndre", "ndmi", "gndvi"]:
        raster = date_dir / f"{date_dir.name}_{metric}.tif"
        if not raster.exists():
            continue
        with rasterio.open(raster) as src:
            pg = pilots.to_crs(src.crs)
            for _, row in pg.iterrows():
                arr, _ = mask(src, [row.geometry], crop=True, filled=False)
                band = arr[0]
                vals = band.compressed().astype("float64")
                vals = vals[np.isfinite(vals)]
                if src.nodata is not None:
                    vals = vals[vals != src.nodata]
                pixel_area = abs(src.transform.a * src.transform.e - src.transform.b * src.transform.d)
                expected_pixels = float(row["core_area_ha"]) * 10000.0 / pixel_area
                n = len(vals)
                rows.append({
                    "date": date.isoformat(), "pilot_id": row["pilot_id"],
                    "poly_id": row["poly_id"], "class4": row["class4"],
                    "sigla": row["SIGLA"], "zone": row["zone"],
                    "area_ha": float(row["area_ha_geom"]),
                    "core_area_ha": float(row["core_area_ha"]), "metric": metric,
                    "n_valid": n,
                    "valid_fraction": min(1.0, n / expected_pixels) if expected_pixels else np.nan,
                    "mean": float(np.mean(vals)) if n else np.nan,
                    "median": float(np.median(vals)) if n else np.nan,
                    "std": float(np.std(vals)) if n else np.nan,
                })

df = pd.DataFrame(rows)
out = BASE / "data/processed/s2_polygon_timeseries.csv"
df.to_csv(out, index=False)
print("Rows:", len(df))
if len(df):
    print(df.groupby(["date", "metric"])["valid_fraction"].median().to_string())
print(out)
