from pathlib import Path
import json
import subprocess
import pandas as pd

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
SEL = BASE / "metadata/sentinel1_grd_pilot_selection.csv"
OUT = BASE / "data/raw/sentinel1/grd"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(SEL)
records = []
for row in df.itertuples(index=False):
    dt = pd.to_datetime(row.startTime)
    scene = row.sceneName
    pol_dir = "DV"
    prefix = (
        f"s3://sentinel-s1-l1c/GRD/{dt.year}/{dt.month}/{dt.day}/"
        f"IW/{pol_dir}/{scene}/"
    )
    dest = OUT / scene
    dest.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {scene}")
    cmd = [
        "aws", "s3", "cp", prefix, str(dest),
        "--recursive", "--no-sign-request", "--only-show-errors"
    ]
    subprocess.run(cmd, check=True)
    records.append({"scene": scene, "s3_prefix": prefix, "local": str(dest)})
(BASE / "metadata/sentinel1_grd_download_manifest.json").write_text(
    json.dumps(records, indent=2), encoding="utf-8"
)
print(f"Downloaded {len(records)} Sentinel-1 GRD scenes.")
