from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
QC=BASE/"data/processed/qc"; FIG=BASE/"outputs/figures_qc"; DOC=BASE/"docs"
FIG.mkdir(parents=True,exist_ok=True); DOC.mkdir(parents=True,exist_ok=True)

reg=pd.read_csv(QC/"product_qc_register_base.csv")
anom=pd.read_csv(QC/"date_anomaly_summary.csv")
parcel=pd.read_csv(QC/"parcel_anomalies.csv")
s1acq=pd.read_csv(QC/"s1_acquisition_qc.csv")
rtc=pd.read_csv(QC/"s1_rtc_qc.csv")
coh=pd.read_csv(QC/"s1_coherence_pair_qc.csv")
s2d=pd.read_csv(QC/"s2_date_qc.csv")
cross=pd.read_csv(QC/"cross_sensor_qc.csv")
rep=pd.read_csv(QC/"reprocessing_replication_qc.csv")
repsum=pd.read_csv(QC/"reprocessing_validation_summary.csv")
reppoly=pd.read_csv(QC/"reprocessing_polygon_effects.csv")

# Integrate automatic anomaly investigation flags without treating parcel anomalies as failures.
reg["anomaly_investigation_flag"]=False
reg["anomaly_note"]=""
for i,r in reg.iterrows():
    ds={"S1_RTC":"S1_RTC","S2_L2A":"S2","S1_COHERENCE":"S1_COHERENCE"}.get(r["product_type"])
    if ds is None: continue
    g=anom[(anom["dataset"]==ds)&(anom["date_or_pair"].astype(str)==str(r["date_or_pair"]))]
    flagged=g[g["acquisition_investigation_flag"]==True]
    if len(flagged):
        reg.loc[i,"anomaly_investigation_flag"]=True
        reg.loc[i,"anomaly_note"]="; ".join(f"{x.metric}:{x.anomaly_rate:.1%}" for x in flagged.itertuples())
        if r["status"]=="PASS":
            reg.loc[i,"status"]="WARNING"
            reg.loc[i,"reason"]=str(r["reason"])+"; widespread statistical anomaly requires investigation"
reg.to_csv(QC/"product_qc_register.csv",index=False)

summary_obj={
    "workflow":"dataset -> quality control -> anomaly investigation -> reprocessing -> validation -> reporting",
    "status_counts":reg["status"].value_counts().to_dict(),
    "s1_acquisitions":int(len(s1acq)),
    "s1_rtc_rasters":int(len(rtc)),
    "coherence_pairs":int(len(coh)),
    "s2_dates":int(len(s2d)),
    "cross_sensor_pairs":int(len(cross)),
    "parcel_anomaly_triggers":int(len(parcel)),
    "acquisition_anomaly_flags":int(anom["acquisition_investigation_flag"].sum()),
    "baseline_reprocessing_max_rmse":float(rep["replication_rmse"].max()),
}
(QC/"qc_report.json").write_text(json.dumps(summary_obj,indent=2),encoding="utf-8")

fig,ax=plt.subplots(figsize=(11,4.5))
sd=pd.to_datetime(s1acq["date"]); od=pd.to_datetime(s2d["date"])
cm=pd.to_datetime(coh["master_date"])+(pd.to_datetime(coh["slave_date"])-pd.to_datetime(coh["master_date"]))/2
ax.scatter(sd,np.zeros(len(sd)),label="Sentinel-1 RTC (30)",s=28)
ax.scatter(od,np.ones(len(od)),label="Sentinel-2 L2A (5)",s=70,marker="s")
ax.scatter(cm,np.full(len(cm),2),label="S1 coherence pairs (6)",s=70,marker="D")
ax.set_yticks([0,1,2],["S1 RTC","S2 L2A","S1 coherence"])
ax.set_title("SAR 1B - EO product availability and temporal coverage")
ax.grid(axis="x",alpha=.25); ax.legend(loc="upper center",ncol=3)
fig.tight_layout(); fig.savefig(FIG/"15_qc_availability_timeline.png",dpi=180); plt.close(fig)

fig,ax=plt.subplots(figsize=(11,5))
for pol,g in rtc.groupby("polarization"):
    g=g.copy(); g["date"]=pd.to_datetime(g["date"])
    ax.plot(g["date"],g["median_db"],marker="o",ms=3,label=f"{pol} AOI median")
warn=rtc[rtc["status"]!="PASS"].copy()
if len(warn):
    warn["date"]=pd.to_datetime(warn["date"])
    ax.scatter(warn["date"],warn["median_db"],marker="x",s=70,label="QC warning/fail")
ax.set_ylabel("gamma0 median (dB)"); ax.set_title("Sentinel-1 RTC distribution consistency")
ax.grid(alpha=.25); ax.legend()
fig.tight_layout(); fig.savefig(FIG/"16_rtc_distribution_qc.png",dpi=180); plt.close(fig)

fig,ax=plt.subplots(figsize=(9,5))
x=np.arange(len(s2d)); labels=pd.to_datetime(s2d["date"]).dt.strftime("%d %b").tolist()
ax.bar(x,s2d["fraction_polygons_pass"],label="fraction of polygons >=80% valid")
ax.plot(x,s2d["median_valid_fraction"],marker="o",label="median valid fraction")
ax.scatter(x,s2d["min_valid_fraction"],marker="v",label="minimum valid fraction")
ax.axhline(.8,ls="--",lw=1,label="polygon PASS threshold")
ax.set_xticks(x,labels); ax.set_ylim(0,1.05); ax.set_ylabel("fraction")
ax.set_title("Sentinel-2 cloud/quality-mask availability")
ax.grid(axis="y",alpha=.25); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(FIG/"17_s2_valid_fraction_qc.png",dpi=180); plt.close(fig)

fig,ax=plt.subplots(figsize=(10,5))
x=np.arange(len(coh)); labels=pd.to_datetime(coh["master_date"]).dt.strftime("%b").tolist()
ax.bar(x,coh["abs_baseline_m"],alpha=.75,label="|perpendicular baseline| (m)")
ax.axhline(200,ls="--",lw=1,label="project WARNING band")
ax.set_ylabel("|baseline| (m)"); ax.set_xticks(x,labels)
ax2=ax.twinx(); ax2.plot(x,coh["coherence_median_all_polygons"],marker="o",label="median coherence")
ax2.set_ylabel("median coherence"); ax2.set_ylim(0,1)
ax.set_title("SLC/coherence pair QC: geometry versus observed coherence")
h1,l1=ax.get_legend_handles_labels(); h2,l2=ax2.get_legend_handles_labels()
ax.legend(h1+h2,l1+l2,loc="upper center",ncol=3,fontsize=8)
fig.tight_layout(); fig.savefig(FIG/"18_coherence_pair_qc.png",dpi=180); plt.close(fig)

plot=repsum.copy()
plot["label"]=plot["experiment"].str.replace("_"," ")+" / "+plot["metric"].str.upper()
fig,ax=plt.subplots(figsize=(11,5))
ax.bar(np.arange(len(plot)),plot["median_abs_delta"])
ax.set_xticks(np.arange(len(plot)),plot["label"],rotation=35,ha="right")
ax.set_ylabel("median absolute change in polygon median")
ax.set_title("Controlled reprocessing: sensitivity to mask and 20 m resampling policy")
ax.grid(axis="y",alpha=.25)
fig.tight_layout(); fig.savefig(FIG/"19_reprocessing_impact.png",dpi=180); plt.close(fig)

counts=reg["status"].value_counts().reindex(["PASS","WARNING","FAIL"],fill_value=0)
fig,ax=plt.subplots(figsize=(7,4.5))
ax.bar(counts.index,counts.values)
for i,v in enumerate(counts.values): ax.text(i,v+0.5,str(int(v)),ha="center")
ax.set_ylabel("products / checks"); ax.set_title("SAR 1B final PASS / WARNING / FAIL register")
ax.set_ylim(0,max(counts.max()*1.15,3)); ax.grid(axis="y",alpha=.2)
fig.tight_layout(); fig.savefig(FIG/"20_qc_status_summary.png",dpi=180); plt.close(fig)

warnings=reg[reg["status"]!="PASS"][["product_type","product_id","date_or_pair","status","reason"]]
mean_cross=float(cross["delta_days"].mean()); max_cross=int(cross["delta_days"].max())
strict=repsum[repsum["experiment"]=="STRICT_SCL_MASK"]
nearest=repsum[repsum["experiment"]=="NEAREST_20M_RESAMPLING"]
strict_loss=float(strict["min_delta_valid_fraction"].min()) if len(strict) else np.nan
nearest_effect=float(nearest["p95_abs_delta"].max()) if len(nearest) else np.nan
oct_pass=float(s2d.loc[s2d.date=="2023-10-10","fraction_polygons_pass"].iloc[0])

report=f"""# SAR 1B - EO Data Quality & Processing Validation for Agricultural Monitoring in Emilia-Romagna

**Extension of SAR 1.** Study area: Imola-Castel Bolognese-Faenza corridor, Emilia-Romagna, Italy.

## Purpose

SAR 1B converts the existing agricultural Sentinel-1/Sentinel-2 workflow into an explicit Earth Observation data-quality and processor-validation chain:

**dataset -> quality control -> anomaly investigation -> reprocessing -> validation -> reporting**

The workflow is intentionally traceable. Thresholds are project QC rules documented in metadata/SAR1B_QC_THRESHOLDS.json; they are not represented as ESA mission acceptance specifications.

## Executive QC result

- Final register: **{int((reg.status=="PASS").sum())} PASS, {int((reg.status=="WARNING").sum())} WARNING, {int((reg.status=="FAIL").sum())} FAIL**.
- Sentinel-1 acquisition series: **{len(s1acq)}** path-95/frame-445 descending VV+VH acquisitions from {s1acq.date.min()} to {s1acq.date.max()}.
- RTC QA: **{len(rtc)}** polarization rasters; minimum valid fraction **{rtc.valid_fraction.min():.3%}**; no acquisition-wide anomaly flag.
- SLC/coherence: **{len(coh)}** 12-day pairs. One geometry warning is retained for the February pair because |baseline| = **{coh.abs_baseline_m.max():.1f} m**, above the project 200 m investigation band.
- Sentinel-2: **{len(s2d)}** dates. The 2023-10-10 acquisition is retained as WARNING because only **{oct_pass:.1%}** of pilot polygons reach 80% valid support and some polygons have zero valid pixels.
- S1 x S2 temporal matching: mean offset **{mean_cross:.1f} d**, maximum **{max_cross} d**; the 4-day July match is a WARNING under the project <=3 d PASS rule.
- Automated parcel-level anomaly detector generated **{len(parcel)}** INVESTIGATE triggers, but **{int(anom.acquisition_investigation_flag.sum())}** acquisition-wide anomaly flags. Parcel anomalies are therefore not automatically treated as product failures.

## Controlled reprocessing / processor verification

The Sentinel-2 index processor was independently re-run from the stored band mosaics and SCL layer using the original scale/offset, cloud-mask logic and bilinear alignment of 20 m bands. Pixelwise comparison with the previously generated products gives a maximum replication RMSE of **{rep.replication_rmse.max():.3e}**, verifying reproducibility of the baseline processor.

Two controlled parameter changes were then tested:

1. **Strict SCL mask:** adds SCL classes 2 (dark area pixels) and 7 (unclassified) to the exclusion policy while retaining the original bilinear resampling.
2. **20 m resampling variant:** changes B05/B11 alignment from bilinear to nearest-neighbour while retaining the original SCL mask.

The strict-mask experiment produced a worst parcel-level relative valid-pixel change of **{strict_loss:.1%}**. The largest 95th-percentile absolute polygon-median change produced by the nearest-neighbour resampling experiment was **{nearest_effect:.4f}** index units. These results quantify the effect of processing choices rather than assuming processor invariance.

## PASS / WARNING / FAIL items

{warnings.to_markdown(index=False) if len(warnings) else "All products passed."}

## QA dimensions implemented

### Sentinel-1 acquisitions
Relative orbit, frame, flight direction, VV/VH availability, acquisition cadence and temporal gaps are checked against the project configuration.

### Sentinel-1 RTC
The workflow checks raster presence, CRS/resolution, positive finite gamma0 support, no-data fraction, edge-versus-interior validity and robust temporal distribution anomalies for VV and VH.

### SLC/coherence
Each pair is checked for temporal interval, perpendicular baseline, looks, output resolution, polygon coverage and physical coherence range. Baseline-driven warnings are separated from seasonal coherence variability.

### Sentinel-2
SCL-based valid support is measured per pilot polygon together with cloud, shadow, saturated/defective, no-data, dark-area and unclassified fractions. Availability is summarized at acquisition level.

### Cross-sensor comparability
Nearest-date S1/S2 matches, temporal offsets, native CRS, nominal resolution and common AOI footprint are reported. S1 is EPSG:32633 and S2 is EPSG:32632 in the stored products; analyses therefore use common polygon support rather than assuming pixel-grid identity.

### Automated anomaly investigation
Robust MAD-based detectors operate on S1 temporal parcel series and on within-class S2/coherence distributions. Statistical anomalies are labelled INVESTIGATE and only escalate acquisition status if they become widespread.

## Interpretation

The SAR 1B workflow does not claim to reproduce an ESA operational IPF or mission-specific acceptance procedure. It demonstrates the transferable engineering logic required for instrument/product-quality support: systematic QC, traceable status assignment, anomaly isolation, controlled reprocessing, quantitative comparison, validation and reporting using real EO products.

## Reproducible outputs

- code/40_sar1b_dataset_qc.py
- code/41_sar1b_anomaly_detection.py
- code/42_sar1b_reprocessing_validation.py
- code/43_sar1b_reporting.py
- data/processed/qc/product_qc_register.csv
- data/processed/qc/qc_report.json
- outputs/figures_qc/15_qc_availability_timeline.png through 20_qc_status_summary.png
"""
(DOC/"SAR1B_TECHNICAL_REPORT.md").write_text(report,encoding="utf-8")

print("Reporting complete")
print(reg["status"].value_counts().to_string())
print("Warnings:")
print(warnings.to_string(index=False))
