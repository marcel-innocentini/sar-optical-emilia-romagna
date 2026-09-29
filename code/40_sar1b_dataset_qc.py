from pathlib import Path
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from shapely.geometry import box

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
QC = BASE / "data/processed/qc"
OUT = BASE / "outputs/qc"
QC.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

STATUS_RANK = {"PASS": 0, "WARNING": 1, "FAIL": 2}
def worst_status(items):
    items = list(items)
    return max(items, key=lambda x: STATUS_RANK.get(x, -1)) if items else "PASS"

def robust_z(x):
    s = pd.Series(x, dtype=float)
    med = s.median()
    mad = (s - med).abs().median()
    if not np.isfinite(mad) or mad == 0:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return 0.67448975 * (s - med) / mad

def product_row(product_type, product_id, date_or_pair, status, reason, **kwargs):
    d = {"product_type": product_type, "product_id": product_id,
         "date_or_pair": date_or_pair, "status": status, "reason": reason}
    d.update(kwargs)
    return d

# Thresholds are project QC rules, not ESA mission acceptance specifications.
thresholds = {
    "s1_expected_relative_orbit": 95,
    "s1_expected_frame": 445,
    "s1_expected_direction": "DESCENDING",
    "s1_expected_polarizations": "VV+VH",
    "s1_nominal_repeat_days": 12.0,
    "rtc_warning_invalid_fraction": 0.005,
    "rtc_fail_invalid_fraction": 0.05,
    "rtc_warning_robust_z": 3.5,
    "coherence_warning_baseline_abs_m": 200.0,
    "coherence_fail_baseline_abs_m": 300.0,
    "coherence_warning_valid_fraction": 0.80,
    "coherence_fail_valid_fraction": 0.50,
    "s2_polygon_pass_valid_fraction": 0.80,
    "s2_date_pass_fraction_polygons": 0.90,
    "s2_date_fail_fraction_polygons": 0.70,
    "cross_sensor_pass_delta_days": 3,
    "cross_sensor_warning_delta_days": 6,
    "cross_sensor_fail_footprint_coverage": 0.95,
}
(BASE / "metadata/SAR1B_QC_THRESHOLDS.json").write_text(
    json.dumps(thresholds, indent=2), encoding="utf-8")

register = []

# ---------------------------------------------------------------------
# Sentinel-1 acquisition QA
# ---------------------------------------------------------------------
cat = pd.read_csv(BASE / "metadata/sentinel1_grd_2023_catalog.csv")
sel = cat[
    (cat["pathNumber"] == thresholds["s1_expected_relative_orbit"]) &
    (cat["frameNumber"] == thresholds["s1_expected_frame"]) &
    (cat["flightDirection"] == thresholds["s1_expected_direction"])
].copy()
sel["startTime"] = pd.to_datetime(sel["startTime"], utc=True)
sel = sel.sort_values("startTime").drop_duplicates("sceneName")
sel["delta_prev_days"] = sel["startTime"].diff().dt.total_seconds() / 86400.0
s1_rows = []
for _, r in sel.iterrows():
    reasons, status = [], "PASS"
    if str(r["polarization"]) != thresholds["s1_expected_polarizations"]:
        status = "FAIL"; reasons.append(f"polarization={r['polarization']}")
    if pd.notna(r["delta_prev_days"]):
        delta = float(r["delta_prev_days"])
        if abs(delta - thresholds["s1_nominal_repeat_days"]) > 0.25:
            status = worst_status([status, "WARNING"])
            reasons.append(f"repeat interval {delta:.2f} d")
    if not reasons:
        reasons = ["orbit/frame/direction/polarizations and cadence consistent"]
    s1_rows.append({
        "date": r["startTime"].date().isoformat(),
        "scene": r["sceneName"], "orbit": int(r["orbit"]),
        "relative_orbit": int(r["pathNumber"]), "frame": int(r["frameNumber"]),
        "direction": r["flightDirection"], "polarization": r["polarization"],
        "delta_prev_days": r["delta_prev_days"], "status": status,
        "reason": "; ".join(reasons)
    })
    register.append(product_row("S1_ACQUISITION", r["sceneName"],
                                r["startTime"].date().isoformat(), status,
                                "; ".join(reasons)))
s1_qc = pd.DataFrame(s1_rows)
s1_qc.to_csv(QC / "s1_acquisition_qc.csv", index=False)

# ---------------------------------------------------------------------
# Sentinel-1 RTC QA
# ---------------------------------------------------------------------
rtc_root = BASE / "data/processed/sentinel1/rtc_2023_full"
rtc_rows = []
for date_dir in sorted(p for p in rtc_root.glob("20*") if p.is_dir()):
    for pol in ("VV", "VH"):
        files = sorted(date_dir.glob(f"*_{pol}_gamma0_rtc.tif"))
        if not files:
            rtc_rows.append({"date": date_dir.name, "polarization": pol,
                             "status": "FAIL", "reason": "missing raster"})
            continue
        fp = files[0]
        with rasterio.open(fp) as src:
            a = src.read(1, masked=True).astype("float64")
            data = a.data
            good = (~np.ma.getmaskarray(a)) & np.isfinite(data) & (data > 0)
            valid_fraction = float(good.mean())
            vals = data[good]
            k = min(5, max(1, min(good.shape) // 20))
            edge = np.zeros(good.shape, bool)
            edge[:k, :] = True; edge[-k:, :] = True
            edge[:, :k] = True; edge[:, -k:] = True
            edge_valid = float(good[edge].mean())
            interior_valid = float(good[~edge].mean())
            rtc_rows.append({
                "date": date_dir.name, "polarization": pol, "file": fp.name,
                "crs": str(src.crs), "resolution_m": float(abs(src.res[0])),
                "width": src.width, "height": src.height, "nodata": src.nodata,
                "valid_fraction": valid_fraction, "edge_valid_fraction": edge_valid,
                "interior_valid_fraction": interior_valid,
                "p01_db": float(10*np.log10(np.percentile(vals, 1))),
                "median_db": float(10*np.log10(np.median(vals))),
                "p99_db": float(10*np.log10(np.percentile(vals, 99))),
            })
rtc = pd.DataFrame(rtc_rows)
for pol in ("VV", "VH"):
    ix = rtc["polarization"].eq(pol) & rtc["median_db"].notna()
    rtc.loc[ix, "median_robust_z"] = robust_z(rtc.loc[ix, "median_db"]).values

for i, r in rtc.iterrows():
    status, reasons = "PASS", []
    if pd.isna(r.get("valid_fraction")):
        status = "FAIL"; reasons.append("missing/unreadable raster")
    else:
        invalid = 1.0 - float(r["valid_fraction"])
        if invalid >= thresholds["rtc_fail_invalid_fraction"]:
            status = "FAIL"; reasons.append(f"invalid fraction={invalid:.3%}")
        elif invalid >= thresholds["rtc_warning_invalid_fraction"]:
            status = "WARNING"; reasons.append(f"invalid fraction={invalid:.3%}")
        edge_loss = float(r["interior_valid_fraction"] - r["edge_valid_fraction"])
        if edge_loss > 0.01:
            status = worst_status([status, "WARNING"])
            reasons.append(f"edge validity lower by {edge_loss:.3%}")
        if abs(float(r.get("median_robust_z", 0))) >= thresholds["rtc_warning_robust_z"]:
            status = worst_status([status, "WARNING"])
            reasons.append(f"date-level median robust-z={r['median_robust_z']:.2f}")
    if not reasons:
        reasons = ["complete raster; positive finite gamma0; no edge validity loss; temporal distribution consistent"]
    rtc.loc[i, "status"] = status
    rtc.loc[i, "reason"] = "; ".join(reasons)
rtc.to_csv(QC / "s1_rtc_qc.csv", index=False)

rtc_date_rows = []
for date, g in rtc.groupby("date"):
    status = worst_status(g["status"])
    reasons = sorted(set(g.loc[g["status"] != "PASS", "reason"].tolist()))
    reason = "; ".join(reasons) if reasons else "VV/VH RTC products passed grid, validity and distribution checks"
    rtc_date_rows.append({"date": date, "status": status, "reason": reason})
    register.append(product_row("S1_RTC", f"RTC_{date}", date, status, reason))
pd.DataFrame(rtc_date_rows).to_csv(QC / "s1_rtc_date_qc.csv", index=False)

# ---------------------------------------------------------------------
# Sentinel-1 SLC/coherence pair QA
# ---------------------------------------------------------------------
coh_meta = pd.read_csv(BASE / "metadata/seasonal_coherence_product_metadata.csv", dtype={"master_date": str, "slave_date": str})
coh_ts = pd.read_csv(BASE / "data/processed/seasonal_coherence_polygon_timeseries.csv")
coh_rows = []
for _, m in coh_meta.iterrows():
    master = pd.to_datetime(str(m["master_date"]))
    slave = pd.to_datetime(str(m["slave_date"]))
    pair_id = f"{master:%Y%m%d}_{slave:%Y%m%d}"
    g = coh_ts[coh_ts["pair_id"] == pair_id].copy()
    expected = g["core_area_ha"] * 10000.0 / (float(m["output_resolution_m"])**2)
    valid_frac = np.minimum(1.0, g["n_valid"] / expected.replace(0, np.nan))
    status, reasons = "PASS", []
    delta = (slave - master).days
    if delta != 12:
        status = worst_status([status, "WARNING"])
        reasons.append(f"temporal interval={delta} d")
    ab = abs(float(m["baseline_m"]))
    if ab >= thresholds["coherence_fail_baseline_abs_m"]:
        status = "FAIL"; reasons.append(f"|perpendicular baseline|={ab:.1f} m")
    elif ab >= thresholds["coherence_warning_baseline_abs_m"]:
        status = worst_status([status, "WARNING"])
        reasons.append(f"|perpendicular baseline|={ab:.1f} m")
    med_valid = float(valid_frac.median()) if len(valid_frac) else np.nan
    if np.isfinite(med_valid):
        if med_valid < thresholds["coherence_fail_valid_fraction"]:
            status = "FAIL"; reasons.append(f"median polygon valid fraction={med_valid:.2f}")
        elif med_valid < thresholds["coherence_warning_valid_fraction"]:
            status = worst_status([status, "WARNING"])
            reasons.append(f"median polygon valid fraction={med_valid:.2f}")
    bad_range = ((g["coherence_median"] < 0) | (g["coherence_median"] > 1)).any()
    if bad_range:
        status = "FAIL"; reasons.append("coherence outside [0,1]")
    if not reasons:
        reasons = ["12-day pair; baseline within project QC band; coherence range/coverage valid"]
    coh_rows.append({
        "pair_id": pair_id, "master_date": master.date().isoformat(),
        "slave_date": slave.date().isoformat(), "delta_days": delta,
        "baseline_m": float(m["baseline_m"]), "abs_baseline_m": ab,
        "output_resolution_m": float(m["output_resolution_m"]),
        "range_looks": int(m["range_looks"]), "azimuth_looks": int(m["azimuth_looks"]),
        "median_polygon_valid_fraction": med_valid,
        "coherence_median_all_polygons": float(g["coherence_median"].median()),
        "coherence_p10_all_polygons": float(g["coherence_median"].quantile(.10)),
        "coherence_p90_all_polygons": float(g["coherence_median"].quantile(.90)),
        "status": status, "reason": "; ".join(reasons)
    })
    register.append(product_row("S1_COHERENCE", pair_id, pair_id, status, "; ".join(reasons)))
coh_qc = pd.DataFrame(coh_rows)
coh_qc.to_csv(QC / "s1_coherence_pair_qc.csv", index=False)

# ---------------------------------------------------------------------
# Sentinel-2 QA
# ---------------------------------------------------------------------
pilots = gpd.read_file(BASE / "data/processed/pilot_polygons_core20m.gpkg", layer="core20m")
s2_root = BASE / "data/processed/sentinel2"
s2_poly_rows, s2_date_rows = [], []
bad_baseline = {0, 1, 3, 8, 9, 10, 11}
for date_dir in sorted(p for p in s2_root.glob("20*") if p.is_dir()):
    date = pd.to_datetime(date_dir.name, format="%Y%m%d").date().isoformat()
    scl_path = date_dir / f"{date_dir.name}_scl.tif"
    if not scl_path.exists():
        s2_date_rows.append({"date": date, "status": "FAIL", "reason": "missing SCL mosaic"})
        register.append(product_row("S2_L2A", date_dir.name, date, "FAIL", "missing SCL mosaic"))
        continue
    with rasterio.open(scl_path) as src:
        pg = pilots.to_crs(src.crs)
        for _, r in pg.iterrows():
            ma, _ = mask(src, [r.geometry], crop=True, filled=False)
            vals = ma[0].compressed().astype("int16")
            total = len(vals)
            if total == 0:
                frac_valid = 0.0; cloud = shadow = sat = nod = dark = unclass = np.nan
            else:
                frac_valid = float((~np.isin(vals, list(bad_baseline))).mean())
                cloud = float(np.isin(vals, [8, 9, 10]).mean())
                shadow = float((vals == 3).mean())
                sat = float((vals == 1).mean())
                nod = float((vals == 0).mean())
                dark = float((vals == 2).mean())
                unclass = float((vals == 7).mean())
            pstatus = "PASS" if frac_valid >= thresholds["s2_polygon_pass_valid_fraction"] else ("WARNING" if frac_valid >= 0.50 else "FAIL")
            s2_poly_rows.append({
                "date": date, "pilot_id": r["pilot_id"], "class4": r["class4"], "zone": r["zone"],
                "n_scl_pixels": total, "valid_fraction": frac_valid,
                "cloud_fraction": cloud, "shadow_fraction": shadow,
                "saturated_defective_fraction": sat, "nodata_fraction": nod,
                "dark_area_fraction": dark, "unclassified_fraction": unclass,
                "status": pstatus
            })
    gd = pd.DataFrame([x for x in s2_poly_rows if x["date"] == date])
    frac_pass = float((gd["valid_fraction"] >= thresholds["s2_polygon_pass_valid_fraction"]).mean())
    if frac_pass >= thresholds["s2_date_pass_fraction_polygons"]:
        status = "PASS"
    elif frac_pass < thresholds["s2_date_fail_fraction_polygons"]:
        status = "FAIL"
    else:
        status = "WARNING"
    min_valid = float(gd["valid_fraction"].min())
    reasons = [f"{frac_pass:.1%} polygons >=80% valid; minimum={min_valid:.1%}"]
    if gd["saturated_defective_fraction"].fillna(0).max() > 0:
        reasons.append(f"SCL saturated/defective max={gd['saturated_defective_fraction'].max():.2%}")
    reason = "; ".join(reasons)
    s2_date_rows.append({"date": date, "fraction_polygons_pass": frac_pass,
                         "min_valid_fraction": min_valid,
                         "median_valid_fraction": float(gd["valid_fraction"].median()),
                         "status": status, "reason": reason})
    register.append(product_row("S2_L2A", date_dir.name, date, status, reason))
s2_poly = pd.DataFrame(s2_poly_rows)
s2_date = pd.DataFrame(s2_date_rows)
s2_poly.to_csv(QC / "s2_polygon_qc.csv", index=False)
s2_date.to_csv(QC / "s2_date_qc.csv", index=False)

# ---------------------------------------------------------------------
# Cross-sensor QA: temporal alignment, footprint, native grids
# ---------------------------------------------------------------------
aoi = gpd.read_file(BASE / "data/processed/aoi_corridor.gpkg", layer="aoi")
aoi_area = float(aoi.geometry.area.sum())
s1_dates = pd.DatetimeIndex(pd.to_datetime(s1_qc["date"]).sort_values().unique())
cross_rows = []
for _, r in s2_date.iterrows():
    od = pd.Timestamp(r["date"])
    sd = min(s1_dates, key=lambda x: abs(x - od))
    delta = abs((sd - od).days)
    s1fp = next((rtc_root / f"{sd:%Y%m%d}").glob("*_VV_gamma0_rtc.tif"))
    s2fp = s2_root / f"{od:%Y%m%d}" / f"{od:%Y%m%d}_ndvi.tif"
    with rasterio.open(s1fp) as a, rasterio.open(s2fp) as b:
        ga = gpd.GeoSeries([box(*a.bounds)], crs=a.crs).to_crs(aoi.crs).iloc[0]
        gb = gpd.GeoSeries([box(*b.bounds)], crs=b.crs).to_crs(aoi.crs).iloc[0]
        cov_a = float(aoi.geometry.union_all().intersection(ga).area / aoi_area)
        cov_b = float(aoi.geometry.union_all().intersection(gb).area / aoi_area)
        cov_common = float(aoi.geometry.union_all().intersection(ga).intersection(gb).area / aoi_area)
        native_crs_match = str(a.crs) == str(b.crs)
        res_s1, res_s2 = abs(a.res[0]), abs(b.res[0])
    status, reasons = "PASS", []
    if cov_common < thresholds["cross_sensor_fail_footprint_coverage"]:
        status = "FAIL"; reasons.append(f"common AOI footprint={cov_common:.1%}")
    if delta > thresholds["cross_sensor_warning_delta_days"]:
        status = "FAIL"; reasons.append(f"temporal offset={delta} d")
    elif delta > thresholds["cross_sensor_pass_delta_days"]:
        status = worst_status([status, "WARNING"]); reasons.append(f"temporal offset={delta} d")
    if not native_crs_match:
        reasons.append("native CRS differs (S1 EPSG:32633 vs S2 EPSG:32632); comparison uses common polygon support")
    if not reasons:
        reasons.append("temporal offset <=3 d; AOI footprints complete; 10 m nominal grids")
    cross_rows.append({
        "s2_date": od.date().isoformat(), "s1_date": sd.date().isoformat(),
        "delta_days": delta, "s1_resolution_m": res_s1, "s2_resolution_m": res_s2,
        "native_crs_match": native_crs_match, "s1_aoi_coverage": cov_a,
        "s2_aoi_coverage": cov_b, "common_aoi_coverage": cov_common,
        "status": status, "reason": "; ".join(reasons)
    })
    register.append(product_row("S1_S2_PAIR", f"{sd:%Y%m%d}_{od:%Y%m%d}",
                                f"{sd.date()} / {od.date()}", status, "; ".join(reasons)))
cross = pd.DataFrame(cross_rows)
cross.to_csv(QC / "cross_sensor_qc.csv", index=False)

reg = pd.DataFrame(register)
reg.to_csv(QC / "product_qc_register_base.csv", index=False)
print("SAR 1B dataset QC complete")
print(reg["status"].value_counts().to_string())
print("Outputs:", QC)
