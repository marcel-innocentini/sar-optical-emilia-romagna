# Version 1.1 — EO Data Quality & Processing Validation

Version 1.1 extends the existing SAR–Optical Emilia-Romagna pilot with a traceable EO product-quality and processor-validation workflow. It is not a separate project.

## Added in v1.1

- Sentinel-1 acquisition QA: relative orbit, frame, direction, VV/VH, cadence and gaps.
- RTC gamma0 QA: availability, no-data/valid-pixel support, edge checks, temporal distributions and outliers.
- Sentinel-1 SLC/coherence-pair QA: temporal interval, perpendicular baseline, looks, resolution, coverage and physical-range checks.
- Sentinel-2 QA: SCL/cloud masking, valid support by parcel, cloud/shadow/saturation/no-data checks.
- Sentinel-1 × Sentinel-2 temporal/spatial comparability checks.
- Robust parcel/date anomaly screening based on MAD / robust-z statistics.
- Traceable PASS / WARNING / FAIL classification.
- Controlled Sentinel-2 reprocessing experiments.
- Independent processor replication verification.
- Machine-readable QC outputs and human-readable reporting.

## Final QC summary

- **73 PASS**
- **3 WARNING**
- **0 FAIL**
- **54 parcel-level INVESTIGATE triggers**
- **0 acquisition-wide anomaly flags**

Warnings were associated with:

1. one SLC coherence pair with |perpendicular baseline| = **225.6 m**, above the project's internal 200 m investigation threshold;
2. Sentinel-2 2023-10-10, when **89.4% of pilot parcels** reached at least 80% valid support;
3. one Sentinel-1/Sentinel-2 aligned pair with a **4-day temporal offset**, above the project's internal PASS threshold of at most 3 days.

The anomaly-screening workflow deliberately distinguishes local statistical investigation triggers from product-level failure.

## Processor replication and controlled reprocessing

The stored Sentinel-2 baseline was independently reconstructed using the documented scale/offset, SCL mask and resampling logic. Pixelwise comparison reproduced the baseline exactly across the tested products (**maximum replication RMSE = 0**).

Two controlled processing changes were then tested:

- a stricter SCL mask adding classes 2 and 7 to exclusions, which produced no measurable parcel-median index effect in this dataset;
- nearest-neighbour instead of bilinear resampling for 20 m B05/B11 inputs, which produced measurable differences, with maximum P95 absolute parcel-median change of approximately **0.0099 index units**.

## Scope and limitations

All QC thresholds are transparent project engineering rules for this pilot. They are not ESA mission acceptance specifications. Version 1.1 demonstrates transferable EO product-quality, anomaly-investigation, reprocessing and processor-validation practice; it does not claim prior operational responsibility for ESA Instrument Processing Facilities or Swarm mission instruments.
