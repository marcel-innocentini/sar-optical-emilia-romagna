from pathlib import Path
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from sklearn.pipeline import Pipeline

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
OUT = BASE / "data/processed/ml"
X = pd.read_csv(OUT / "analysis_feature_matrix_optical_sar.csv")
coh = pd.read_csv(BASE / "data/processed/coherence_polygon_features.csv")

# One coherence product is expected for the fixed 12-day pair.
coh1 = coh.groupby(["pilot_id","class4","zone"], as_index=False).agg(
    COH_median=("coherence_median","median"),
    COH_mean=("coherence_mean","mean"),
    COH_std=("coherence_std","mean"),
)
X = X.merge(coh1, on=["pilot_id","class4","zone"], how="inner")

opt_cols = [c for c in X.columns if c.startswith("OPT_")]
sar_cols = [c for c in X.columns if c.startswith("SAR_")]
coh_cols = [c for c in X.columns if c.startswith("COH_")]

def evaluate(name, cols):
    pipe = Pipeline([
        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
        ("rf", RandomForestClassifier(
            n_estimators=600, max_features="sqrt", min_samples_leaf=2,
            class_weight="balanced", random_state=42, n_jobs=-1
        )),
    ])
    preds, folds = [], []
    for zone in sorted(X["zone"].unique()):
        tr = X["zone"] != zone
        te = ~tr
        pipe.fit(X.loc[tr, cols], X.loc[tr, "class4"])
        p = pipe.predict(X.loc[te, cols])
        y = X.loc[te, "class4"]
        folds.append({
            "modality": name, "test_zone": zone,
            "balanced_accuracy": balanced_accuracy_score(y,p),
            "macro_f1": f1_score(y,p,average="macro",zero_division=0),
        })
        for pid, yt, yp in zip(X.loc[te,"pilot_id"], y, p):
            preds.append({"modality":name,"pilot_id":pid,"truth":yt,"pred":yp})
    p = pd.DataFrame(preds)
    return {
        "modality": name,
        "n_polygons": len(X),
        "n_features": len(cols),
        "accuracy": accuracy_score(p.truth,p.pred),
        "balanced_accuracy": balanced_accuracy_score(p.truth,p.pred),
        "macro_f1": f1_score(p.truth,p.pred,average="macro",zero_division=0),
    }, pd.DataFrame(folds), p

specs = [
    ("OPTICAL_ONLY", opt_cols),
    ("SAR_ONLY", sar_cols),
    ("SAR_PLUS_COHERENCE", sar_cols + coh_cols),
    ("SAR_OPTICAL_FUSION", opt_cols + sar_cols),
    ("SAR_OPTICAL_PLUS_COHERENCE", opt_cols + sar_cols + coh_cols),
]
overall, folds, preds = [], [], []
for name, cols in specs:
    a,b,c = evaluate(name, cols)
    overall.append(a); folds.append(b); preds.append(c)

pd.DataFrame(overall).to_csv(OUT / "modality_comparison_with_coherence_overall.csv", index=False)
pd.concat(folds,ignore_index=True).to_csv(OUT / "modality_comparison_with_coherence_by_zone.csv", index=False)
pd.concat(preds,ignore_index=True).to_csv(OUT / "modality_comparison_with_coherence_predictions.csv", index=False)
print(pd.DataFrame(overall).to_string(index=False))
