from pathlib import Path
import shutil, hashlib, csv, zipfile

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
SRC=BASE/"release/SAR_Optical_Perennial_Crops_Italy_v1.0"
DST=BASE/"release/SAR_Optical_Perennial_Crops_Italy_v1.1"
ZIP=BASE/"release/SAR_Optical_Perennial_Crops_Italy_v1.1.zip"

if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC,DST)

for name in [
    "40_sar1b_dataset_qc.py",
    "41_sar1b_anomaly_detection.py",
    "42_sar1b_reprocessing_validation.py",
    "43_sar1b_reporting.py",
    "44_finalize_sar1b_release.py"]:
    shutil.copy2(BASE/"code"/name,DST/"code"/name)

qdst=DST/"data/processed/qc"
qdst.mkdir(parents=True,exist_ok=True)
for p in sorted((BASE/"data/processed/qc").glob("*.csv")):
    shutil.copy2(p,qdst/p.name)
for p in sorted((BASE/"data/processed/qc").glob("*.json")):
    shutil.copy2(p,qdst/p.name)

fdst=DST/"outputs/figures_qc"
fdst.mkdir(parents=True,exist_ok=True)
for p in sorted((BASE/"outputs/figures_qc").glob("*.png")):
    shutil.copy2(p,fdst/p.name)

shutil.copy2(BASE/"docs/SAR1B_TECHNICAL_REPORT.md",DST/"docs/SAR1B_TECHNICAL_REPORT.md")
shutil.copy2(BASE/"metadata/SAR1B_QC_THRESHOLDS.json",DST/"metadata/SAR1B_QC_THRESHOLDS.json")
shutil.copy2(BASE/"release/Agropixel_SAR1B_EO_Data_Quality_Processing_Validation_v1.1.pdf",
             DST/"docs/Agropixel_SAR1B_EO_Data_Quality_Processing_Validation_v1.1.pdf")

readme="""# SAR 1B - EO Data Quality & Processing Validation

SAR 1B is an extension of the SAR-Optical Emilia-Romagna pilot archived at DOI 10.5281/zenodo.23041619.

It adds an explicit operational-style validation chain:

dataset -> quality control -> anomaly investigation -> reprocessing -> validation -> reporting

The extension includes acquisition QA, Sentinel-1 RTC QA, SLC/coherence-pair QA, Sentinel-2 cloud/validity QA, S1-S2 comparability checks, robust anomaly detection, controlled Sentinel-2 reprocessing, baseline processor replication, PASS/WARNING/FAIL traceability, and automatic QC reporting.

Important: project QC thresholds are transparent engineering rules for this pilot and are not ESA mission acceptance specifications. SAR 1B does not claim prior operation of an ESA Instrument Processing Facility.
"""
(DST/"README_SAR1B.md").write_text(readme,encoding="utf-8")

manifest=[]
for p in sorted(x for x in DST.rglob("*") if x.is_file() and x.name!="SHA256_MANIFEST.csv"):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    manifest.append([p.relative_to(DST).as_posix(),h.hexdigest(),p.stat().st_size])
with open(DST/"SHA256_MANIFEST.csv","w",newline="",encoding="utf-8") as f:
    w=csv.writer(f); w.writerow(["relative_path","sha256","bytes"]); w.writerows(manifest)

if ZIP.exists(): ZIP.unlink()
with zipfile.ZipFile(ZIP,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(x for x in DST.rglob("*") if x.is_file()):
        z.write(p,p.relative_to(DST.parent))
print("Release:",DST)
print("ZIP:",ZIP)
print("Files:",sum(1 for x in DST.rglob("*") if x.is_file()))
print("ZIP MB:",round(ZIP.stat().st_size/1024/1024,2))
