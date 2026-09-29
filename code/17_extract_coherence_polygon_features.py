from pathlib import Path
import zipfile
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
ROOT = BASE / "data/processed/sentinel1/coherence"
pilots = gpd.read_file(
    BASE / "data/processed/pilot_polygons_core20m.gpkg", layer="core20m"
)

for z in ROOT.glob("*.zip"):
    target = ROOT / f"{z.stem}_corr.tif"
    if target.exists():
        continue
    with zipfile.ZipFile(z) as src:
        members = [n for n in src.namelist() if n.endswith("_corr.tif")]
        if len(members) != 1:
            raise RuntimeError(f"Expected one coherence raster in {z.name}; found {len(members)}")
        with src.open(members[0]) as inp, open(target, "wb") as out:
            import shutil
            shutil.copyfileobj(inp, out)

corrs = sorted(ROOT.glob("*_corr.tif"))
if not corrs:
    raise FileNotFoundError("No HyP3 *_corr.tif coherence raster found")
if len(corrs) > 1:
    print("WARNING: multiple coherence rasters found; processing all:", len(corrs))

rows = []
for corr in corrs:
    with rasterio.open(corr) as src:
        pg = pilots.to_crs(src.crs)
        for _, row in pg.iterrows():
            arr, _ = mask(src, [row.geometry], crop=True, filled=False)
            vals = arr[0].compressed().astype("float64")
            vals = vals[np.isfinite(vals) & (vals >= 0) & (vals <= 1)]
            rows.append({
                "product": corr.stem,
                "pilot_id": row["pilot_id"],
                "class4": row["class4"],
                "zone": row["zone"],
                "core_area_ha": float(row["core_area_ha"]),
                "n_valid": len(vals),
                "coherence_mean": float(vals.mean()) if len(vals) else np.nan,
                "coherence_median": float(np.median(vals)) if len(vals) else np.nan,
                "coherence_std": float(vals.std()) if len(vals) else np.nan,
                "coherence_p10": float(np.percentile(vals,10)) if len(vals) else np.nan,
                "coherence_p90": float(np.percentile(vals,90)) if len(vals) else np.nan,
            })

df = pd.DataFrame(rows)
out = BASE / "data/processed/coherence_polygon_features.csv"
df.to_csv(out, index=False)
print("Rows:", len(df))
print(df.groupby("class4")["coherence_median"].agg(["count","median","mean","std"]).to_string())
print(out)
