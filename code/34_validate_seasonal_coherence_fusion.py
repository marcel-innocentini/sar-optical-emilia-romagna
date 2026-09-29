from pathlib import Path
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.pipeline import Pipeline

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
ML=BASE/"data/processed/ml"

X=pd.read_csv(ML/"analysis_feature_matrix_aligned_fusion.csv")
coh=pd.read_csv(BASE/"data/processed/seasonal_coherence_polygon_timeseries.csv")

cw=coh.pivot_table(
    index=["pilot_id","class4","zone"],
    columns="mid_date",
    values="coherence_median",
    aggfunc="first"
)
cw.columns=[f"COH_{d}" for d in cw.columns]
cw=cw.reset_index()

X=X.merge(cw,on=["pilot_id","class4","zone"],how="inner")
X.to_csv(ML/"analysis_feature_matrix_aligned_plus_seasonal_coherence.csv",index=False)

opt=sorted(c for c in X.columns if c.startswith("OPT_"))
sar=sorted(c for c in X.columns if c.startswith("SARALIGN_"))
cohcols=sorted(c for c in X.columns if c.startswith("COH_"))

specs={
    "OPTICAL_ONLY":opt,
    "SAR_ALIGNED_ONLY":sar,
    "COHERENCE_SEASONAL_ONLY":cohcols,
    "OPTICAL_PLUS_COH":sorted(opt+cohcols),
    "SAR_PLUS_COH":sorted(sar+cohcols),
    "FUSION_ALIGNED":sorted(opt+sar),
    "FUSION_PLUS_SEASONAL_COH":sorted(opt+sar+cohcols),
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
        yt.extend(X.loc[te,"class4"].tolist())
        yp.extend(p.tolist())
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
    ba_min=("balanced_accuracy","min"),
    ba_max=("balanced_accuracy","max"),
    f1_mean=("macro_f1","mean"),
    f1_sd=("macro_f1","std")
).reset_index()

w=d.pivot(index="seed",columns="modality",values="balanced_accuracy")
w["seasonal_coh_gain_over_fusion"]=w["FUSION_PLUS_SEASONAL_COH"]-w["FUSION_ALIGNED"]
w["seasonal_coh_gain_over_optical"]=w["OPTICAL_PLUS_COH"]-w["OPTICAL_ONLY"]
w["seasonal_coh_gain_over_sar"]=w["SAR_PLUS_COH"]-w["SAR_ALIGNED_ONLY"]

delta=pd.DataFrame([{
    "fusion_plus_coh_minus_fusion_mean":w["seasonal_coh_gain_over_fusion"].mean(),
    "fusion_plus_coh_minus_fusion_sd":w["seasonal_coh_gain_over_fusion"].std(),
    "coh_improves_fusion_seeds":int((w["seasonal_coh_gain_over_fusion"]>0).sum()),
    "coh_equal_fusion_seeds":int((w["seasonal_coh_gain_over_fusion"]==0).sum()),
    "coh_worsens_fusion_seeds":int((w["seasonal_coh_gain_over_fusion"]<0).sum()),
    "optical_plus_coh_minus_optical_mean":w["seasonal_coh_gain_over_optical"].mean(),
    "sar_plus_coh_minus_sar_mean":w["seasonal_coh_gain_over_sar"].mean(),
}])

d.to_csv(ML/"seasonal_coherence_seed_metrics.csv",index=False)
summary.to_csv(ML/"seasonal_coherence_summary.csv",index=False)
w.reset_index().to_csv(ML/"seasonal_coherence_paired_deltas.csv",index=False)
delta.to_csv(ML/"seasonal_coherence_delta_summary.csv",index=False)

print("\nSeasonal coherence comparison:")
print(summary.to_string(index=False))
print("\nIncremental effect:")
print(delta.to_string(index=False))
