from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.pipeline import Pipeline

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
OUT=BASE/"data/processed/ml"
opt=pd.read_csv(BASE/"data/processed/s2_polygon_timeseries.csv")
sar=pd.read_csv(BASE/"data/processed/s1_rtc_polygon_timeseries.csv")

o=opt.pivot_table(index=["pilot_id","class4","zone"],
                  columns=["date","metric"],values="median",aggfunc="first")
o.columns=[f"OPT_{m}_{d}" for d,m in o.columns]
o=o.reset_index()

vars_=["vv_gamma0_db","vh_gamma0_db","vh_vv_ratio_db"]
s=sar.pivot_table(index=["pilot_id","class4","zone"],
                  columns="date",values=vars_,aggfunc="first")
s.columns=[f"SAR_{v}_{d}" for v,d in s.columns]
s=s.reset_index()

base=o.merge(s,on=["pilot_id","class4","zone"],how="inner")
opt_cols=sorted(c for c in base.columns if c.startswith("OPT_"))
sar_cols=sorted(c for c in base.columns if c.startswith("SAR_"))
specs={"OPTICAL_ONLY":opt_cols,"SAR_ONLY":sar_cols,
       "FUSION":sorted(opt_cols+sar_cols)}
def run_seed(seed,name,cols):
    truth=[]; pred=[]
    fold_rows=[]
    for zone in sorted(base["zone"].unique()):
        tr=base["zone"]!=zone; te=~tr
        pipe=Pipeline([
            ("impute",SimpleImputer(strategy="median",add_indicator=True)),
            ("rf",RandomForestClassifier(
                n_estimators=300,max_features="sqrt",min_samples_leaf=2,
                class_weight="balanced",random_state=seed,n_jobs=-1))
        ])
        pipe.fit(base.loc[tr,cols],base.loc[tr,"class4"])
        p=pipe.predict(base.loc[te,cols])
        y=base.loc[te,"class4"].tolist()
        truth.extend(y); pred.extend(p.tolist())
        fold_rows.append({
            "seed":seed,"modality":name,"test_zone":zone,
            "balanced_accuracy":balanced_accuracy_score(y,p),
            "macro_f1":f1_score(y,p,average="macro",zero_division=0)
        })
    return {
        "seed":seed,"modality":name,
        "balanced_accuracy":balanced_accuracy_score(truth,pred),
        "macro_f1":f1_score(truth,pred,average="macro",zero_division=0)
    },fold_rows

rows=[]; folds=[]
for seed in range(20):
    for name,cols in specs.items():
        a,b=run_seed(seed,name,cols)
        rows.append(a); folds.extend(b)
    print("seed",seed,flush=True)
d=pd.DataFrame(rows)
f=pd.DataFrame(folds)
summary=d.groupby("modality").agg(
    ba_mean=("balanced_accuracy","mean"),
    ba_sd=("balanced_accuracy","std"),
    ba_median=("balanced_accuracy","median"),
    ba_min=("balanced_accuracy","min"),
    ba_max=("balanced_accuracy","max"),
    f1_mean=("macro_f1","mean"),
    f1_sd=("macro_f1","std"),
    f1_median=("macro_f1","median"),
).reset_index()

wide=d.pivot(index="seed",columns="modality",values="balanced_accuracy")
wide["fusion_minus_optical"]=wide["FUSION"]-wide["OPTICAL_ONLY"]
wide["fusion_minus_sar"]=wide["FUSION"]-wide["SAR_ONLY"]

delta=pd.DataFrame([{
    "n_seeds":len(wide),
    "fusion_minus_optical_mean":wide["fusion_minus_optical"].mean(),
    "fusion_minus_optical_sd":wide["fusion_minus_optical"].std(),
    "fusion_minus_optical_median":wide["fusion_minus_optical"].median(),
    "fusion_gt_optical_seeds":int((wide["fusion_minus_optical"]>0).sum()),
    "fusion_eq_optical_seeds":int((wide["fusion_minus_optical"]==0).sum()),
    "fusion_lt_optical_seeds":int((wide["fusion_minus_optical"]<0).sum()),
    "fusion_minus_sar_mean":wide["fusion_minus_sar"].mean(),
}])
d.to_csv(OUT/"repeated_seed_metrics.csv",index=False)
f.to_csv(OUT/"repeated_seed_by_zone.csv",index=False)
summary.to_csv(OUT/"repeated_seed_summary.csv",index=False)
wide.reset_index().to_csv(OUT/"repeated_seed_paired_deltas.csv",index=False)
delta.to_csv(OUT/"repeated_seed_delta_summary.csv",index=False)

print("\nRepeated-seed summary:")
print(summary.to_string(index=False))
print("\nPaired algorithmic stability (not an inferential test):")
print(delta.to_string(index=False))
