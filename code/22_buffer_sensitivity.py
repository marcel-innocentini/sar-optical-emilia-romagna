from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.pipeline import Pipeline

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
PILOTS = gpd.read_file(BASE / "data/processed/pilot_polygons.gpkg", layer="pilots")
S2ROOT = BASE / "data/processed/sentinel2"
S1ROOT = BASE / "data/processed/sentinel1/rtc"
OUT = BASE / "data/processed/ml"

def core_polys(buffer_m):
    g = PILOTS.copy()
    g.geometry = g.geometry.buffer(-float(buffer_m))
    g["core_area_ha"] = g.geometry.area / 10000.0
    g = g[~g.geometry.is_empty & (g["core_area_ha"] >= 0.25)].copy()
    return g

def s2_table(core):
    rows = []
    for day in sorted(p for p in S2ROOT.glob("20*") if p.is_dir()):
        for metric in ["ndvi","ndre","ndmi","gndvi"]:
            fp = day / f"{day.name}_{metric}.tif"
            with rasterio.open(fp) as src:
                pg = core.to_crs(src.crs)
                for _, r in pg.iterrows():
                    a,_ = mask(src,[r.geometry],crop=True,filled=False)
                    v = a[0].compressed().astype("float64")
                    v = v[np.isfinite(v) & (v != src.nodata)]
                    rows.append({
                        "pilot_id":r["pilot_id"],"class4":r["class4"],"zone":r["zone"],
                        "date":pd.to_datetime(day.name,format="%Y%m%d").date().isoformat(),
                        "metric":metric,"value":float(np.median(v)) if len(v) else np.nan,
                    })
    return pd.DataFrame(rows)

def s1_table(core):
    rows = []
    for folder in sorted(p for p in S1ROOT.glob("*") if p.is_dir()):
        vv = sorted(folder.glob("*_VV_gamma0_rtc.tif"))
        vh = sorted(folder.glob("*_VH_gamma0_rtc.tif"))
        if len(vv)!=1 or len(vh)!=1:
            continue
        date = pd.to_datetime(folder.name[17:25],format="%Y%m%d").date().isoformat()
        with rasterio.open(vv[0]) as svv, rasterio.open(vh[0]) as svh:
            pg = core.to_crs(svv.crs)
            for _, r in pg.iterrows():
                avv,_ = mask(svv,[r.geometry],crop=True,filled=False)
                avh,_ = mask(svh,[r.geometry],crop=True,filled=False)
                x = avv[0].filled(np.nan).astype("float64")
                y = avh[0].filled(np.nan).astype("float64")
                good = np.isfinite(x)&np.isfinite(y)&(x>0)&(y>0)
                x,y = x[good],y[good]
                if not len(x):
                    continue
                xm,ym = float(x.mean()),float(y.mean())
                for metric,val in [
                    ("vv_db",10*np.log10(xm)),
                    ("vh_db",10*np.log10(ym)),
                    ("ratio_db",10*np.log10(ym/xm)),
                ]:
                    rows.append({
                        "pilot_id":r["pilot_id"],"class4":r["class4"],"zone":r["zone"],
                        "date":date,"metric":metric,"value":val,
                    })
    return pd.DataFrame(rows)

def evaluate(base, name, cols):
    pipe = Pipeline([
        ("impute",SimpleImputer(strategy="median",add_indicator=True)),
        ("rf",RandomForestClassifier(
            n_estimators=600,max_features="sqrt",min_samples_leaf=2,
            class_weight="balanced",random_state=42,n_jobs=-1))
    ])
    yt,yp = [],[]
    for zone in sorted(base["zone"].unique()):
        tr = base["zone"] != zone
        te = ~tr
        pipe.fit(base.loc[tr,cols],base.loc[tr,"class4"])
        p = pipe.predict(base.loc[te,cols])
        yt.extend(base.loc[te,"class4"]); yp.extend(p)
    return {
        "modality":name,
        "balanced_accuracy":balanced_accuracy_score(yt,yp),
        "macro_f1":f1_score(yt,yp,average="macro",zero_division=0),
    }

results = []
for buffer_m in [10,20,30]:
    core = core_polys(buffer_m)
    s2 = s2_table(core)
    s1 = s1_table(core)

    o = s2.pivot_table(
        index=["pilot_id","class4","zone"],columns=["date","metric"],
        values="value",aggfunc="first")
    o.columns = [f"O_{m}_{d}" for d,m in o.columns]
    o = o.reset_index()

    s = s1.pivot_table(
        index=["pilot_id","class4","zone"],columns=["date","metric"],
        values="value",aggfunc="first")
    s.columns = [f"S_{m}_{d}" for d,m in s.columns]
    s = s.reset_index()

    base = o.merge(s,on=["pilot_id","class4","zone"],how="inner")
    oc = [c for c in base.columns if c.startswith("O_")]
    sc = [c for c in base.columns if c.startswith("S_")]
    for name,cols in [
        ("OPTICAL_ONLY",oc),("SAR_ONLY",sc),("FUSION",oc+sc)
    ]:
        r = evaluate(base,name,cols)
        r.update({"buffer_m":buffer_m,"n_polygons":len(base),
                  "min_core_ha":float(core["core_area_ha"].min())})
        results.append(r)
    print("buffer",buffer_m,"n",len(base),flush=True)

out = pd.DataFrame(results)
out.to_csv(OUT / "buffer_sensitivity.csv",index=False)
print(out.to_string(index=False))
