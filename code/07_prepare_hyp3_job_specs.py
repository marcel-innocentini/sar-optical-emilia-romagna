from pathlib import Path
import json
import pandas as pd

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
META = BASE / "metadata"

grd = pd.read_csv(META / "sentinel1_grd_pilot_selection.csv")
pairs = pd.read_csv(META / "sentinel1_slc_coherence_candidates.csv")

rtc_jobs = []
for scene in grd["sceneName"]:
    rtc_jobs.append({
        "job_type": "RTC_GAMMA",
        "granule": scene,
        "radiometry": "gamma0",
        "scale": "power",
        "resolution": 20,
        "dem_name": "copernicus",
        "speckle_filter": False,
        "include_inc_map": True,
        "include_dem": False,
        "include_scattering_area": False,
    })
best = pairs.iloc[0]
insar_job = {
    "job_type": "INSAR_GAMMA",
    "reference": best["master_scene"],
    "secondary": best["slave_scene"],
    "temporal_baseline_days": int(best["delta_days"]),
    "looks": "10x2",
    "include_inc_map": True,
    "include_dem": False,
    "include_wrapped_phase": False,
    "include_displacement_maps": False,
    "apply_water_mask": False,
    "phase_filter_parameter": 0.6,
}

spec = {
    "note": "Preparation only. No authenticated HyP3 jobs have been submitted.",
    "rtc_jobs": rtc_jobs,
    "coherence_insar_job": insar_job,
}
(META / "hyp3_job_specs.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
print(json.dumps(spec, indent=2))
