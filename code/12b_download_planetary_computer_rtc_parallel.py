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
SEL = pd.read_csv(BASE / "metadata/sentinel1_grd_pilot_selection.csv")
AOI = gpd.read_file(BASE / "data/processed/aoi_corridor.geojson")
OUT = BASE / "data/processed/sentinel1/rtc"
OUT.mkdir(parents=True, exist_ok=True)
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SIGN = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"

def signed_href(href):
    r = requests.get(SIGN, params={"href": href}, timeout=60)
    r.raise_for_status()
    return r.json()["href"]

items = []
for rec in SEL.itertuples(index=False):
    dt = pd.to_datetime(rec.startTime, utc=True)
    payload = {
        "collections": ["sentinel-1-rtc"],
        "bbox": [float(x) for x in AOI.total_bounds],
        "datetime": f"{dt:%Y-%m-%dT00:00:00Z}/{(dt + pd.Timedelta(days=1)):%Y-%m-%dT00:00:00Z}",
        "limit": 20,
    }
    feats = requests.post(STAC, json=payload, timeout=90).json().get("features", [])
    cand = [f for f in feats if f["properties"].get("sat:relative_orbit") == int(rec.pathNumber)
            and str(f["properties"].get("sat:orbit_state","")).upper() == str(rec.flightDirection).upper()]
    if not cand:
        raise RuntimeError(f"No RTC item for {rec.sceneName}")
    item = cand[0]
    for pol in ("vv","vh"):
        items.append((rec, item, pol))
def download_one(task):
    rec, item, pol = task
    dt = pd.to_datetime(rec.startTime, utc=True)
    scene_dir = OUT / item["id"]
    scene_dir.mkdir(parents=True, exist_ok=True)
    dst = scene_dir / f"{item['id']}_{pol.upper()}_gamma0_rtc.tif"
    if dst.exists() and dst.stat().st_size > 1_000_000:
        try:
            with rasterio.open(dst) as chk:
                if chk.width > 100 and chk.height > 100:
                    return {"status":"existing","scene_source":rec.sceneName,"rtc_item":item["id"],
                            "date":dt.date().isoformat(),"relative_orbit":int(rec.pathNumber),
                            "orbit_state":rec.flightDirection,"polarization":pol.upper(),
                            "source_href":item["assets"][pol]["href"],"local":str(dst),
                            "crs":str(chk.crs),"resolution_x":abs(chk.transform.a),
                            "resolution_y":abs(chk.transform.e),"nodata":chk.nodata,
                            "dtype":chk.dtypes[0],"height":chk.height,"width":chk.width}
        except Exception:
            pass
    href = item["assets"][pol]["href"]
    url = signed_href(href)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open(url) as src:
            aoi_src = AOI.to_crs(src.crs).geometry.iloc[0]
            inter = aoi_src.intersection(box(*src.bounds))
            win = from_bounds(*inter.bounds, transform=src.transform).round_offsets().round_lengths()
            arr = src.read(1, window=win)
            profile = src.profile.copy()
            profile.update(driver="GTiff",height=arr.shape[0],width=arr.shape[1],
                           transform=src.window_transform(win),count=1,
                           compress="deflate",tiled=True,BIGTIFF="IF_SAFER")
            with rasterio.open(dst, "w", **profile) as out:
                out.write(arr,1)
            return {"status":"downloaded","scene_source":rec.sceneName,"rtc_item":item["id"],
                    "date":dt.date().isoformat(),"relative_orbit":int(rec.pathNumber),
                    "orbit_state":rec.flightDirection,"polarization":pol.upper(),
                    "source_href":href,"local":str(dst),"crs":str(src.crs),
                    "resolution_x":abs(src.transform.a),"resolution_y":abs(src.transform.e),
                    "nodata":src.nodata,"dtype":src.dtypes[0],
                    "height":arr.shape[0],"width":arr.shape[1]}
manifest = []
with ThreadPoolExecutor(max_workers=4) as ex:
    futs = [ex.submit(download_one, t) for t in items]
    for fut in as_completed(futs):
        rec = fut.result()
        manifest.append(rec)
        print(rec["status"], rec["date"], rec["polarization"], rec["height"], rec["width"], flush=True)

manifest = sorted(manifest, key=lambda r:(r["date"],r["polarization"]))
(BASE / "metadata/planetary_computer_rtc_manifest.json").write_text(
    json.dumps(manifest, indent=2), encoding="utf-8")
pd.DataFrame(manifest).to_csv(BASE / "metadata/planetary_computer_rtc_manifest.csv", index=False)
print("RTC assets ready:", len(manifest), flush=True)
