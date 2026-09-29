from pathlib import Path
import json
import requests
import pandas as pd
import geopandas as gpd

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
META = BASE / "metadata"
META.mkdir(parents=True, exist_ok=True)
aoi = gpd.read_file(BASE / "data/processed/aoi_corridor.geojson")
bbox = [float(x) for x in aoi.total_bounds]
bbox_text = ",".join(f"{x:.8f}" for x in bbox)
DATE_START, DATE_END = "2023-01-01", "2023-12-31"

def asf_search(level):
    params = {
        "dataset": "SENTINEL-1",
        "bbox": bbox_text,
        "start": DATE_START,
        "end": DATE_END,
        "beamMode": "IW",
        "polarization": "VV+VH",
        "processingLevel": level,
        "output": "geojson",
        "maxResults": 500,
    }
    r = requests.get(
        "https://api.daac.asf.alaska.edu/services/search/param",
        params=params, timeout=120
    )
    r.raise_for_status()
    return r.json()

def flatten_asf(js):
    rows = []
    for f in js.get("features", []):
        p = f["properties"].copy()
        p["geometry_wkt"] = gpd.GeoSeries.from_wkt(
            [gpd.GeoSeries([f["geometry"]]).__geo_interface__ if False else None]
        ) if False else None
        rows.append(p)
    return pd.DataFrame(rows)

grd = asf_search("GRD_HD")
slc = asf_search("SLC")
(META / "sentinel1_grd_2023_asf.geojson").write_text(json.dumps(grd), encoding="utf-8")
(META / "sentinel1_slc_2023_asf.geojson").write_text(json.dumps(slc), encoding="utf-8")
grd_df = pd.json_normalize([f["properties"] for f in grd["features"]])
slc_df = pd.json_normalize([f["properties"] for f in slc["features"]])
for df in (grd_df, slc_df):
    if "startTime" in df:
        df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
        df.sort_values("startTime", inplace=True)
grd_df.to_csv(META / "sentinel1_grd_2023_catalog.csv", index=False)
slc_df.to_csv(META / "sentinel1_slc_2023_catalog.csv", index=False)

payload = {
    "collections": ["sentinel-2-c1-l2a"],
    "bbox": bbox,
    "datetime": f"{DATE_START}T00:00:00Z/{DATE_END}T23:59:59Z",
    "query": {"eo:cloud_cover": {"lt": 70}},
    "limit": 100,
}
url = "https://earth-search.aws.element84.com/v1/search"
items = []
while url:
    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    js = r.json()
    items.extend(js.get("features", []))
    nxt = next((x for x in js.get("links", []) if x.get("rel") == "next"), None)
    if not nxt:
        break
    url = nxt["href"]
    payload = nxt.get("body", payload)

s2 = {"type": "FeatureCollection", "features": items}
(META / "sentinel2_l2a_2023_earthsearch.geojson").write_text(
    json.dumps(s2), encoding="utf-8"
)
s2_rows = []
for f in items:
    p = f["properties"]
    s2_rows.append({
        "id": f["id"],
        "datetime": p.get("datetime"),
        "cloud_cover": p.get("eo:cloud_cover"),
        "mgrs_tile": p.get("mgrs:tile"),
        "platform": p.get("platform"),
        "assets": json.dumps({k: v.get("href") for k, v in f["assets"].items()}),
    })
s2_df = pd.DataFrame(s2_rows)
if not s2_df.empty:
    s2_df["datetime"] = pd.to_datetime(s2_df["datetime"], utc=True)
    s2_df.sort_values(["datetime", "cloud_cover"], inplace=True)
s2_df.to_csv(META / "sentinel2_l2a_2023_catalog.csv", index=False)

print("AOI bbox WGS84:", bbox)
print("S1 GRD scenes:", len(grd_df))
print(grd_df.groupby(["flightDirection", "pathNumber"]).size().to_string())
print("S1 SLC scenes:", len(slc_df))
print(slc_df.groupby(["flightDirection", "pathNumber"]).size().to_string())
print("S2 L2A items (<70% scene cloud):", len(s2_df))
print(s2_df[["datetime", "cloud_cover", "mgrs_tile", "id"]].head(20).to_string(index=False))
