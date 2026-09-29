from pathlib import Path
import zipfile, shutil, re
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
ROOTS=[
    BASE/"data/processed/sentinel1/coherence",
    BASE/"data/processed/sentinel1/coherence_seasonal",
]
PILOTS=gpd.read_file(BASE/"data/processed/pilot_polygons_core20m.gpkg",layer="core20m")
OUT=BASE/"data/processed/seasonal_coherence_polygon_timeseries.csv"

# Extract only *_corr.tif from each HyP3 zip, avoiding Windows long-path issues.
corr_files=[]
for root in ROOTS:
    if not root.exists():
        continue
    for z in root.glob("*.zip"):
        short=root/f"{z.stem}_corr.tif"
        if not short.exists():
            with zipfile.ZipFile(z) as src:
                members=[n for n in src.namelist() if n.endswith("_corr.tif")]
                if len(members)!=1:
                    raise RuntimeError(f"Expected one coherence raster in {z.name}; found {len(members)}")
                with src.open(members[0]) as inp, open(short,"wb") as out:
                    shutil.copyfileobj(inp,out)
        corr_files.append(short)

# Also include any already-extracted short coherence raster.
for root in ROOTS:
    if root.exists():
        corr_files.extend(root.glob("*_corr.tif"))
corr_files=sorted(set(corr_files))
if not corr_files:
    raise FileNotFoundError("No coherence rasters found")
rows=[]
for corr in corr_files:
    m=re.search(r"(20\d{6}).*?(20\d{6})",corr.stem)
    if not m:
        # HyP3 compact name uses timestamps such as 20230603T...
        dates=re.findall(r"20\d{6}",corr.stem)
        if len(dates)<2:
            raise RuntimeError(f"Could not parse pair dates from {corr.name}")
        d1,d2=dates[0],dates[1]
    else:
        d1,d2=m.group(1),m.group(2)
    master=pd.to_datetime(d1,format="%Y%m%d")
    slave=pd.to_datetime(d2,format="%Y%m%d")
    mid=master+(slave-master)/2

    with rasterio.open(corr) as src:
        pg=PILOTS.to_crs(src.crs)
        for _,r in pg.iterrows():
            a,_=mask(src,[r.geometry],crop=True,filled=False)
            v=a[0].compressed().astype(float)
            v=v[np.isfinite(v)&(v>0)&(v<=1)]
            rows.append({
                "pair_id":f"{d1}_{d2}",
                "master_date":master.date().isoformat(),
                "slave_date":slave.date().isoformat(),
                "mid_date":mid.date().isoformat(),
                "pilot_id":r["pilot_id"],
                "class4":r["class4"],
                "zone":r["zone"],
                "core_area_ha":float(r["core_area_ha"]),
                "n_valid":len(v),
                "coherence_mean":float(v.mean()) if len(v) else np.nan,
                "coherence_median":float(np.median(v)) if len(v) else np.nan,
                "coherence_std":float(v.std()) if len(v) else np.nan,
                "coherence_p10":float(np.percentile(v,10)) if len(v) else np.nan,
                "coherence_p90":float(np.percentile(v,90)) if len(v) else np.nan,
            })
df=pd.DataFrame(rows)
df=df.sort_values(["pair_id","pilot_id"]).drop_duplicates(["pair_id","pilot_id"],keep="first")
df.to_csv(OUT,index=False)
print("Pairs:",df["pair_id"].nunique())
print("Rows:",len(df))
print("\nPair dates:")
print(df[["pair_id","master_date","slave_date","mid_date"]].drop_duplicates().sort_values("mid_date").to_string(index=False))
print("\nMedian coherence by class and pair:")
print(df.groupby(["mid_date","class4"])["coherence_median"].median().round(3).to_string())
print(OUT)
