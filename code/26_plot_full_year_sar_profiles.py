from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
d=pd.read_csv(BASE/"data/processed/s1_rtc_polygon_timeseries_full2023.csv")
d["date"]=pd.to_datetime(d["date"])
OUT=BASE/"outputs/figures"

for var,label,num in [
    ("vv_gamma0_db","VV gamma0 (dB)","07"),
    ("vh_gamma0_db","VH gamma0 (dB)","08"),
    ("vh_vv_ratio_db","VH/VV ratio (dB)","09"),
]:
    p=d.groupby(["date","class4"])[var].median().unstack()
    fig,ax=plt.subplots(figsize=(10,5))
    for c in p.columns:
        ax.plot(p.index,p[c],marker="o",markersize=3,label=c)
    ax.set_ylabel(label)
    ax.set_title(f"Sentinel-1 RTC full-year temporal profile — {label}")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    out=OUT/f"{num}_full_year_{var}.png"
    fig.savefig(out,dpi=220)
    plt.close(fig)
    print(out)
