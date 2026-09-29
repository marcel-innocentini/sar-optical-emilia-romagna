from pathlib import Path
import argparse
import json
import hyp3_sdk

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
OUT = BASE / "data/processed/sentinel1/coherence"
OUT.mkdir(parents=True, exist_ok=True)

MASTER = "S1A_IW_SLC__1SDV_20230603T051945_20230603T052012_048817_05DEE7_31E0"
SLAVE  = "S1A_IW_SLC__1SDV_20230615T051946_20230615T052013_048992_05E43B_5133"

ap = argparse.ArgumentParser()
ap.add_argument("--auth", choices=["password","token"], default="token",
                help="Prompt mode; credentials are not written to disk.")
ap.add_argument("--submit", action="store_true",
                help="Actually submit the HyP3 InSAR job. Default is dry-run.")
args = ap.parse_args()

hyp3 = hyp3_sdk.HyP3(prompt=args.auth)
credits = hyp3.check_credits()
costs = hyp3.costs()
print("Remaining credits:", credits)
print("Job cost table:")
print(json.dumps(costs, indent=2))
params = dict(
    granule1=MASTER,
    granule2=SLAVE,
    name="SAR_OPTICAL_ITALY_COH_20230603_20230615",
    include_look_vectors=False,
    include_los_displacement=False,
    include_inc_map=True,
    looks="10x2",
    include_dem=False,
    include_wrapped_phase=False,
    apply_water_mask=False,
    include_displacement_maps=False,
    phase_filter_parameter=0.6,
)

print("\nSelected pair:")
print(MASTER)
print(SLAVE)
print("Temporal baseline: 12 days")
print("Parameters:")
print(json.dumps(params, indent=2))

auth_status = {
    "status": "authenticated_dry_run" if not args.submit else "authenticated_submit_requested",
    "remaining_credits": credits,
    "cost_table": costs,
    "master": MASTER,
    "slave": SLAVE,
    "temporal_baseline_days": 12,
    "parameters": params,
}
(BASE / "metadata/hyp3_auth_cost_check.json").write_text(
    json.dumps(auth_status, indent=2), encoding="utf-8"
)

if not args.submit:
    print("\nDRY RUN ONLY. Re-run with --submit after reviewing credits/cost.")
    raise SystemExit(0)

batch = hyp3.submit_insar_job(**params)
print("Submitted:", batch)
batch = hyp3.watch(batch)
print("Completed:", batch)
files = batch.download_files(location=OUT)
print("Downloaded outputs:")
for f in files:
    print(f)

record = {
    "master": MASTER,
    "slave": SLAVE,
    "temporal_baseline_days": 12,
    "parameters": params,
    "credits_after_submission_check": hyp3.check_credits(),
    "downloaded": [str(x) for x in files],
}
(BASE / "metadata/hyp3_coherence_run.json").write_text(
    json.dumps(record, indent=2), encoding="utf-8"
)
