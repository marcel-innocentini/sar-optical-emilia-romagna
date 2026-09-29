from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import requests
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import box

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
ASF = gpd.read_file(BASE / "metadata/sentinel1_grd_2023_asf.geojson")
AOI = gpd.read_file(BASE / "data/processed/aoi_corridor.geojson")
OUT = BASE / "data/processed/sentinel1/rtc_2023_full"
OUT.mkdir(parents=True, exist_ok=True)

scenes = ASF[
    (ASF["flightDirection"] == "DESCENDING") &
    (ASF["pathNumber"] == 95) &
    (ASF["frameNumber"] == 445)
].copy()
scenes["startTime"] = pd.to_datetime(scenes["startTime"], utc=True)
scenes = scenes.sort_values("startTime")

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SIGN = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"
def signed_href(href):
    r = requests.get(SIGN, params={"href": href}, timeout=60)
    r.raise_for_status()
    return r.json()["href"]

tasks = []
for rec in scenes.itertuples(index=False):
    dt = rec.startTime
    payload = {
        "collections": ["sentinel-1-rtc"],
        "bbox": [float(x) for x in AOI.total_bounds],
        "datetime": f"{dt:%Y-%m-%dT00:00:00Z}/{(dt + pd.Timedelta(days=1)):%Y-%m-%dT00:00:00Z}",
        "limit": 20,
    }
    sr = requests.post(STAC, json=payload, timeout=90)
    sr.raise_for_status()
    feats = sr.json().get("features", [])
    cand = [
        f for f in feats
        if f["properties"].get("sat:relative_orbit") == 95
        and str(f["properties"].get("sat:orbit_state","")).lower() == "descending"
    ]
    if not cand:
        print("MISSING RTC", rec.sceneName, flush=True)
        continue
    item = cand[0]
    for pol in ("vv","vh"):
        tasks.append((rec.sceneName, dt, item, pol))
def download_one(task):
    scene, dt, item, pol = task
    day = dt.strftime("%Y%m%d")
    scene_dir = OUT / day
    scene_dir.mkdir(parents=True, exist_ok=True)
    dst = scene_dir / f"{item['id']}_{pol.upper()}_gamma0_rtc.tif"

    if dst.exists() and dst.stat().st_size > 1_000_000:
        with rasterio.open(dst) as chk:
            return {
                "status":"existing","scene_source":scene,"date":day,
                "rtc_item":item["id"],"polarization":pol.upper(),
                "local":str(dst),"crs":str(chk.crs),
                "resolution_x":abs(chk.transform.a),"resolution_y":abs(chk.transform.e),
                "height":chk.height,"width":chk.width
            }

    href = item["assets"][pol]["href"]
    url = signed_href(href)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open(url) as src:
            aoi_src = AOI.to_crs(src.crs).geometry.iloc[0]
            inter = aoi_src.intersection(box(*src.bounds))
            win = from_bounds(*inter.bounds, transform=src.transform).round_offsets().round_lengths()
            arr = src.read(1, window=win)
            profile = src.profile.copy()
            profile.update(driver="GTiff", height=arr.shape[0], width=arr.shape[1],
                           transform=src.window_transform(win), count=1,
                           compress="deflate", tiled=True, BIGTIFF="IF_SAFER")
            with rasterio.open(dst, "w", **profile) as out:
                out.write(arr, 1)
            return {
                "status":"downloaded","scene_source":scene,"date":day,
                "rtc_item":item["id"],"polarization":pol.upper(),
                "source_href":href,"local":str(dst),"crs":str(src.crs),
                "resolution_x":abs(src.transform.a),"resolution_y":abs(src.transform.e),
                "height":arr.shape[0],"width":arr.shape[1],
                "nodata":src.nodata,"dtype":src.dtypes[0]
            }

manifest = []
with ThreadPoolExecutor(max_workers=1) as ex:
    futs = [ex.submit(download_one, t) for t in tasks]
    for fut in as_completed(futs):
        rec = fut.result()
        manifest.append(rec)
        print(rec["status"], rec["date"], rec["polarization"], flush=True)

manifest = sorted(manifest, key=lambda x:(x["date"],x["polarization"]))
pd.DataFrame(manifest).to_csv(BASE / "metadata/rtc_2023_full_manifest.csv", index=False)
(BASE / "metadata/rtc_2023_full_manifest.json").write_text(
    json.dumps(manifest, indent=2), encoding="utf-8"
)
print("Scenes selected:", len(scenes), flush=True)
print("RTC assets ready:", len(manifest), flush=True)
