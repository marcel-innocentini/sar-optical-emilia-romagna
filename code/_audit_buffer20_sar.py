from pathlib import Path
import numpy as np, pandas as pd, geopandas as gpd, rasterio
from rasterio.mask import mask
BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
g=gpd.read_file(BASE/"data/processed/pilot_polygons.gpkg",layer="pilots")
g.geometry=g.geometry.buffer(-20)
rows=[]
for folder in sorted((BASE/"data/processed/sentinel1/rtc").glob("*")):
    if not folder.is_dir(): continue
    vv=sorted(folder.glob("*_VV_gamma0_rtc.tif")); vh=sorted(folder.glob("*_VH_gamma0_rtc.tif"))
    if len(vv)!=1 or len(vh)!=1: continue
    date=pd.to_datetime(folder.name[17:25],format="%Y%m%d").date().isoformat()
    with rasterio.open(vv[0]) as a, rasterio.open(vh[0]) as b:
        pg=g.to_crs(a.crs)
        for _,r in pg.iterrows():
            x,_=mask(a,[r.geometry],crop=True,filled=False)
            y,_=mask(b,[r.geometry],crop=True,filled=False)
            x=x[0].filled(np.nan).astype(float); y=y[0].filled(np.nan).astype(float)
            ok=np.isfinite(x)&np.isfinite(y)&(x>0)&(y>0); x=x[ok]; y=y[ok]
            xm,ym=x.mean(),y.mean()
            rows.append((date,r.pilot_id,10*np.log10(xm),10*np.log10(ym),10*np.log10(ym/xm)))
q=pd.DataFrame(rows,columns=["date","pilot_id","vv2","vh2","r2"])
p=pd.read_csv(BASE/"data/processed/s1_rtc_polygon_timeseries.csv")
m=p.merge(q,on=["date","pilot_id"],how="outer",indicator=True)
for a,b in [("vv_gamma0_db","vv2"),("vh_gamma0_db","vh2"),("vh_vv_ratio_db","r2")]:
    m[a+"_diff"]=m[a]-m[b]
print(m._merge.value_counts().to_string())
print(m[["vv_gamma0_db_diff","vh_gamma0_db_diff","vh_vv_ratio_db_diff"]].abs().max().to_string())
print(m.sort_values("vv_gamma0_db_diff",key=lambda s:s.abs(),ascending=False).head().to_string(index=False))
