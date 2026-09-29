from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from scipy.stats import kruskal, spearmanr

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
COH=BASE/"data/processed/sentinel1/coherence/coherence_20230603_20230615_corr.tif"
P= gpd.read_file(BASE/"data/processed/pilot_polygons.gpkg",layer="pilots")
OUT=BASE/"data/processed/ml"

rows=[]
with rasterio.open(COH) as src:
    for buffer_m in [0,10,20,30]:
        g=P.copy()
        if buffer_m:
            g.geometry=g.geometry.buffer(-buffer_m)
        g["core_area_ha"]=g.geometry.area/10000.0
        g=g[~g.geometry.is_empty].copy()
        pg=g.to_crs(src.crs)
        for _,r in pg.iterrows():
            a,_=mask(src,[r.geometry],crop=True,filled=False)
            v=a[0].compressed().astype(float)
            v=v[np.isfinite(v)&(v>0)&(v<=1)]
            rows.append({
                "buffer_m":buffer_m,"pilot_id":r["pilot_id"],
                "class4":r["class4"],"zone":r["zone"],
                "area_ha":float(r["area_ha_geom"]),
                "support_area_ha":float(r["core_area_ha"]),
                "n_valid":len(v),
                "coh_mean":float(v.mean()) if len(v) else np.nan,
                "coh_median":float(np.median(v)) if len(v) else np.nan,
                "coh_std":float(v.std()) if len(v) else np.nan,
            })
d=pd.DataFrame(rows)
d.to_csv(OUT/"coherence_buffer_sensitivity_values.csv",index=False)

tests=[]
for b,db in d.groupby("buffer_m"):
    groups=[x["coh_median"].dropna().values for _,x in db.groupby("class4")]
    H,p=kruskal(*groups)
    rho_area,p_area=spearmanr(db["area_ha"],db["coh_median"],nan_policy="omit")
    tests.append({
        "buffer_m":b,"n_polygons":db["pilot_id"].nunique(),
        "n_valid_min":db["n_valid"].min(),
        "n_valid_median":db["n_valid"].median(),
        "kruskal_H_class":H,"kruskal_p_class":p,
        "spearman_area_coh":rho_area,"spearman_area_p":p_area,
    })
t=pd.DataFrame(tests)
t.to_csv(OUT/"coherence_buffer_sensitivity_tests.csv",index=False)

summary=d.groupby(["buffer_m","class4"]).agg(
    n=("pilot_id","size"),
    coh_median=("coh_median","median"),
    coh_mean=("coh_median","mean"),
    coh_sd=("coh_median","std"),
    pixels_median=("n_valid","median"),
).reset_index()
summary.to_csv(OUT/"coherence_buffer_sensitivity_summary.csv",index=False)

print("Class summaries:")
print(summary.to_string(index=False))
print("\nTests:")
print(t.to_string(index=False))
