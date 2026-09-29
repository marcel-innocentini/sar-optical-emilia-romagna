from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
OUT=BASE/"outputs/figures"
OUT.mkdir(parents=True,exist_ok=True)

d=pd.read_csv(BASE/"data/processed/seasonal_coherence_polygon_timeseries.csv")
d["mid_date"]=pd.to_datetime(d["mid_date"])

p=d.groupby(["mid_date","class4"])["coherence_median"].median().unstack()
fig,ax=plt.subplots(figsize=(9.0,5.2))
for c in p.columns:
    ax.plot(p.index,p[c],marker="o",label=c)
ax.set_ylim(0,1)
ax.set_ylabel("Median coherence")
ax.set_title("Seasonal Sentinel-1 interferometric coherence")
ax.legend()
fig.autofmt_xdate()
fig.tight_layout()
fig.savefig(OUT/"12_seasonal_coherence_profiles.png",dpi=220)
plt.close(fig)

m=pd.read_csv(BASE/"data/processed/ml/seasonal_coherence_summary.csv")
fig,ax=plt.subplots(figsize=(10.5,5.3))
ax.bar(m["modality"],m["ba_mean"],yerr=m["ba_sd"],capsize=4)
ax.set_ylim(0,0.85)
ax.set_ylabel("Balanced accuracy (mean ± SD)")
ax.set_title("Seasonal coherence contribution — 20 RF seeds")
ax.tick_params(axis="x",rotation=24)
fig.tight_layout()
fig.savefig(OUT/"13_seasonal_coherence_validation.png",dpi=220)
plt.close(fig)

print("Figures written.")
