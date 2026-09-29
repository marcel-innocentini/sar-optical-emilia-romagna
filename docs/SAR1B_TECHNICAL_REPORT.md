# SAR 1B - EO Data Quality & Processing Validation for Agricultural Monitoring in Emilia-Romagna

**Extension of SAR 1.** Study area: Imola-Castel Bolognese-Faenza corridor, Emilia-Romagna, Italy.

## Purpose

SAR 1B converts the existing agricultural Sentinel-1/Sentinel-2 workflow into an explicit Earth Observation data-quality and processor-validation chain:

**dataset -> quality control -> anomaly investigation -> reprocessing -> validation -> reporting**

The workflow is intentionally traceable. Thresholds are project QC rules documented in metadata/SAR1B_QC_THRESHOLDS.json; they are not represented as ESA mission acceptance specifications.

## Executive QC result

- Final register: **73 PASS, 3 WARNING, 0 FAIL**.
- Sentinel-1 acquisition series: **30** path-95/frame-445 descending VV+VH acquisitions from 2023-01-10 to 2023-12-24.
- RTC QA: **60** polarization rasters; minimum valid fraction **100.000%**; no acquisition-wide anomaly flag.
- SLC/coherence: **6** 12-day pairs. One geometry warning is retained for the February pair because |baseline| = **225.6 m**, above the project 200 m investigation band.
- Sentinel-2: **5** dates. The 2023-10-10 acquisition is retained as WARNING because only **89.4%** of pilot polygons reach 80% valid support and some polygons have zero valid pixels.
- S1 x S2 temporal matching: mean offset **2.6 d**, maximum **4 d**; the 4-day July match is a WARNING under the project <=3 d PASS rule.
- Automated parcel-level anomaly detector generated **54** INVESTIGATE triggers, but **0** acquisition-wide anomaly flags. Parcel anomalies are therefore not automatically treated as product failures.

## Controlled reprocessing / processor verification

The Sentinel-2 index processor was independently re-run from the stored band mosaics and SCL layer using the original scale/offset, cloud-mask logic and bilinear alignment of 20 m bands. Pixelwise comparison with the previously generated products gives a maximum replication RMSE of **0.000e+00**, verifying reproducibility of the baseline processor.

Two controlled parameter changes were then tested:

1. **Strict SCL mask:** adds SCL classes 2 (dark area pixels) and 7 (unclassified) to the exclusion policy while retaining the original bilinear resampling.
2. **20 m resampling variant:** changes B05/B11 alignment from bilinear to nearest-neighbour while retaining the original SCL mask.

The strict-mask experiment produced a worst parcel-level relative valid-pixel change of **0.0%**. The largest 95th-percentile absolute polygon-median change produced by the nearest-neighbour resampling experiment was **0.0099** index units. These results quantify the effect of processing choices rather than assuming processor invariance.

## PASS / WARNING / FAIL items

| product_type   |        product_id | date_or_pair            | status   | reason                                                                                                           |
|:---------------|------------------:|:------------------------|:---------|:-----------------------------------------------------------------------------------------------------------------|
| S1_COHERENCE   | 20230203_20230215 | 20230203_20230215       | WARNING  | |perpendicular baseline|=225.6 m                                                                                 |
| S2_L2A         |          20231010 | 2023-10-10              | WARNING  | 89.4% polygons >=80% valid; minimum=0.0%                                                                         |
| S1_S2_PAIR     | 20230721_20230717 | 2023-07-21 / 2023-07-17 | WARNING  | temporal offset=4 d; native CRS differs (S1 EPSG:32633 vs S2 EPSG:32632); comparison uses common polygon support |

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
