from pathlib import Path
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.pipeline import Pipeline

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
OUT=BASE/"data/processed/ml"
X=pd.read_csv(OUT/"analysis_feature_matrix_optical_sar_full2023.csv")

opt=sorted(c for c in X.columns if c.startswith("OPT_"))
sar=sorted(c for c in X.columns if c.startswith("SARFULL_"))
specs={"OPTICAL_ONLY":opt,
       "SAR_FULLYEAR":sar,
       "FUSION_FULLYEAR":sorted(opt+sar)}

def run(seed,name,cols):
    yt=[]; yp=[]
    for zone in sorted(X["zone"].unique()):
        tr=X["zone"]!=zone; te=~tr
        pipe=Pipeline([
            ("impute",SimpleImputer(strategy="median",add_indicator=True)),
            ("rf",RandomForestClassifier(
                n_estimators=300,max_features="sqrt",min_samples_leaf=2,
                class_weight="balanced",random_state=seed,n_jobs=-1))
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
s=d.groupby("modality").agg(
    ba_mean=("balanced_accuracy","mean"),
    ba_sd=("balanced_accuracy","std"),
    ba_median=("balanced_accuracy","median"),
    ba_min=("balanced_accuracy","min"),
    ba_max=("balanced_accuracy","max"),
    f1_mean=("macro_f1","mean"),
    f1_sd=("macro_f1","std")
).reset_index()

w=d.pivot(index="seed",columns="modality",values="balanced_accuracy")
w["fusion_minus_optical"]=w["FUSION_FULLYEAR"]-w["OPTICAL_ONLY"]
w["fusion_minus_sar"]=w["FUSION_FULLYEAR"]-w["SAR_FULLYEAR"]
delta=pd.DataFrame([{
    "fusion_minus_optical_mean":w["fusion_minus_optical"].mean(),
    "fusion_minus_optical_sd":w["fusion_minus_optical"].std(),
    "fusion_gt_optical_seeds":int((w["fusion_minus_optical"]>0).sum()),
    "fusion_eq_optical_seeds":int((w["fusion_minus_optical"]==0).sum()),
    "fusion_lt_optical_seeds":int((w["fusion_minus_optical"]<0).sum()),
    "sar_fullyear_mean_ba":w["SAR_FULLYEAR"].mean(),
}])

d.to_csv(OUT/"repeated_full_year_seed_metrics.csv",index=False)
s.to_csv(OUT/"repeated_full_year_seed_summary.csv",index=False)
w.reset_index().to_csv(OUT/"repeated_full_year_paired_deltas.csv",index=False)
delta.to_csv(OUT/"repeated_full_year_delta_summary.csv",index=False)

print("\nFull-year repeated-seed summary:")
print(s.to_string(index=False))
print("\nPaired stability:")
print(delta.to_string(index=False))
