from pathlib import Path
import geopandas as gpd

BASE = Path(r"C:\\Projetos\\SAR_Optical_Perennial_Crops_Italy")
g = gpd.read_file(BASE / "data/processed/pilot_polygons.gpkg", layer="pilots")
core = g.copy()
core.geometry = core.geometry.buffer(-20.0)
core["core_buffer_m"] = 20.0
core["core_area_ha"] = core.geometry.area / 10000.0
core["core_fraction"] = core["core_area_ha"] / core["area_ha_geom"]
assert not core.geometry.is_empty.any()
assert (core["core_area_ha"] >= 0.5).all()
out = BASE / "data/processed/pilot_polygons_core20m.gpkg"
core.to_file(out, layer="core20m", driver="GPKG")
core.drop(columns="geometry").to_csv(BASE / "data/processed/pilot_polygons_core20m.csv", index=False)
print(core.groupby("class4")["core_area_ha"].agg(["count","min","median","max"]).to_string())
print(out)
