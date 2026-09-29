from pathlib import Path
import pandas as pd
import geopandas as gpd

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
META = BASE / "metadata"
aoi = gpd.read_file(BASE / "data/processed/aoi_corridor.geojson").to_crs(25832)
aoi_geom = aoi.geometry.iloc[0]
aoi_area = aoi_geom.area

def add_overlap(g):
    g = g.to_crs(25832).copy()
    g["overlap"] = g.geometry.intersection(aoi_geom).area / aoi_area
    g["date"] = pd.to_datetime(g["startTime"], utc=True).dt.normalize()
    return g

grd = add_overlap(gpd.read_file(META / "sentinel1_grd_2023_asf.geojson"))
slc = add_overlap(gpd.read_file(META / "sentinel1_slc_2023_asf.geojson"))
good = grd[grd["overlap"] >= 0.98].copy()
route_stats = (good.groupby(["flightDirection","pathNumber","frameNumber"])
               .size().rename("n").reset_index().sort_values("n", ascending=False))
route = route_stats.iloc[0]
mask = ((good["flightDirection"] == route["flightDirection"]) &
        (good["pathNumber"] == route["pathNumber"]) &
        (good["frameNumber"] == route["frameNumber"]))
track = good[mask].sort_values("date").copy()
targets = pd.to_datetime(
    ["2023-03-15","2023-05-15","2023-07-15","2023-09-15","2023-11-01"], utc=True
)
rows = []
for t in targets:
    i = (track["date"] - t).abs().idxmin()
    rows.append(track.loc[i])
s1_sel = gpd.GeoDataFrame(rows, crs=track.crs).drop_duplicates("sceneName")
cols = ["sceneName","startTime","flightDirection","pathNumber","frameNumber",
        "orbit","polarization","bytes","url","overlap"]
s1_sel[cols].to_csv(META / "sentinel1_grd_pilot_selection.csv", index=False)

slc_track = slc[
    (slc["flightDirection"] == route["flightDirection"]) &
    (slc["pathNumber"] == route["pathNumber"]) &
    (slc["overlap"] >= 0.98)
].sort_values("date").copy()
pairs = []
vals = list(slc_track.itertuples())
for a, b in zip(vals[:-1], vals[1:]):
    dt = (b.date - a.date).days
    if 10 <= dt <= 14:
        mid = a.date + (b.date - a.date) / 2
        score = abs(dt - 12) + abs((mid - pd.Timestamp("2023-06-15", tz="UTC")).days) / 30
        pairs.append((score, a.sceneName, a.startTime, b.sceneName, b.startTime, dt))
pair_df = pd.DataFrame(pairs, columns=["score","master_scene","master_time",
                                      "slave_scene","slave_time","delta_days"]).sort_values("score")
pair_df.head(10).to_csv(META / "sentinel1_slc_coherence_candidates.csv", index=False)
s2 = gpd.read_file(META / "sentinel2_l2a_2023_earthsearch.geojson").to_crs(25832)
s2["date"] = pd.to_datetime(s2["datetime"], utc=True).dt.normalize()
date_rows = []
for d, grp in s2.groupby("date"):
    union = grp.geometry.union_all()
    coverage = union.intersection(aoi_geom).area / aoi_area
    inter = grp[grp.geometry.intersects(aoi_geom)]
    cloud = float(inter["eo:cloud_cover"].mean()) if len(inter) else 100.0
    date_rows.append((d, coverage, cloud, len(inter)))
dates = pd.DataFrame(date_rows, columns=["date","coverage","mean_scene_cloud","n_tiles"])
dates = dates[(dates["coverage"] >= 0.99) & (dates["mean_scene_cloud"] <= 25)].copy()

chosen_dates = []
for t in targets:
    if dates.empty:
        break
    score = (dates["date"] - t).abs().dt.days + dates["mean_scene_cloud"] * 0.35
    chosen_dates.append(dates.loc[score.idxmin(), "date"])
chosen_dates = pd.Series(chosen_dates).drop_duplicates().tolist()
s2_sel = s2[s2["date"].isin(chosen_dates) & s2.geometry.intersects(aoi_geom)].copy()
s2_cols = ["id","datetime","eo:cloud_cover","grid:code",
           "assets.red.href","assets.green.href","assets.nir.href",
           "assets.rededge1.href","assets.swir16.href","assets.scl.href"]
s2_sel[s2_cols].sort_values("datetime").to_csv(
    META / "sentinel2_l2a_pilot_selection.csv", index=False
)

print("Selected S1 route:")
print(route.to_string())
print("\nS1 GRD pilot dates:")
print(s1_sel[cols].to_string(index=False))
print("\nTop SLC coherence pairs:")
print(pair_df.head(6).to_string(index=False))
print("\nSelected S2 dates:")
print(dates[dates["date"].isin(chosen_dates)].sort_values("date").to_string(index=False))
