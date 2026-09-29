from pathlib import Path
import json
import requests
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import box

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
SEL = pd.read_csv(BASE / "metadata/sentinel1_grd_pilot_selection.csv")
AOI = gpd.read_file(BASE / "data/processed/aoi_corridor.geojson")
OUT = BASE / "data/processed/sentinel1/rtc"
OUT.mkdir(parents=True, exist_ok=True)

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SIGN = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"
manifest = []

def signed_href(href):
    r = requests.get(SIGN, params={"href": href}, timeout=60)
    r.raise_for_status()
    return r.json()["href"]

for rec in SEL.itertuples(index=False):
    dt = pd.to_datetime(rec.startTime, utc=True)
    start = dt.strftime("%Y-%m-%dT00:00:00Z")
    end = (dt + pd.Timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
    payload = {
        "collections": ["sentinel-1-rtc"],
        "bbox": [float(x) for x in AOI.total_bounds],
        "datetime": f"{start}/{end}",
        "limit": 20,
    }
    sr = requests.post(STAC, json=payload, timeout=90)
    sr.raise_for_status()
    feats = sr.json().get("features", [])
    candidates = [
        f for f in feats
        if f["properties"].get("sat:relative_orbit") == int(rec.pathNumber)
        and str(f["properties"].get("sat:orbit_state", "")).upper() == str(rec.flightDirection).upper()
    ]
    if not candidates:
        raise RuntimeError(f"No RTC item found for {rec.sceneName}")
    item = candidates[0]
    scene_dir = OUT / item["id"]
    scene_dir.mkdir(parents=True, exist_ok=True)

    for pol in ["vv", "vh"]:
        href = item["assets"][pol]["href"]
        url = signed_href(href)
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
            with rasterio.open(url) as src:
                aoi_src = AOI.to_crs(src.crs).geometry.iloc[0]
                inter = aoi_src.intersection(box(*src.bounds))
                if inter.is_empty:
                    raise RuntimeError(f"RTC {item['id']} does not overlap AOI")
                win = from_bounds(*inter.bounds, transform=src.transform)
                win = win.round_offsets().round_lengths()
                arr = src.read(1, window=win)
                profile = src.profile.copy()
                profile.update(
                    driver="GTiff", height=arr.shape[0], width=arr.shape[1],
                    transform=src.window_transform(win), count=1,
                    compress="deflate", tiled=True, BIGTIFF="IF_SAFER"
                )
                dst = scene_dir / f"{item['id']}_{pol.upper()}_gamma0_rtc.tif"
                with rasterio.open(dst, "w", **profile) as out:
                    out.write(arr, 1)

                manifest.append({
                    "scene_source": rec.sceneName,
                    "rtc_item": item["id"],
                    "date": dt.date().isoformat(),
                    "relative_orbit": int(rec.pathNumber),
                    "orbit_state": rec.flightDirection,
                    "polarization": pol.upper(),
                    "source_href": href,
                    "local": str(dst),
                    "crs": str(src.crs),
                    "resolution_x": abs(src.transform.a),
                    "resolution_y": abs(src.transform.e),
                    "nodata": src.nodata,
                    "dtype": src.dtypes[0],
                    "height": arr.shape[0],
                    "width": arr.shape[1],
                })
                print(dt.date(), item["id"], pol.upper(), arr.shape, src.crs)

(BASE / "metadata/planetary_computer_rtc_manifest.json").write_text(
    json.dumps(manifest, indent=2), encoding="utf-8"
)
pd.DataFrame(manifest).to_csv(
    BASE / "metadata/planetary_computer_rtc_manifest.csv", index=False
)
print("RTC assets downloaded:", len(manifest))
