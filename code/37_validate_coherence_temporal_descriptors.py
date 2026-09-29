from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.pipeline import Pipeline

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
ML=BASE/"data/processed/ml"
coh=pd.read_csv(BASE/"data/processed/seasonal_coherence_polygon_timeseries.csv")
coh["mid_date"]=pd.to_datetime(coh["mid_date"])

w=coh.pivot_table(index=["pilot_id","class4","zone"],
                  columns="mid_date",values="coherence_median",aggfunc="first")
cols=sorted(w.columns)
arr=w[cols]

desc=pd.DataFrame(index=w.index)
desc["COHD_mean"]=arr.mean(axis=1)
desc["COHD_std"]=arr.std(axis=1)
desc["COHD_min"]=arr.min(axis=1)
desc["COHD_max"]=arr.max(axis=1)
desc["COHD_amp"]=desc["COHD_max"]-desc["COHD_min"]

# winter = Feb + Dec; summer = Jun + Aug
winter=[c for c in cols if c.month in (2,12)]
summer=[c for c in cols if c.month in (6,8)]
desc["COHD_winter_minus_summer"]=arr[winter].mean(axis=1)-arr[summer].mean(axis=1)
desc=desc.reset_index()

X=pd.read_csv(ML/"analysis_feature_matrix_aligned_fusion.csv")
X=X.merge(desc,on=["pilot_id","class4","zone"],how="inner")
X.to_csv(ML/"analysis_feature_matrix_coherence_descriptors.csv",index=False)

opt=sorted(c for c in X.columns if c.startswith("OPT_"))
sar=sorted(c for c in X.columns if c.startswith("SARALIGN_"))
cd=sorted(c for c in X.columns if c.startswith("COHD_"))
specs={
    "COH_DESCRIPTORS_ONLY":cd,
    "OPTICAL_ONLY":opt,
    "SAR_ALIGNED_ONLY":sar,
    "FUSION_ALIGNED":sorted(opt+sar),
    "FUSION_PLUS_COH_DESC":sorted(opt+sar+cd),
}
def run(seed,name,cols):
    yt=[]; yp=[]
    for zone in sorted(X["zone"].unique()):
        tr=X["zone"]!=zone; te=~tr
        pipe=Pipeline([
            ("impute",SimpleImputer(strategy="median",add_indicator=True)),
            ("rf",RandomForestClassifier(
                n_estimators=300,max_features="sqrt",min_samples_leaf=2,
                class_weight="balanced",random_state=seed,n_jobs=-1
            ))
        ])
        pipe.fit(X.loc[tr,cols],X.loc[tr,"class4"])
        p=pipe.predict(X.loc[te,cols])
        yt.extend(X.loc[te,"class4"].tolist()); yp.extend(p.tolist())
    return {
        "seed":seed,"modality":name,
        "balanced_accuracy":balanced_accuracy_score(yt,yp),
        "macro_f1":f1_score(yt,yp,average="macro",zero_division=0)
    }

rows=[]
for seed in range(20):
    for name,cols in specs.items():
        rows.append(run(seed,name,cols))
    print("seed",seed,flush=True)
d=pd.DataFrame(rows)
summary=d.groupby("modality").agg(
    ba_mean=("balanced_accuracy","mean"),
    ba_sd=("balanced_accuracy","std"),
    ba_median=("balanced_accuracy","median"),
    f1_mean=("macro_f1","mean"),
    f1_sd=("macro_f1","std")
).reset_index()

w2=d.pivot(index="seed",columns="modality",values="balanced_accuracy")
w2["gain_desc_over_fusion"]=w2["FUSION_PLUS_COH_DESC"]-w2["FUSION_ALIGNED"]
delta=pd.DataFrame([{
    "gain_mean":w2["gain_desc_over_fusion"].mean(),
    "gain_sd":w2["gain_desc_over_fusion"].std(),
    "improves":int((w2["gain_desc_over_fusion"]>0).sum()),
    "ties":int((w2["gain_desc_over_fusion"]==0).sum()),
    "worsens":int((w2["gain_desc_over_fusion"]<0).sum()),
}])

d.to_csv(ML/"coherence_descriptor_seed_metrics.csv",index=False)
summary.to_csv(ML/"coherence_descriptor_summary.csv",index=False)
w2.reset_index().to_csv(ML/"coherence_descriptor_paired_deltas.csv",index=False)
delta.to_csv(ML/"coherence_descriptor_delta_summary.csv",index=False)

print("\nTemporal-descriptor comparison:")
print(summary.to_string(index=False))
print("\nIncremental descriptor effect:")
print(delta.to_string(index=False))
