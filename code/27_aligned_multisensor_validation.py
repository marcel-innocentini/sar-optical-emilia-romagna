from pathlib import Path
import json
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.pipeline import Pipeline

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
OUT=BASE/"data/processed/ml"
opt=pd.read_csv(BASE/"data/processed/s2_polygon_timeseries.csv")
sar=pd.read_csv(BASE/"data/processed/s1_rtc_polygon_timeseries_full2023.csv")
opt["date"]=pd.to_datetime(opt["date"])
sar["date"]=pd.to_datetime(sar["date"])

opt_dates=sorted(opt["date"].unique())
sar_dates=pd.DatetimeIndex(sorted(sar["date"].unique()))
pairs=[]
for od in opt_dates:
    i=(sar_dates-pd.Timestamp(od)).to_series(index=sar_dates).abs().argmin()
    sd=sar_dates[i]
    pairs.append({
        "optical_date":pd.Timestamp(od).date().isoformat(),
        "sar_date":pd.Timestamp(sd).date().isoformat(),
        "delta_days":abs((pd.Timestamp(sd)-pd.Timestamp(od)).days)
    })
pairs_df=pd.DataFrame(pairs)
pairs_df.to_csv(OUT/"aligned_s1_s2_dates.csv",index=False)
print(pairs_df.to_string(index=False))
selected=set(pd.to_datetime(pairs_df["sar_date"]))
sar_sel=sar[sar["date"].isin(selected)].copy()
vars_=["vv_gamma0_db","vh_gamma0_db","vh_vv_ratio_db"]

o=opt.pivot_table(index=["pilot_id","class4","zone"],
                  columns=["date","metric"],values="median",aggfunc="first")
o.columns=[f"OPT_{m}_{pd.Timestamp(d).date()}" for d,m in o.columns]
o=o.reset_index()

s=sar_sel.pivot_table(index=["pilot_id","class4","zone"],
                      columns="date",values=vars_,aggfunc="first")
s.columns=[f"SARALIGN_{v}_{pd.Timestamp(d).date()}" for v,d in s.columns]
s=s.reset_index()

X=o.merge(s,on=["pilot_id","class4","zone"],how="inner")
X.to_csv(OUT/"analysis_feature_matrix_aligned_fusion.csv",index=False)

oc=sorted(c for c in X.columns if c.startswith("OPT_"))
sc=sorted(c for c in X.columns if c.startswith("SARALIGN_"))
specs={"OPTICAL_ONLY":oc,"SAR_ALIGNED_ONLY":sc,
       "FUSION_ALIGNED":sorted(oc+sc)}
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
w["fusion_minus_optical"]=w["FUSION_ALIGNED"]-w["OPTICAL_ONLY"]
delta=pd.DataFrame([{
    "mean_date_offset_days":pairs_df["delta_days"].mean(),
    "max_date_offset_days":pairs_df["delta_days"].max(),
    "fusion_minus_optical_mean":w["fusion_minus_optical"].mean(),
    "fusion_minus_optical_sd":w["fusion_minus_optical"].std(),
    "fusion_gt_optical_seeds":int((w["fusion_minus_optical"]>0).sum()),
    "fusion_eq_optical_seeds":int((w["fusion_minus_optical"]==0).sum()),
    "fusion_lt_optical_seeds":int((w["fusion_minus_optical"]<0).sum()),
}])

d.to_csv(OUT/"aligned_repeated_seed_metrics.csv",index=False)
summary.to_csv(OUT/"aligned_repeated_seed_summary.csv",index=False)
w.reset_index().to_csv(OUT/"aligned_repeated_seed_deltas.csv",index=False)
delta.to_csv(OUT/"aligned_repeated_seed_delta_summary.csv",index=False)
print("\nAligned repeated-seed summary:")
print(summary.to_string(index=False))
print("\nDelta:")
print(delta.to_string(index=False))
