from pathlib import Path
import numpy as np
import pandas as pd

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
p=BASE/"data/processed/ml/seasonal_coherence_class_tests.csv"
d=pd.read_csv(p)
m=len(d)

d["p_bonferroni"]=np.minimum(d["kruskal_p"]*m,1.0)

order=np.argsort(d["kruskal_p"].to_numpy())
ps=d["kruskal_p"].to_numpy()[order]
adj=np.empty(m,float)
running=1.0
for i in range(m-1,-1,-1):
    rank=i+1
    running=min(running, ps[i]*m/rank)
    adj[i]=min(running,1.0)
back=np.empty(m,float)
back[order]=adj
d["p_fdr_bh"]=back
d["fdr_reject_0_05"]=d["p_fdr_bh"]<=0.05

d.to_csv(p,index=False)
print(d[["mid_date","kruskal_p","p_bonferroni","p_fdr_bh","fdr_reject_0_05"]].to_string(index=False))
