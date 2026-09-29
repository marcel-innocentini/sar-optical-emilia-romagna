# SAR–Optical Multi-Sensor Monitoring of Perennial Crops in Emilia-Romagna, Italy

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23041618.svg)](https://doi.org/10.5281/zenodo.23041618)

A reproducible agricultural remote-sensing pilot integrating **Sentinel-1 C-band SAR**, **Sentinel-2 optical imagery**, and **Sentinel-1 SLC interferometric coherence** over the Imola–Castel Bolognese–Faenza corridor in Emilia-Romagna, Italy.

**Author:** Marcel de Mello Innocentini — Agropixel  
**ORCID:** 0009-0006-2409-0946  
**Version:** 1.1
**Canonical all-versions archive:** https://doi.org/10.5281/zenodo.23041618
**Version 1.0 DOI:** https://doi.org/10.5281/zenodo.23041619

![Study area](figures/study_area_map.png)

## Version 1.1 — EO Data Quality & Processing Validation

Version 1.1 extends the same Emilia-Romagna pilot with a dedicated, traceable QA/QC and processor-validation layer. It is **not a separate project**.

The extension follows the operational-style chain:

> **dataset → quality control → anomaly investigation → reprocessing → validation → reporting**

It audits **30 Sentinel-1 RTC acquisitions**, **six 12-day Sentinel-1 SLC coherence pairs**, and **five Sentinel-2 L2A dates**. It adds acquisition/product QA, no-data and valid-support checks, cross-sensor temporal/spatial comparability, robust anomaly screening, PASS/WARNING/FAIL traceability, controlled reprocessing, independent processor replication verification, and automated reporting in Python.

Final project-QC status: **73 PASS / 3 WARNING / 0 FAIL**. Robust anomaly screening generated **54 parcel-level INVESTIGATE triggers** and **0 acquisition-wide anomaly flags**; local statistical anomalies are intentionally not treated automatically as product failures.

The documented Sentinel-2 baseline was reconstructed independently from the stored bands using the same scale/offset, SCL mask and resampling logic. Pixelwise comparison reproduced the baseline exactly across the tested products (**maximum replication RMSE = 0**). Controlled reprocessing then tested a stricter SCL mask and nearest-neighbour versus bilinear resampling for 20 m bands. The stricter mask produced no measurable parcel-median index effect in this dataset, while the resampling change produced measurable differences, with maximum P95 absolute parcel-median change of approximately **0.0099 index units**.

See [Version 1.1 release notes](docs/RELEASE_NOTES_v1.1.md), the [SAR 1B technical report](docs/SAR1B_TECHNICAL_REPORT.md), and the [PDF technical report](docs/Agropixel_SAR1B_EO_Data_Quality_Processing_Validation_v1.1.pdf).

> **Scope note:** QC thresholds are transparent engineering rules for this pilot, not ESA mission acceptance specifications. Version 1.1 demonstrates transferable EO product-quality, anomaly-investigation, reprocessing and processor-validation practice; it does not claim prior operational responsibility for ESA Instrument Processing Facilities or Swarm mission instruments.

## Objective

The pilot asks:

> **How much does C-band SAR add to Sentinel-2 optical information for structural and seasonal characterization of perennial crops?**

The analytical sample contains **47 official 2023 land-use polygons**: 12 vineyards, 12 orchards, 11 olive groves, and 12 annual-crop comparison polygons.

## Data actually processed

| Source | Representation | Scope |
|---|---|---:|
| Sentinel-1 | RTC gamma0 VV/VH | 30 acquisitions in 2023 |
| Sentinel-1 | SLC interferometric coherence | 6 twelve-day pairs |
| Sentinel-2 | L2A optical indices | 5 dates |
| Regione Emilia-Romagna | Uso del Suolo 2023 | 47 pilot polygons |
Optical features include **NDVI, NDRE, NDMI, and GNDVI**. SAR features include **VV, VH, VH/VV**, full-year temporal descriptors, and SLC-derived coherence.

## Processing principles

- Quantitative SAR analysis uses **RTC gamma0**, not raw GRD digital numbers.
- SAR polygon means are aggregated in **linear power** and converted to dB afterward.
- Sentinel-2 reflectance scaling and offset are applied **before** index calculation.
- The primary spatial support is a **20 m inward polygon core**.
- Classification uses **leave-one-zone-out geographic validation** across Imola, Castel Bolognese, and Faenza.
- Algorithmic stability is evaluated over **20 Random Forest seeds** with fixed geographic folds.
- Results are exploratory; no yield, physiology, causal agronomic, or operational crop-mapping claims are made.

## Main result

![Final model comparison](figures/final_model_comparison.png)

| Representation | Balanced accuracy (mean ± SD) | Macro-F1 (mean ± SD) |
|---|---:|---:|
| Optical only | 0.653 ± 0.028 | 0.643 ± 0.027 |
| Aligned SAR only | 0.558 ± 0.015 | 0.533 ± 0.016 |
| **Optical + aligned SAR** | **0.671 ± 0.027** | **0.663 ± 0.028** |
| Full-year SAR descriptors | 0.606 ± 0.014 | 0.579 ± 0.016 |

Temporally aligned Sentinel-1/Sentinel-2 fusion produced a **modest but repeatable improvement** over optical-only classification.

## Interferometric coherence

Six 12-day SLC pairs were processed through **ASF HyP3/GAMMA** using 10×2 looks and 40 m output spacing.
![Seasonal coherence profiles](figures/seasonal_coherence_profiles.png)

![Coherence validation](figures/seasonal_coherence_validation.png)

Coherence was technically successful but did **not** provide a stable incremental classification gain. Adding six seasonal coherence features changed mean balanced accuracy from **0.671 to 0.667**. Compact temporal coherence descriptors produced **0.6715**, effectively identical to fusion without coherence.

Perpendicular baselines varied from approximately **−225.6 m to +173.3 m**, so absolute differences among seasonal coherence pairs are not interpreted as pure phenology.

## Repository structure

```text
code/          processing, extraction, validation, QC and reporting scripts
data/          compact polygon-level analytical and QC tables
metadata/      scene catalogues, processing parameters, thresholds and provenance
figures/       main maps and scientific result figures
figures_qc/    QA/QC, availability, support and reprocessing figures
docs/          technical summaries, release notes and reports
```

Large raw and derived satellite rasters are **not duplicated** in this repository. Scene identifiers, acquisition dates, orbit geometry, processing parameters, and analytical outputs are retained so the workflow can be reproduced from public sources.

## Reproducibility

The canonical all-versions Zenodo archive is:

**https://doi.org/10.5281/zenodo.23041618**

Version 1.0 is archived at **https://doi.org/10.5281/zenodo.23041619**. The v1.1 version-specific DOI will be added here after Zenodo archival publication.

## Citation

Until the v1.1 version-specific DOI is minted, cite the project through the canonical all-versions DOI:

> Innocentini, M. de M. (2026). *SAR–Optical Multi-Sensor Monitoring of Perennial Crops in Emilia-Romagna, Italy* (Version 1.1). Zenodo. https://doi.org/10.5281/zenodo.23041618

A machine-readable citation is provided in [CITATION.cff](CITATION.cff).

## Licenses

- Original source code: **MIT License**
- Original documentation, figures, and technical material: **CC BY 4.0**
- Third-party datasets and satellite products remain subject to their respective source licenses.

## Scope

This repository documents **hands-on SAR processing and interpretation in agriculture**, including Sentinel-1 RTC backscatter, VV/VH analysis, SLC-derived interferometric coherence, Sentinel-2 optical processing, temporal feature engineering, quality control, anomaly investigation, controlled reprocessing, processor replication, SAR–optical fusion, and geographic validation.

Negative results are retained where a tested representation or processing change did not produce a measurable improvement.
