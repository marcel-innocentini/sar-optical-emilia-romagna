from pathlib import Path
import numpy as np
import pandas as pd

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
QC=BASE/"data/processed/qc"
QC.mkdir(parents=True,exist_ok=True)

def rz(s):
    s=pd.Series(s,dtype=float)
    med=s.median(); mad=(s-med).abs().median()
    if not np.isfinite(mad) or mad==0:
        return pd.Series(np.zeros(len(s)),index=s.index)
    return 0.67448975*(s-med)/mad

rows=[]

# S1 RTC: temporal anomaly per parcel and metric.
s1=pd.read_csv(BASE/"data/processed/s1_rtc_polygon_timeseries_full2023.csv")
s1["date"]=pd.to_datetime(s1["date"])
for metric in ["vv_gamma0_db","vh_gamma0_db","vh_vv_ratio_db"]:
    for pid,g in s1.groupby("pilot_id"):
        z=rz(g[metric])
        for idx,zz in z.items():
            if abs(float(zz))>=3.5:
                r=s1.loc[idx]
                rows.append({"dataset":"S1_RTC","date_or_pair":r["date"].date().isoformat(),
                    "pilot_id":pid,"class4":r["class4"],"metric":metric,
                    "value":float(r[metric]),"robust_z":float(zz),
                    "anomaly_type":"temporal_robust_z","severity":"INVESTIGATE"})

# S1 RTC: date-global median anomaly (more likely acquisition-wide).
global_rows=[]
for metric in ["vv_gamma0_db","vh_gamma0_db","vh_vv_ratio_db"]:
    x=s1.groupby("date")[metric].median().sort_index()
    z=rz(x)
    for d,v in x.items():
        global_rows.append({"dataset":"S1_RTC","date_or_pair":d.date().isoformat(),
            "metric":metric,"median_value":float(v),"robust_z":float(z.loc[d]),
            "flag":bool(abs(float(z.loc[d]))>=3.5)})

# Sentinel-2: within-date, within-class spatial anomaly.
s2=pd.read_csv(BASE/"data/processed/s2_polygon_timeseries.csv")
for (date,cl,metric),g in s2.groupby(["date","class4","metric"]):
    good=g["median"].notna()
    if good.sum()<5: continue
    z=rz(g.loc[good,"median"])
    for idx,zz in z.items():
        if abs(float(zz))>=3.5:
            r=s2.loc[idx]
            rows.append({"dataset":"S2","date_or_pair":date,"pilot_id":r["pilot_id"],
                "class4":cl,"metric":metric,"value":float(r["median"]),
                "robust_z":float(zz),"anomaly_type":"spatial_within_class",
                "severity":"INVESTIGATE"})

# Coherence: within-pair, within-class spatial anomaly.
coh=pd.read_csv(BASE/"data/processed/seasonal_coherence_polygon_timeseries.csv")
for (pair,cl),g in coh.groupby(["pair_id","class4"]):
    good=g["coherence_median"].notna()
    if good.sum()<5: continue
    z=rz(g.loc[good,"coherence_median"])
    for idx,zz in z.items():
        if abs(float(zz))>=3.5:
            r=coh.loc[idx]
            rows.append({"dataset":"S1_COHERENCE","date_or_pair":pair,
                "pilot_id":r["pilot_id"],"class4":cl,"metric":"coherence_median",
                "value":float(r["coherence_median"]),"robust_z":float(zz),
                "anomaly_type":"spatial_within_class","severity":"INVESTIGATE"})

anom=pd.DataFrame(rows,columns=["dataset","date_or_pair","pilot_id","class4","metric",
    "value","robust_z","anomaly_type","severity"])
anom.to_csv(QC/"parcel_anomalies.csv",index=False)

glob=pd.DataFrame(global_rows)
glob.to_csv(QC/"s1_date_global_anomaly_qc.csv",index=False)

# Summary rates. Statistical anomalies are investigation triggers, not automatic data failures.
universe=[]
for (date,metric),g in s1.groupby([s1["date"].dt.date.astype(str), "vv_gamma0_db"]):
    pass
for ds,src,datecol,metriccol in [
    ("S1_RTC",s1.assign(date_key=s1["date"].dt.date.astype(str)),"date_key",None),
    ("S2",s2,"date","metric"),
    ("S1_COHERENCE",coh,"pair_id",None)]:
    if ds=="S1_RTC":
        metrics=["vv_gamma0_db","vh_gamma0_db","vh_vv_ratio_db"]
        for date,g in src.groupby(datecol):
            for m in metrics:
                n=len(g); na=len(anom[(anom.dataset==ds)&(anom.date_or_pair==date)&(anom.metric==m)])
                universe.append({"dataset":ds,"date_or_pair":date,"metric":m,"n_units":n,
                    "n_anomalies":na,"anomaly_rate":na/n if n else np.nan})
    elif ds=="S2":
        for (date,m),g in src.groupby([datecol,metriccol]):
            n=g["pilot_id"].nunique(); na=len(anom[(anom.dataset==ds)&(anom.date_or_pair==date)&(anom.metric==m)])
            universe.append({"dataset":ds,"date_or_pair":date,"metric":m,"n_units":n,
                "n_anomalies":na,"anomaly_rate":na/n if n else np.nan})
    else:
        for pair,g in src.groupby(datecol):
            n=g["pilot_id"].nunique(); na=len(anom[(anom.dataset==ds)&(anom.date_or_pair==pair)])
            universe.append({"dataset":ds,"date_or_pair":pair,"metric":"coherence_median","n_units":n,
                "n_anomalies":na,"anomaly_rate":na/n if n else np.nan})
summary=pd.DataFrame(universe)
summary["acquisition_investigation_flag"]=summary["anomaly_rate"]>=0.25
summary.to_csv(QC/"date_anomaly_summary.csv",index=False)
print("Anomalies:",len(anom))
print("Acquisition-level investigation flags:",int(summary["acquisition_investigation_flag"].sum()))
print(anom.groupby("dataset").size().to_string() if len(anom) else "none")
