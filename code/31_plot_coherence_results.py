from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
OUT=BASE/"outputs/figures"
OUT.mkdir(parents=True,exist_ok=True)

coh=pd.read_csv(BASE/"data/processed/coherence_polygon_features.csv")
order=["ANNUAL","ORCHARD","OLIVE","VINEYARD"]

fig,ax=plt.subplots(figsize=(7.5,5.0))
data=[coh.loc[coh["class4"]==c,"coherence_median"].values for c in order]
ax.boxplot(data,tick_labels=order,showmeans=True)
ax.set_ylim(0,1)
ax.set_ylabel("Median interferometric coherence")
ax.set_title("Sentinel-1 coherence by land-use class\n03–15 June 2023, 12-day pair")
fig.tight_layout()
fig.savefig(OUT/"10_coherence_by_class.png",dpi=220)
plt.close(fig)

m=pd.read_csv(BASE/"data/processed/ml/coherence_repeated_seed_summary.csv")
fig,ax=plt.subplots(figsize=(9.0,5.0))
ax.bar(m["modality"],m["ba_mean"],yerr=m["ba_sd"],capsize=4)
ax.set_ylim(0,0.8)
ax.set_ylabel("Balanced accuracy (mean ± SD)")
ax.set_title("Incremental effect of interferometric coherence\n20 RF seeds, fixed geographic folds")
ax.tick_params(axis="x",rotation=20)
fig.tight_layout()
fig.savefig(OUT/"11_coherence_incremental_validation.png",dpi=220)
plt.close(fig)
print("Figures written.")
