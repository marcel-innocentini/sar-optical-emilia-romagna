from pathlib import Path
import argparse
import json
import pandas as pd
import hyp3_sdk

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
PAIRS=pd.read_csv(BASE/"data/processed/ml/candidate_seasonal_coherence_pairs.csv")
OUT=BASE/"data/processed/sentinel1/coherence_seasonal"
OUT.mkdir(parents=True,exist_ok=True)

DONE_MASTER="S1A_IW_SLC__1SDV_20230603T051945_20230603T052012_048817_05DEE7_31E0"
PAIRS=PAIRS[PAIRS["master"]!=DONE_MASTER].copy()

ap=argparse.ArgumentParser()
ap.add_argument("--auth",choices=["password","token"],default="token")
ap.add_argument("--submit",action="store_true")
args=ap.parse_args()

hyp3=hyp3_sdk.HyP3(prompt=args.auth)
credits=hyp3.check_credits()
costs=hyp3.costs()
unit_cost=costs["INSAR_GAMMA"]["cost_table"]["10x2"]
total_cost=int(len(PAIRS)*unit_cost)

print("Remaining credits:",credits)
print("Additional pairs:",len(PAIRS))
print("Unit cost:",unit_cost)
print("Total additional cost:",total_cost)
print(PAIRS[["mid_date","master_time","slave_time"]].to_string(index=False))
status={
    "remaining_credits_before":credits,
    "pairs_to_submit":int(len(PAIRS)),
    "unit_cost":unit_cost,
    "total_cost":total_cost,
    "pairs":PAIRS[["mid_date","master","slave"]].to_dict("records"),
}
(BASE/"metadata/seasonal_coherence_cost_check.json").write_text(
    json.dumps(status,indent=2),encoding="utf-8"
)

if not args.submit:
    print("\nDRY RUN ONLY. No jobs submitted.")
    raise SystemExit(0)

batches=[]
for row in PAIRS.itertuples(index=False):
    name=f"SAR_OPTICAL_ITALY_COH_{pd.to_datetime(row.master_time):%Y%m%d}_{pd.to_datetime(row.slave_time):%Y%m%d}"
    b=hyp3.submit_insar_job(
        granule1=row.master,
        granule2=row.slave,
        name=name,
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
    batches.extend(list(b))
    print("Submitted",name,flush=True)
batch=hyp3_sdk.Batch(batches)
batch=hyp3.watch(batch,timeout=10800,interval=60)
files=batch.download_files(location=OUT)
record={
    "remaining_credits_after":hyp3.check_credits(),
    "downloaded":[str(x) for x in files],
}
(BASE/"metadata/seasonal_coherence_run.json").write_text(
    json.dumps(record,indent=2),encoding="utf-8"
)
print("Downloaded:",len(files))
