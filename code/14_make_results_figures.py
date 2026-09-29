from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
OUT = BASE / "outputs/figures"
OUT.mkdir(parents=True, exist_ok=True)

m = pd.read_csv(BASE / "data/processed/ml/modality_comparison_overall.csv")
fig, ax = plt.subplots(figsize=(7.5, 4.8))
ax.bar(m["modality"], m["balanced_accuracy"])
ax.set_ylim(0, 1)
ax.set_ylabel("Balanced accuracy")
ax.set_title("Geographic holdout comparison (leave-one-zone-out)")
ax.tick_params(axis="x", rotation=18)
for i, v in enumerate(m["balanced_accuracy"]):
    ax.text(i, v + 0.025, f"{v:.3f}", ha="center")
fig.tight_layout()
fig.savefig(OUT / "01_modality_balanced_accuracy.png", dpi=220)
plt.close(fig)

opt = pd.read_csv(BASE / "data/processed/s2_polygon_timeseries.csv")
ndvi = opt[opt["metric"] == "ndvi"].copy()
ndvi["date"] = pd.to_datetime(ndvi["date"])
p = ndvi.groupby(["date","class4"])["median"].median().unstack()
fig, ax = plt.subplots(figsize=(8.5, 5.0))
for c in p.columns:
    ax.plot(p.index, p[c], marker="o", label=c)
ax.set_ylabel("Median NDVI")
ax.set_title("Sentinel-2 NDVI temporal profiles — pilot polygon cores")
ax.legend()
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig(OUT / "02_class_ndvi_profiles.png", dpi=220)
plt.close(fig)
sar = pd.read_csv(BASE / "data/processed/s1_rtc_polygon_timeseries.csv")
sar["date"] = pd.to_datetime(sar["date"])
for var, label, filename in [
    ("vv_gamma0_db", "VV gamma0 (dB)", "03_class_vv_gamma0_profiles.png"),
    ("vh_gamma0_db", "VH gamma0 (dB)", "04_class_vh_gamma0_profiles.png"),
    ("vh_vv_ratio_db", "VH/VV ratio (dB)", "05_class_vh_vv_ratio_profiles.png"),
]:
    p = sar.groupby(["date","class4"])[var].median().unstack()
    fig, ax = plt.subplots(figsize=(8.5, 5.0))
    for c in p.columns:
        ax.plot(p.index, p[c], marker="o", label=c)
    ax.set_ylabel(label)
    ax.set_title(f"Sentinel-1 RTC {label} temporal profiles — pilot polygon cores")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(OUT / filename, dpi=220)
    plt.close(fig)

print("Figures:")
for p in sorted(OUT.glob("0*_*.png")):
    print(p)
