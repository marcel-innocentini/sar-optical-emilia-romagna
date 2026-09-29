from pathlib import Path
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.pipeline import Pipeline

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
OUT=BASE/"data/processed/ml"

X=pd.read_csv(OUT/"analysis_feature_matrix_aligned_fusion.csv")
coh=pd.read_csv(BASE/"data/processed/coherence_polygon_features.csv")

coh1=coh.groupby(["pilot_id","class4","zone"],as_index=False).agg(
    COH_median=("coherence_median","median"),
    COH_mean=("coherence_mean","mean"),
    COH_std=("coherence_std","mean"),
    COH_p10=("coherence_p10","median"),
    COH_p90=("coherence_p90","median"),
)
X=X.merge(coh1,on=["pilot_id","class4","zone"],how="inner")

opt=sorted(c for c in X.columns if c.startswith("OPT_"))
sar=sorted(c for c in X.columns if c.startswith("SARALIGN_"))
cohcols=sorted(c for c in X.columns if c.startswith("COH_"))

specs={
    "OPTICAL_ONLY":opt,
    "SAR_ALIGNED_ONLY":sar,
    "SAR_ALIGNED_PLUS_COH":sorted(sar+cohcols),
    "FUSION_ALIGNED":sorted(opt+sar),
    "FUSION_ALIGNED_PLUS_COH":sorted(opt+sar+cohcols),
}
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
        yt.extend(X.loc[te,"class4"].tolist())
        yp.extend(p.tolist())
    return {
        "seed":seed,"modality":name,
        "balanced_accuracy":balanced_accuracy_score(yt,yp),
        "macro_f1":f1_score(yt,yp,average="macro",zero_division=0),
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
    ba_min=("balanced_accuracy","min"),
    ba_max=("balanced_accuracy","max"),
    f1_mean=("macro_f1","mean"),
    f1_sd=("macro_f1","std"),
).reset_index()

w=d.pivot(index="seed",columns="modality",values="balanced_accuracy")
w["coh_gain_over_fusion"]=w["FUSION_ALIGNED_PLUS_COH"]-w["FUSION_ALIGNED"]
w["coh_gain_over_sar"]=w["SAR_ALIGNED_PLUS_COH"]-w["SAR_ALIGNED_ONLY"]

delta=pd.DataFrame([{
    "coh_gain_over_fusion_mean":w["coh_gain_over_fusion"].mean(),
    "coh_gain_over_fusion_sd":w["coh_gain_over_fusion"].std(),
    "coh_improves_fusion_seeds":int((w["coh_gain_over_fusion"]>0).sum()),
    "coh_equal_fusion_seeds":int((w["coh_gain_over_fusion"]==0).sum()),
    "coh_worsens_fusion_seeds":int((w["coh_gain_over_fusion"]<0).sum()),
    "coh_gain_over_sar_mean":w["coh_gain_over_sar"].mean(),
}])

d.to_csv(OUT/"coherence_repeated_seed_metrics.csv",index=False)
summary.to_csv(OUT/"coherence_repeated_seed_summary.csv",index=False)
w.reset_index().to_csv(OUT/"coherence_repeated_seed_deltas.csv",index=False)
delta.to_csv(OUT/"coherence_delta_summary.csv",index=False)

print("\nCoherence comparison:")
print(summary.to_string(index=False))
print("\nIncremental coherence effect:")
print(delta.to_string(index=False))
