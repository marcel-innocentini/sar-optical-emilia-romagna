from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
d=pd.read_csv(BASE/"data/processed/ml/repeated_seed_metrics.csv")
order=["OPTICAL_ONLY","SAR_ONLY","FUSION"]
data=[d.loc[d.modality==m,"balanced_accuracy"].values for m in order]

fig,ax=plt.subplots(figsize=(7.5,4.8))
ax.boxplot(data,tick_labels=order,showmeans=True)
ax.set_ylim(0,1)
ax.set_ylabel("Balanced accuracy")
ax.set_title("Algorithmic stability across 20 Random Forest seeds")
fig.tight_layout()
out=BASE/"outputs/figures/06_repeated_seed_stability.png"
fig.savefig(out,dpi=220)
plt.close(fig)
print(out)
