from pathlib import Path
import pandas as pd
import geopandas as gpd
from scipy.stats import spearmanr

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
ML=BASE/"data/processed/ml"

coh=pd.read_csv(BASE/"data/processed/coherence_polygon_features.csv")
coh=coh[["pilot_id","class4","zone","coherence_median"]].copy()

sar=pd.read_csv(BASE/"data/processed/s1_rtc_polygon_timeseries_full2023.csv")
sar["date"]=pd.to_datetime(sar["date"])
# Pair dates used to generate coherence
pair_dates=pd.to_datetime(["2023-06-03","2023-06-15"])
sarj=sar[sar["date"].isin(pair_dates)].pivot_table(
    index="pilot_id",columns="date",
    values=["vv_gamma0_db","vh_gamma0_db","vh_vv_ratio_db"],aggfunc="first")
sarj.columns=[f"{v}_{pd.Timestamp(d).date()}" for v,d in sarj.columns]
sarj=sarj.reset_index()

opt=pd.read_csv(BASE/"data/processed/s2_polygon_timeseries.csv")
opt["date"]=pd.to_datetime(opt["date"])
# Nearest optical date before and after coherence interval
optn=opt[opt["date"].isin(pd.to_datetime(["2023-05-23","2023-07-17"]))].pivot_table(
    index="pilot_id",columns=["date","metric"],values="median",aggfunc="first")
optn.columns=[f"{m}_{pd.Timestamp(d).date()}" for d,m in optn.columns]
optn=optn.reset_index()

x=coh.merge(sarj,on="pilot_id",how="left").merge(optn,on="pilot_id",how="left")
rows=[]
for c in x.columns:
    if c in ["pilot_id","class4","zone","coherence_median"]: continue
    rho,p=spearmanr(x["coherence_median"],x[c],nan_policy="omit")
    rows.append({"feature":c,"spearman_rho":rho,"p_value":p})
corr=pd.DataFrame(rows).sort_values("spearman_rho",key=lambda s:s.abs(),ascending=False)
corr.to_csv(ML/"coherence_redundancy_correlations.csv",index=False)
print("Coherence correlations:")
print(corr.to_string(index=False))
# Candidate 12-day SLC pairs on the same path/frame as the processed pair.
slc=gpd.read_file(BASE/"metadata/sentinel1_slc_2023_asf.geojson")
q=slc[(slc["flightDirection"]=="DESCENDING")&
      (slc["pathNumber"]==95)&
      (slc["frameNumber"]==445)].copy()
q["date"]=pd.to_datetime(q["startTime"],utc=True)
q=q.sort_values("date").drop_duplicates("sceneName")

vals=list(q.itertuples())
pairs=[]
for i,a in enumerate(vals):
    for b in vals[i+1:]:
        dt=(b.date-a.date).days
        if dt>13: break
        if 11<=dt<=13:
            mid=a.date+(b.date-a.date)/2
            pairs.append({
                "master":a.sceneName,"master_time":a.startTime,
                "slave":b.sceneName,"slave_time":b.startTime,
                "delta_days":dt,"mid_date":mid.date().isoformat(),
                "month":mid.month
            })
pairs=pd.DataFrame(pairs)
targets=[2,4,6,8,10,12]
sel=[]
for m in targets:
    if pairs.empty: break
    score=(pairs["month"]-m).abs()
    candidate=pairs.loc[score.idxmin()]
    sel.append(candidate)
seasonal=pd.DataFrame(sel).drop_duplicates(["master","slave"])
seasonal.to_csv(ML/"candidate_seasonal_coherence_pairs.csv",index=False)
print("\nSeasonal candidate 12-day pairs:")
print(seasonal[["mid_date","master_time","slave_time","delta_days","master","slave"]].to_string(index=False))
print("\nAdditional cost at 15 credits/pair if June pair is reused:",
      max(0,len(seasonal)-1)*15)
