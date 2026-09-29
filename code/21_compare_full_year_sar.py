from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from sklearn.pipeline import Pipeline

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
OUT = BASE / "data/processed/ml"
OUT.mkdir(parents=True, exist_ok=True)

sar = pd.read_csv(BASE / "data/processed/s1_rtc_polygon_timeseries_full2023.csv")
opt = pd.read_csv(BASE / "data/processed/s2_polygon_timeseries.csv")
sar["date"] = pd.to_datetime(sar["date"])
sar["month"] = sar["date"].dt.month

vars_ = ["vv_gamma0_db","vh_gamma0_db","vh_vv_ratio_db"]
meta = sar[["pilot_id","class4","zone"]].drop_duplicates().set_index("pilot_id")

# Compact temporal descriptors: avoid using 90 raw SAR dates/features with only 47 polygons.
frames = []
for v in vars_:
    g = sar.groupby("pilot_id")[v]
    f = pd.DataFrame({
        f"SARFULL_{v}_mean": g.mean(),
        f"SARFULL_{v}_median": g.median(),
        f"SARFULL_{v}_std": g.std(),
        f"SARFULL_{v}_p10": g.quantile(0.10),
        f"SARFULL_{v}_p90": g.quantile(0.90),
    })
    f[f"SARFULL_{v}_amp80"] = f[f"SARFULL_{v}_p90"] - f[f"SARFULL_{v}_p10"]
    frames.append(f)
sar_desc = pd.concat(frames, axis=1)
# Four seasonal medians per SAR variable.
sar["season"] = pd.cut(
    sar["month"], bins=[0,3,6,9,12],
    labels=["Q1","Q2","Q3","Q4"], include_lowest=True
)
season = sar.pivot_table(
    index="pilot_id", columns=["season"], values=vars_, aggfunc="median",
    observed=True
)
season.columns = [f"SARFULL_{v}_{q}_median" for v,q in season.columns]
sar_desc = sar_desc.join(season)
sar_desc = meta.join(sar_desc).reset_index()

opt_w = opt.pivot_table(
    index=["pilot_id","class4","zone"],
    columns=["date","metric"], values="median", aggfunc="first"
)
opt_w.columns = [f"OPT_{m}_{d}" for d,m in opt_w.columns]
opt_w = opt_w.reset_index()

base = opt_w.merge(sar_desc, on=["pilot_id","class4","zone"], how="inner")
base.to_csv(OUT / "analysis_feature_matrix_optical_sar_full2023.csv", index=False)

opt_cols = [c for c in base.columns if c.startswith("OPT_")]
sar_cols = [c for c in base.columns if c.startswith("SARFULL_")]
def evaluate(name, cols):
    pipe = Pipeline([
        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
        ("rf", RandomForestClassifier(
            n_estimators=800, max_features="sqrt", min_samples_leaf=2,
            class_weight="balanced", random_state=42, n_jobs=-1
        ))
    ])
    pred_rows, fold_rows = [], []
    for zone in sorted(base["zone"].unique()):
        tr = base["zone"] != zone
        te = ~tr
        pipe.fit(base.loc[tr, cols], base.loc[tr,"class4"])
        p = pipe.predict(base.loc[te, cols])
        y = base.loc[te,"class4"]
        fold_rows.append({
            "modality":name,"test_zone":zone,
            "accuracy":accuracy_score(y,p),
            "balanced_accuracy":balanced_accuracy_score(y,p),
            "macro_f1":f1_score(y,p,average="macro",zero_division=0),
        })
        for pid,yt,yp in zip(base.loc[te,"pilot_id"],y,p):
            pred_rows.append({"modality":name,"pilot_id":pid,"zone":zone,
                              "truth":yt,"pred":yp})
    pred = pd.DataFrame(pred_rows)
    return {
        "modality":name,"n_polygons":len(base),"n_features":len(cols),
        "accuracy":accuracy_score(pred.truth,pred.pred),
        "balanced_accuracy":balanced_accuracy_score(pred.truth,pred.pred),
        "macro_f1":f1_score(pred.truth,pred.pred,average="macro",zero_division=0),
    }, pd.DataFrame(fold_rows), pred
specs = [
    ("OPTICAL_ONLY", opt_cols),
    ("SAR_FULLYEAR_DESCRIPTORS", sar_cols),
    ("OPTICAL_PLUS_SAR_FULLYEAR", opt_cols + sar_cols),
]
overall, folds, preds = [], [], []
for name, cols in specs:
    a,b,c = evaluate(name, cols)
    overall.append(a); folds.append(b); preds.append(c)

overall = pd.DataFrame(overall)
folds = pd.concat(folds, ignore_index=True)
preds = pd.concat(preds, ignore_index=True)

overall.to_csv(OUT / "full_year_sar_comparison_overall.csv", index=False)
folds.to_csv(OUT / "full_year_sar_comparison_by_zone.csv", index=False)
preds.to_csv(OUT / "full_year_sar_comparison_predictions.csv", index=False)

print("SAR dates:", sar["date"].nunique())
print("SAR descriptor features:", len(sar_cols))
print(overall.to_string(index=False))
print("\nBy zone:")
print(folds.to_string(index=False))
