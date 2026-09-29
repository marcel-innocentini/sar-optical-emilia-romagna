from pathlib import Path
import re, zipfile
import pandas as pd

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
roots=[
    BASE/"data/processed/sentinel1/coherence",
    BASE/"data/processed/sentinel1/coherence_seasonal",
]
rows=[]
for root in roots:
    if not root.exists(): continue
    for z in sorted(root.glob("*.zip")):
        with zipfile.ZipFile(z) as zz:
            txts=[n for n in zz.namelist() if n.endswith(".txt") and not n.endswith("README.md.txt")]
            if len(txts)!=1:
                raise RuntimeError(f"{z.name}: expected one parameter txt, found {len(txts)}")
            t=zz.read(txts[0]).decode("utf-8","replace")
        def val(label):
            m=re.search(rf"^{re.escape(label)}:\s*(.+)$",t,re.M)
            return m.group(1).strip() if m else None
        ref=val("Reference Granule")
        sec=val("Secondary Granule")
        mref=re.search(r"_(20\d{6})T",ref or "")
        msec=re.search(r"_(20\d{6})T",sec or "")
        rows.append({
            "product_zip":z.name,
            "master_date":mref.group(1) if mref else None,
            "slave_date":msec.group(1) if msec else None,
            "baseline_m":float(val("Baseline")) if val("Baseline") else None,
            "range_looks":int(val("Range looks")) if val("Range looks") else None,
            "azimuth_looks":int(val("Azimuth looks")) if val("Azimuth looks") else None,
            "output_resolution_m":float(val("Resolution of output (m)")) if val("Resolution of output (m)") else None,
            "dem_source":val("DEM source"),
            "dem_resolution_m":float(val("DEM resolution (m)")) if val("DEM resolution (m)") else None,
            "reference_direction":val("Reference Pass Direction"),
            "reference_orbit":val("Reference Orbit Number"),
            "secondary_orbit":val("Secondary Orbit Number"),
        })
d=pd.DataFrame(rows).drop_duplicates(["master_date","slave_date"]).sort_values("master_date")
out=BASE/"metadata/seasonal_coherence_product_metadata.csv"
d.to_csv(out,index=False)
print(d.to_string(index=False))
print("\nBaseline range:",d["baseline_m"].min(),d["baseline_m"].max())
print("All 40 m:",bool((d["output_resolution_m"]==40).all()))
print("All 10x2:",bool(((d["range_looks"]==10)&(d["azimuth_looks"]==2)).all()))
print(out)
