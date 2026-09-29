from pathlib import Path
import shutil, hashlib, zipfile, json
import pandas as pd
import matplotlib.pyplot as plt

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
ML=BASE/"data/processed/ml"
FIG=BASE/"outputs/figures"

# Consolidated final comparison
aligned=pd.read_csv(ML/"aligned_repeated_seed_summary.csv").set_index("modality")
seasonal=pd.read_csv(ML/"seasonal_coherence_summary.csv").set_index("modality")
desc=pd.read_csv(ML/"coherence_descriptor_summary.csv").set_index("modality")
full=pd.read_csv(ML/"repeated_full_year_seed_summary.csv").set_index("modality")

rows=[
    ["OPTICAL_ONLY", aligned.loc["OPTICAL_ONLY","ba_mean"], aligned.loc["OPTICAL_ONLY","ba_sd"], aligned.loc["OPTICAL_ONLY","f1_mean"], "5 Sentinel-2 dates"],
    ["SAR_ALIGNED_ONLY", aligned.loc["SAR_ALIGNED_ONLY","ba_mean"], aligned.loc["SAR_ALIGNED_ONLY","ba_sd"], aligned.loc["SAR_ALIGNED_ONLY","f1_mean"], "5 nearest Sentinel-1 RTC dates"],
    ["FUSION_ALIGNED", aligned.loc["FUSION_ALIGNED","ba_mean"], aligned.loc["FUSION_ALIGNED","ba_sd"], aligned.loc["FUSION_ALIGNED","f1_mean"], "temporally aligned S1+S2"],
    ["COHERENCE_SEASONAL_ONLY", seasonal.loc["COHERENCE_SEASONAL_ONLY","ba_mean"], seasonal.loc["COHERENCE_SEASONAL_ONLY","ba_sd"], seasonal.loc["COHERENCE_SEASONAL_ONLY","f1_mean"], "6 twelve-day coherence pairs"],
    ["FUSION_PLUS_SEASONAL_COH", seasonal.loc["FUSION_PLUS_SEASONAL_COH","ba_mean"], seasonal.loc["FUSION_PLUS_SEASONAL_COH","ba_sd"], seasonal.loc["FUSION_PLUS_SEASONAL_COH","f1_mean"], "aligned S1+S2 + 6 coherence"],
    ["FUSION_PLUS_COH_DESC", desc.loc["FUSION_PLUS_COH_DESC","ba_mean"], desc.loc["FUSION_PLUS_COH_DESC","ba_sd"], desc.loc["FUSION_PLUS_COH_DESC","f1_mean"], "aligned S1+S2 + coherence temporal descriptors"],
    ["SAR_FULLYEAR", full.loc["SAR_FULLYEAR","ba_mean"], full.loc["SAR_FULLYEAR","ba_sd"], full.loc["SAR_FULLYEAR","f1_mean"], "30-date SAR temporal descriptors"],
]
final=pd.DataFrame(rows,columns=["representation","ba_mean","ba_sd","f1_mean","description"])
final.to_csv(ML/"FINAL_MODEL_COMPARISON.csv",index=False)

fig,ax=plt.subplots(figsize=(10.5,5.5))
ax.bar(final["representation"],final["ba_mean"],yerr=final["ba_sd"],capsize=4)
ax.set_ylim(0,0.8)
ax.set_ylabel("Balanced accuracy (mean ± SD)")
ax.set_title("Final modality comparison — fixed geographic folds, 20 RF seeds")
ax.tick_params(axis="x",rotation=28)
fig.tight_layout()
fig.savefig(FIG/"14_final_modality_comparison.png",dpi=220)
plt.close(fig)
# Final run log
log=BASE/"metadata/RUN_LOG_2026-09-29_FINAL.txt"
log.write_text(
f"""SAR-OPTICAL PERENNIAL CROPS ITALY — FINAL v0.1
Date: 2026-09-29

AOI: Imola–Castel Bolognese–Faenza, Emilia-Romagna
Reference polygons: 47 (12 vineyard, 12 orchard, 11 olive, 12 annual)
Primary core buffer: 20 m

Sentinel-1 RTC:
- Descending path 95 / frame 445
- 30 acquisitions in 2023
- 1,410 polygon-date records

Sentinel-2:
- 5 L2A dates
- scale 0.0001, offset -0.1 applied before indices
- NDVI, NDRE, NDMI, GNDVI

InSAR coherence:
- 6 x 12-day Sentinel-1 SLC pairs
- 10x2 looks, 40 m output, GLO-30
- 282 polygon-pair records
- perpendicular baseline range: -225.6053 to +173.3043 m
- HyP3 credits used: 90 total (15 June pilot + 75 seasonal extension)
- remaining credits after seasonal run: 7910

Preferred exploratory model result:
- Optical only BA mean: {aligned.loc["OPTICAL_ONLY","ba_mean"]:.6f}
- Aligned SAR only BA mean: {aligned.loc["SAR_ALIGNED_ONLY","ba_mean"]:.6f}
- Aligned SAR+optical BA mean: {aligned.loc["FUSION_ALIGNED","ba_mean"]:.6f}
- Mean aligned fusion gain over optical: 0.018371

Coherence:
- 6 raw seasonal features + fusion BA mean: {seasonal.loc["FUSION_PLUS_SEASONAL_COH","ba_mean"]:.6f}
- coherence temporal descriptors + fusion BA mean: {desc.loc["FUSION_PLUS_COH_DESC","ba_mean"]:.6f}
- no stable incremental gain

Multiple temporal tests:
- February raw Kruskal-Wallis p=0.034046
- adjusted Bonferroni/FDR p=0.204277
- no epoch significant at FDR 0.05

Interpretation:
Exploratory separability only. No claims of yield, physiology, causality,
operational crop-map accuracy, or universal SAR superiority.
""",encoding="utf-8")
# Build lightweight reproducible release
RELROOT=BASE/"release"
REL=RELROOT/"SAR_Optical_Perennial_Crops_Italy_v1.0"
if REL.exists():
    shutil.rmtree(REL)
REL.mkdir(parents=True)

for name in ["README.md","requirements.txt","CITATION.cff"]:
    shutil.copy2(BASE/name,REL/name)

for folder in ["code","docs"]:
    shutil.copytree(BASE/folder,REL/folder)

# metadata: include all compact provenance files
shutil.copytree(BASE/"metadata",REL/"metadata")

# outputs
shutil.copytree(BASE/"outputs",REL/"outputs")

# compact analytical data only
dstd=REL/"data/processed"
dstd.mkdir(parents=True)
top_files=[
    "aoi_corridor.gpkg","aoi_corridor.geojson",
    "pilot_polygons.gpkg","pilot_polygons.csv",
    "pilot_polygons_core20m.gpkg","pilot_polygons_core20m.csv",
    "landuse_selection_summary.csv",
    "s1_rtc_polygon_timeseries.csv",
    "s1_rtc_polygon_timeseries_full2023.csv",
    "s2_polygon_timeseries.csv",
    "coherence_polygon_features.csv",
    "seasonal_coherence_polygon_timeseries.csv",
]
for name in top_files:
    src=BASE/"data/processed"/name
    if src.exists():
        shutil.copy2(src,dstd/name)
shutil.copytree(ML,dstd/"ml")

(REL/"README_RELEASE.md").write_text(
"""# Release v1.0

This lightweight research release contains code, provenance, pilot geometries,
polygon-level analytical tables, model outputs, figures and documentation.

Large raw/derived satellite rasters are intentionally excluded:
Sentinel-1 GRD archives, Sentinel-1 RTC GeoTIFFs, Sentinel-2 band/index rasters,
and HyP3 InSAR ZIP/GeoTIFF products remain in the local project archive.
Their identifiers, acquisition dates, processing parameters and provenance are
retained in metadata and the analytical tables.

Zenodo DOI: 10.5281/zenodo.23041619\n\nNo credentials, Earthdata bearer tokens or passwords are included.
""",encoding="utf-8")

# SHA256 manifest
records=[]
for f in sorted(x for x in REL.rglob("*") if x.is_file()):
    h=hashlib.sha256()
    with open(f,"rb") as inp:
        for chunk in iter(lambda: inp.read(1024*1024),b""):
            h.update(chunk)
    records.append({"path":f.relative_to(REL).as_posix(),"bytes":f.stat().st_size,"sha256":h.hexdigest()})
pd.DataFrame(records).to_csv(REL/"SHA256_MANIFEST.csv",index=False)

zip_path=RELROOT/"SAR_Optical_Perennial_Crops_Italy_v1.0.zip"
if zip_path.exists(): zip_path.unlink()
with zipfile.ZipFile(zip_path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for f in sorted(x for x in REL.rglob("*") if x.is_file()):
        z.write(f,f.relative_to(RELROOT))

print(final.to_string(index=False))
print("\nRelease:",REL)
print("ZIP:",zip_path)
print("ZIP MB:",round(zip_path.stat().st_size/1024**2,2))
print("Manifest files:",len(records))
