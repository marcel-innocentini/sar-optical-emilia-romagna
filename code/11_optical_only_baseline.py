from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, confusion_matrix
from sklearn.pipeline import Pipeline

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
IN = BASE / "data/processed/s2_polygon_timeseries.csv"
OUT = BASE / "data/processed/ml"
OUT.mkdir(parents=True, exist_ok=True)

d = pd.read_csv(IN)
# One observation per polygon. Temporal optical signatures become columns.
wide = d.pivot_table(
    index=["pilot_id","class4","zone"],
    columns=["date","metric"],
    values="median",
    aggfunc="first"
)
wide.columns = [f"{metric}_{date}" for date, metric in wide.columns]
wide = wide.reset_index()
feature_cols = [c for c in wide.columns if c not in ["pilot_id","class4","zone"]]

pipe = Pipeline([
    ("impute", SimpleImputer(strategy="median", add_indicator=True)),
    ("rf", RandomForestClassifier(
        n_estimators=600, max_features="sqrt", min_samples_leaf=2,
        class_weight="balanced", random_state=42, n_jobs=-1
    )),
])
classes = sorted(wide["class4"].unique())
pred_rows = []
fold_rows = []

# Geographic holdout: train on two corridor zones, test on the third.
for test_zone in sorted(wide["zone"].unique()):
    train = wide["zone"] != test_zone
    test = ~train
    Xtr, Xte = wide.loc[train, feature_cols], wide.loc[test, feature_cols]
    ytr, yte = wide.loc[train, "class4"], wide.loc[test, "class4"]
    pipe.fit(Xtr, ytr)
    pred = pipe.predict(Xte)
    fold_rows.append({
        "test_zone": test_zone,
        "n_train": int(train.sum()), "n_test": int(test.sum()),
        "accuracy": accuracy_score(yte, pred),
        "balanced_accuracy": balanced_accuracy_score(yte, pred),
        "macro_f1": f1_score(yte, pred, average="macro", zero_division=0),
    })
    for pid, yt, yp in zip(wide.loc[test,"pilot_id"], yte, pred):
        pred_rows.append({"pilot_id": pid, "zone": test_zone, "truth": yt, "pred": yp})

folds = pd.DataFrame(fold_rows)
preds = pd.DataFrame(pred_rows)
folds.to_csv(OUT / "optical_only_leave_zone_out_metrics.csv", index=False)
preds.to_csv(OUT / "optical_only_leave_zone_out_predictions.csv", index=False)
cm = confusion_matrix(preds["truth"], preds["pred"], labels=classes)
pd.DataFrame(cm, index=classes, columns=classes).to_csv(
    OUT / "optical_only_leave_zone_out_confusion.csv"
)

overall = {
    "n_polygons": int(len(wide)),
    "n_features_raw": int(len(feature_cols)),
    "classes": classes,
    "zones": sorted(wide["zone"].unique().tolist()),
    "accuracy": float(accuracy_score(preds["truth"], preds["pred"])),
    "balanced_accuracy": float(balanced_accuracy_score(preds["truth"], preds["pred"])),
    "macro_f1": float(f1_score(preds["truth"], preds["pred"], average="macro", zero_division=0)),
    "validation": "leave-one-zone-out; three geographic folds",
    "interpretation": "Exploratory baseline only; small curated pilot sample, not an external validation.",
}
(OUT / "optical_only_baseline_summary.json").write_text(
    json.dumps(overall, indent=2), encoding="utf-8"
)

# Fit all data only for exploratory feature importance.
pipe.fit(wide[feature_cols], wide["class4"])
rf = pipe.named_steps["rf"]
imputer = pipe.named_steps["impute"]
names = list(feature_cols)
if hasattr(imputer, "indicator_") and imputer.indicator_.features_.size:
    names += [f"missing__{feature_cols[i]}" for i in imputer.indicator_.features_]
imp = pd.DataFrame({"feature": names, "importance": rf.feature_importances_})
imp.sort_values("importance", ascending=False).to_csv(
    OUT / "optical_only_feature_importance.csv", index=False
)

print(pd.DataFrame([overall]).to_string(index=False))
print("\nBy geographic holdout:")
print(folds.to_string(index=False))
print("\nConfusion:")
print(pd.DataFrame(cm, index=classes, columns=classes).to_string())
