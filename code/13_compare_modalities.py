from pathlib import Path
import json
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, confusion_matrix
from sklearn.pipeline import Pipeline

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
OUT = BASE / "data/processed/ml"
OUT.mkdir(parents=True, exist_ok=True)

opt = pd.read_csv(BASE / "data/processed/s2_polygon_timeseries.csv")
sar = pd.read_csv(BASE / "data/processed/s1_rtc_polygon_timeseries.csv")

opt_w = opt.pivot_table(
    index=["pilot_id","class4","zone"],
    columns=["date","metric"], values="median", aggfunc="first"
)
opt_w.columns = [f"OPT_{m}_{d}" for d, m in opt_w.columns]
opt_w = opt_w.reset_index()

sar_vars = ["vv_gamma0_db", "vh_gamma0_db", "vh_vv_ratio_db"]
sar_w = sar.pivot_table(
    index=["pilot_id","class4","zone"],
    columns="date", values=sar_vars, aggfunc="first"
)
sar_w.columns = [f"SAR_{v}_{d}" for v, d in sar_w.columns]
sar_w = sar_w.reset_index()

base = opt_w.merge(sar_w, on=["pilot_id","class4","zone"], how="inner")
base.to_csv(OUT / "analysis_feature_matrix_optical_sar.csv", index=False)
def evaluate(name, feature_cols):
    pipe = Pipeline([
        ("impute", SimpleImputer(strategy="median", add_indicator=True)),
        ("rf", RandomForestClassifier(
            n_estimators=600, max_features="sqrt", min_samples_leaf=2,
            class_weight="balanced", random_state=42, n_jobs=-1
        )),
    ])
    pred_rows, fold_rows = [], []
    for zone in sorted(base["zone"].unique()):
        tr = base["zone"] != zone
        te = ~tr
        pipe.fit(base.loc[tr, feature_cols], base.loc[tr, "class4"])
        pred = pipe.predict(base.loc[te, feature_cols])
        y = base.loc[te, "class4"]
        fold_rows.append({
            "modality": name, "test_zone": zone,
            "n_train": int(tr.sum()), "n_test": int(te.sum()),
            "accuracy": accuracy_score(y, pred),
            "balanced_accuracy": balanced_accuracy_score(y, pred),
            "macro_f1": f1_score(y, pred, average="macro", zero_division=0),
        })
        for pid, yt, yp in zip(base.loc[te,"pilot_id"], y, pred):
            pred_rows.append({
                "modality": name, "pilot_id": pid, "zone": zone,
                "truth": yt, "pred": yp
            })
    preds = pd.DataFrame(pred_rows)
    folds = pd.DataFrame(fold_rows)
    overall = {
        "modality": name,
        "n_polygons": len(base),
        "n_features": len(feature_cols),
        "accuracy": accuracy_score(preds["truth"], preds["pred"]),
        "balanced_accuracy": balanced_accuracy_score(preds["truth"], preds["pred"]),
        "macro_f1": f1_score(preds["truth"], preds["pred"], average="macro", zero_division=0),
    }
    return overall, folds, preds
opt_cols = [c for c in base.columns if c.startswith("OPT_")]
sar_cols = [c for c in base.columns if c.startswith("SAR_")]
specs = [
    ("OPTICAL_ONLY", opt_cols),
    ("SAR_ONLY", sar_cols),
    ("SAR_OPTICAL_FUSION", opt_cols + sar_cols),
]
all_overall, all_folds, all_preds = [], [], []
for name, cols in specs:
    o, f, p = evaluate(name, cols)
    all_overall.append(o)
    all_folds.append(f)
    all_preds.append(p)
    classes = sorted(base["class4"].unique())
    cm = confusion_matrix(p["truth"], p["pred"], labels=classes)
    pd.DataFrame(cm, index=classes, columns=classes).to_csv(
        OUT / f"{name.lower()}_confusion.csv"
    )

overall_df = pd.DataFrame(all_overall)
fold_df = pd.concat(all_folds, ignore_index=True)
pred_df = pd.concat(all_preds, ignore_index=True)
overall_df.to_csv(OUT / "modality_comparison_overall.csv", index=False)
fold_df.to_csv(OUT / "modality_comparison_by_zone.csv", index=False)
pred_df.to_csv(OUT / "modality_comparison_predictions.csv", index=False)
(OUT / "modality_comparison_note.json").write_text(json.dumps({
    "validation": "Leave-one-zone-out geographic validation across Imola, Castel Bolognese, Faenza.",
    "purpose": "Exploratory comparison of information content, not external validation or causal inference.",
    "sample": "47 curated pilot polygons; 20 m internal cores.",
    "coherence": "Not included yet; add after SLC pair processing."
}, indent=2), encoding="utf-8")

print(overall_df.to_string(index=False))
print("\nBy zone:")
print(fold_df.to_string(index=False))
