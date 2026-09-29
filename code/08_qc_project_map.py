from pathlib import Path
import geopandas as gpd
import matplotlib.pyplot as plt

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
aoi = gpd.read_file(BASE / "data/processed/aoi_corridor.gpkg", layer="aoi")
cities = gpd.read_file(BASE / "data/processed/aoi_corridor.gpkg", layer="city_centres")
pilots = gpd.read_file(BASE / "data/processed/pilot_polygons.gpkg", layer="pilots")

fig, ax = plt.subplots(figsize=(10, 8))
aoi.boundary.plot(ax=ax, linewidth=1.4)
for cls in ["VINEYARD", "ORCHARD", "OLIVE", "ANNUAL"]:
    g = pilots[pilots["class4"] == cls]
    g.plot(ax=ax, alpha=0.55, label=cls)
cities.plot(ax=ax, marker="x", markersize=60)
for _, row in cities.iterrows():
    ax.annotate(row["city"], (row.geometry.x, row.geometry.y),
                xytext=(5, 5), textcoords="offset points", fontsize=9)
ax.set_title("SAR–Optical Italy | AOI and pilot polygons")
ax.set_xlabel("Easting (m) — EPSG:25832")
ax.set_ylabel("Northing (m)")
ax.legend(loc="best")
ax.set_aspect("equal")
fig.tight_layout()
out = BASE / "outputs/maps/00_AOI_pilot_polygons_QC.png"
fig.savefig(out, dpi=220)
plt.close(fig)
print(out)
