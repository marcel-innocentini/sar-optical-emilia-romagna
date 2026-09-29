from pathlib import Path
import math
import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
LANDUSE = BASE / "data/raw/uso_suolo_2023/etrs89/Uso_Suolo_Dettaglio_2023_ETRS89.shp"
OUT = BASE / "data/processed"
OUT.mkdir(parents=True, exist_ok=True)

CITY_ROWS = [
    ("Imola", 11.7141233, 44.3535145),
    ("Castel Bolognese", 11.7999064, 44.3303030),
    ("Faenza", 11.8832055, 44.2855555),
]
cities = gpd.GeoDataFrame(
    {"city": [r[0] for r in CITY_ROWS]},
    geometry=gpd.points_from_xy([r[1] for r in CITY_ROWS], [r[2] for r in CITY_ROWS]),
    crs="EPSG:4326",
).to_crs(25832)

axis = LineString(cities.geometry.tolist())
aoi = gpd.GeoDataFrame({"name": ["Imola-CastelBolognese-Faenza_8km"]},
                       geometry=[axis.buffer(8000)], crs=25832)
aoi.to_file(OUT / "aoi_corridor.gpkg", layer="aoi", driver="GPKG")
aoi.to_crs(4326).to_file(OUT / "aoi_corridor.geojson", driver="GeoJSON")
cities.to_file(OUT / "aoi_corridor.gpkg", layer="city_centres", driver="GPKG")

bbox = tuple(aoi.total_bounds)
lu = gpd.read_file(LANDUSE, bbox=bbox)
lu = lu[lu.intersects(aoi.geometry.iloc[0])].copy()

classes = {"Cv": "VINEYARD", "Cf": "ORCHARD", "Co": "OLIVE",
           "Se": "ANNUAL", "Sn": "ANNUAL"}
target = lu[lu["SIGLA"].isin(classes)].copy()
target["class4"] = target["SIGLA"].map(classes)
target["area_ha_geom"] = target.geometry.area / 10000.0
target["perimeter_m"] = target.geometry.length
target["compactness"] = (
    4 * math.pi * target.geometry.area / target["perimeter_m"].pow(2)
)
cent = target.geometry.centroid
for city, point in zip(cities["city"], cities.geometry):
    target[f"d_{city.replace(' ', '_')}_m"] = cent.distance(point)
dist_cols = [c for c in target.columns if c.startswith("d_")]
target["zone"] = target[dist_cols].idxmin(axis=1).str.removeprefix("d_").str.removesuffix("_m")
target = target.reset_index(drop=True)
target["poly_id"] = [f"ER23_{s}_{i:05d}" for i, s in enumerate(target["SIGLA"], 1)]

candidates = target[
    (target["area_ha_geom"] >= 2.0) &
    (target["area_ha_geom"] <= 30.0) &
    (target["compactness"] >= 0.15)
].copy()
candidates["score"] = (
    candidates["compactness"] -
    0.03 * (candidates["area_ha_geom"] - 6.0).abs() / 6.0
)

parts = []
for cls in ["VINEYARD", "ORCHARD", "OLIVE", "ANNUAL"]:
    c = candidates[candidates["class4"] == cls]
    for zone in ["Imola", "Castel_Bolognese", "Faenza"]:
        z = c[c["zone"] == zone].sort_values("score", ascending=False)
        parts.append(z.head(4))
pilots = pd.concat(parts, ignore_index=True) if parts else candidates.iloc[0:0].copy()
pilots = gpd.GeoDataFrame(pilots, geometry="geometry", crs=target.crs)
pilots["pilot_id"] = [f"P{i:03d}" for i in range(1, len(pilots) + 1)]

target.to_file(OUT / "landuse_target_aoi.gpkg", layer="target_classes", driver="GPKG")
pilots.to_file(OUT / "pilot_polygons.gpkg", layer="pilots", driver="GPKG")
csv_cols = ["pilot_id", "poly_id", "SIGLA", "COD_TOT", "DESCR", "class4",
            "zone", "area_ha_geom", "compactness"]
pilots[csv_cols].to_csv(OUT / "pilot_polygons.csv", index=False)

summary = (
    target.groupby(["class4", "zone"]).size().rename("n_all").reset_index()
    .merge(candidates.groupby(["class4", "zone"]).size().rename("n_candidates").reset_index(),
           on=["class4", "zone"], how="left")
    .merge(pilots.groupby(["class4", "zone"]).size().rename("n_pilots").reset_index(),
           on=["class4", "zone"], how="left")
    .fillna(0)
)
summary.to_csv(OUT / "landuse_selection_summary.csv", index=False)

print("AOI bounds EPSG:25832:", bbox)
print("Target polygons in AOI:", len(target))
print(summary.to_string(index=False))
print("\nPilot polygons:", len(pilots))
print(pilots[csv_cols].to_string(index=False))
