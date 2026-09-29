from pathlib import Path
import json
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import box

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
SEL = BASE / "metadata/sentinel2_l2a_pilot_selection.csv"
OUT = BASE / "data/raw/sentinel2"
OUT.mkdir(parents=True, exist_ok=True)
aoi4326 = gpd.read_file(BASE / "data/processed/aoi_corridor.geojson")

BANDS = {
    "red": "assets.red.href",
    "green": "assets.green.href",
    "nir": "assets.nir.href",
    "rededge1": "assets.rededge1.href",
    "swir16": "assets.swir16.href",
    "scl": "assets.scl.href",
}
df = pd.read_csv(SEL)
records = []
env_opts = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.tiff",
}
with rasterio.Env(**env_opts):
    for row in df.itertuples(index=False):
        scene = row.id
        dt = pd.to_datetime(row.datetime)
        scene_dir = OUT / dt.strftime("%Y%m%d") / scene
        scene_dir.mkdir(parents=True, exist_ok=True)
        for band, col in BANDS.items():
            url = getattr(row, col.replace(":", "_").replace(".", "_"), None)
            if not url or pd.isna(url):
                url = df.loc[df["id"].eq(scene), col].iloc[0]
            with rasterio.open(url) as src:
                aoi_src = aoi4326.to_crs(src.crs).geometry.iloc[0]
                inter = aoi_src.intersection(box(*src.bounds))
                if inter.is_empty:
                    continue
                win = from_bounds(*inter.bounds, transform=src.transform)
                win = win.round_offsets().round_lengths()
                arr = src.read(1, window=win)
                profile = src.profile.copy()
                profile.update(
                    driver="GTiff",
                    height=arr.shape[0],
                    width=arr.shape[1],
                    transform=src.window_transform(win),
                    compress="deflate",
                    tiled=True,
                    BIGTIFF="IF_SAFER",
                )
                dst = scene_dir / f"{scene}_{band}.tif"
                with rasterio.open(dst, "w", **profile) as out:
                    out.write(arr, 1)
                records.append({
                    "scene": scene, "date": dt.date().isoformat(),
                    "band": band, "source": url, "local": str(dst),
                    "width": arr.shape[1], "height": arr.shape[0],
                    "crs": str(src.crs),
                })
                print(dt.date(), scene, band, arr.shape)

(BASE / "metadata/sentinel2_download_manifest.json").write_text(
    json.dumps(records, indent=2), encoding="utf-8"
)
print(f"Downloaded {len(records)} Sentinel-2 AOI band subsets.")
