# Final technical summary — SAR–Optical Multi-Sensor Monitoring of Perennial Crops in Emilia-Romagna

## Scope
This pilot evaluates whether Sentinel-1 C-band SAR backscatter and interferometric coherence add information to Sentinel-2 optical metrics for structural and seasonal characterization of perennial crops in the Imola–Castel Bolognese–Faenza corridor, Emilia-Romagna, Italy.

The experiment uses 47 official 2023 land-use polygons: 12 vineyards, 12 orchards, 11 olive groves and 12 annual-crop comparison polygons. The primary analytical support is a 20 m inward polygon core. All classification results are exploratory and use leave-one-zone-out geographic validation across Imola, Castel Bolognese and Faenza.

## Data actually processed
- Sentinel-1 GRD archive for provenance.
- Sentinel-1 RTC gamma0 VV/VH for 30 descending path-95 acquisitions in 2023.
- Sentinel-2 L2A on five cloud-screened dates, with scale 0.0001 and offset -0.1 applied before NDVI/NDRE/NDMI/GNDVI.
- Six 12-day Sentinel-1 SLC interferometric coherence pairs centered approximately in February, April, June, August, October and December 2023.
- Official Regione Emilia-Romagna Uso del Suolo 2023 polygons.

The six HyP3 InSAR products use 10x2 looks, 40 m output pixel spacing, Copernicus GLO-30 DEM and descending geometry. Perpendicular baselines range from -225.605 m to +173.304 m, so absolute coherence differences among dates cannot be interpreted as pure phenology.

## Main quantitative results
Using 20 Random Forest seeds with fixed geographic folds:

| Feature representation | Balanced accuracy mean ± SD | Macro-F1 mean ± SD |
|---|---:|---:|
| Optical only | 0.653 ± 0.028 | 0.643 ± 0.027 |
| SAR aligned only | 0.558 ± 0.015 | 0.533 ± 0.016 |
| Optical + aligned SAR | **0.671 ± 0.027** | **0.663 ± 0.028** |
| Seasonal coherence only | 0.357 ± 0.035 | 0.338 ± 0.038 |
| Optical + aligned SAR + seasonal coherence | 0.667 ± 0.028 | 0.657 ± 0.029 |
| Coherence temporal descriptors only | 0.342 ± 0.021 | 0.331 ± 0.019 |
| Optical + aligned SAR + coherence descriptors | 0.671 ± 0.034 | 0.664 ± 0.036 |

The aligned SAR+optical fusion therefore produced a modest average improvement over optical only (+0.018 balanced accuracy), while seasonal coherence did not provide a stable incremental gain.

## SAR temporal representation
Thirty 2023 RTC acquisitions produced 1,410 polygon-date SAR records. Compact full-year SAR descriptors improved standalone SAR balanced accuracy to approximately 0.606, but their fusion with optical features reduced balanced accuracy to approximately 0.620. This indicates that annual aggregation can retain SAR class structure while diluting timing information that matters for multimodal fusion.

A five-date seasonal SAR representation chosen independently from Sentinel-2 dates produced a larger apparent fusion gain (+0.044 balanced accuracy on average), but the more defensible temporally aligned experiment reduced the mean S1/S2 offset to 2.6 days (maximum 4 days) and yielded the smaller +0.018 gain. The aligned result is preferred for interpretation.
## Coherence findings
The June 03–15 pair was first evaluated independently. Median coherence over the 20 m cores was 0.424 for annual crops, 0.384 for orchards, 0.365 for olive groves and 0.364 for vineyards. Class separation was weak (Kruskal-Wallis p=0.690) and remained weak under 0/10/20/30 m buffer sensitivity tests.

The full six-pair series contained exactly 282 records (6 pairs x 47 polygons). Median coherence showed strong seasonal variation, but class separation was generally weak. February gave the smallest unadjusted global p-value (p=0.034), but this did not survive correction for six temporal tests (Bonferroni/FDR-adjusted p=0.204). No seasonal class test remained significant at FDR 0.05.

Adding six raw seasonal coherence features to optical+aligned-SAR changed mean balanced accuracy from 0.671 to 0.667. Across 20 seeds, coherence improved fusion in 9 cases, tied in 2 and worsened it in 9; mean paired effect -0.004.

Replacing the six raw coherence epochs with compact temporal descriptors (mean, standard deviation, minimum, maximum, amplitude and winter-minus-summer contrast) produced essentially zero incremental effect: mean paired balanced-accuracy change +0.0004, with 8 improvements, 1 tie and 11 losses.

Therefore, within this pilot and these six 12-day pairs, interferometric coherence was successfully generated and analyzed but did not add stable crop-class discrimination beyond aligned SAR backscatter and optical metrics.

## Scientific interpretation
The project supports three defensible conclusions:

1. Sentinel-1 RTC backscatter contains complementary information to Sentinel-2 optical indices for this pilot, but the magnitude of the gain depends strongly on temporal representation.
2. Temporally aligned SAR+optical fusion provides a modest, repeatable improvement over optical-only classification in this small geographically held-out sample.
3. Sentinel-1 interferometric coherence is operationally feasible and structurally different from backscatter/optical metrics, but the tested seasonal coherence series does not provide a stable incremental classification gain.

These are exploratory separability results, not claims about yield, crop physiology, causal agronomic response or operational mapping accuracy.

## Reproducibility
The project preserves:
- official land-use source and pilot geometries;
- Sentinel-1 and Sentinel-2 catalog metadata;
- raw GRD provenance and RTC provenance;
- all selected dates/orbits/frames;
- HyP3 job parameters and credit records;
- all six coherence products;
- polygon-level optical, SAR and coherence tables;
- geographic holdout model outputs for repeated seeds;
- scripts, figures and technical documentation.

No unsupported claim of pre-existing SAR expertise is required: this repository documents a real end-to-end SAR/optical workflow executed on public Italian agricultural data.
