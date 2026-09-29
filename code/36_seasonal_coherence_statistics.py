from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import kruskal

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
d=pd.read_csv(BASE/"data/processed/seasonal_coherence_polygon_timeseries.csv")
OUT=BASE/"data/processed/ml"

rows=[]
for mid, g in d.groupby("mid_date"):
    groups=[x["coherence_median"].dropna().values for _,x in g.groupby("class4")]
    H,p=kruskal(*groups)
    med=g.groupby("class4")["coherence_median"].median().to_dict()
    rows.append({
        "mid_date":mid,
        "kruskal_H":H,
        "kruskal_p":p,
        "annual_median":med.get("ANNUAL"),
        "olive_median":med.get("OLIVE"),
        "orchard_median":med.get("ORCHARD"),
        "vineyard_median":med.get("VINEYARD"),
        "range_of_class_medians":max(med.values())-min(med.values()),
    })
res=pd.DataFrame(rows).sort_values("mid_date")
res.to_csv(OUT/"seasonal_coherence_class_tests.csv",index=False)

# Simple pairwise class median contrasts, descriptive only.
classes=sorted(d["class4"].unique())
contr=[]
for mid,g in d.groupby("mid_date"):
    meds=g.groupby("class4")["coherence_median"].median()
    for i,a in enumerate(classes):
        for b in classes[i+1:]:
            contr.append({
                "mid_date":mid,"class_a":a,"class_b":b,
                "median_a":meds[a],"median_b":meds[b],
                "difference_a_minus_b":meds[a]-meds[b],
            })
pd.DataFrame(contr).to_csv(OUT/"seasonal_coherence_pairwise_median_contrasts.csv",index=False)

print(res.to_string(index=False))
