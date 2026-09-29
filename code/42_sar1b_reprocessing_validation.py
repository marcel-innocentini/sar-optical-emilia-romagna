from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import geometry_mask
from rasterio.warp import reproject, Resampling

BASE=Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
S2=BASE/"data/processed/sentinel2"
QC=BASE/"data/processed/qc"
EX=QC/"reprocessing_example"
QC.mkdir(parents=True,exist_ok=True); EX.mkdir(parents=True,exist_ok=True)
PILOTS=gpd.read_file(BASE/"data/processed/pilot_polygons_core20m.gpkg",layer="core20m")
SCALE=0.0001; OFFSET=-0.1
BAD_BASE=np.array([0,1,3,8,9,10,11],dtype=np.int16)
BAD_STRICT=np.array([0,1,2,3,7,8,9,10,11],dtype=np.int16)

def align(path,profile,resampling):
    with rasterio.open(path) as src:
        out=np.empty((profile["height"],profile["width"]),dtype=np.float32)
        reproject(source=src.read(1),destination=out,src_transform=src.transform,
            src_crs=src.crs,dst_transform=profile["transform"],dst_crs=profile["crs"],
            resampling=resampling)
    return out

def write_float(path,arr,profile):
    p=profile.copy()
    p.update(dtype="float32",nodata=-9999.0,count=1,compress="deflate",tiled=True)
    with rasterio.open(path,"w",**p) as dst:
        dst.write(np.where(np.isfinite(arr),arr,-9999.0).astype("float32"),1)

rep_rows=[]; poly_rows=[]
for dd in sorted(p for p in S2.glob("20*") if p.is_dir()):
    d=dd.name
    with rasterio.open(dd/f"{d}_nir.tif") as src:
        profile=src.profile.copy(); nir_dn=src.read(1).astype("float32")
    with rasterio.open(dd/f"{d}_red.tif") as src: red_dn=src.read(1).astype("float32")
    with rasterio.open(dd/f"{d}_green.tif") as src: green_dn=src.read(1).astype("float32")
    re_bil=align(dd/f"{d}_rededge1.tif",profile,Resampling.bilinear)
    sw_bil=align(dd/f"{d}_swir16.tif",profile,Resampling.bilinear)
    re_near=align(dd/f"{d}_rededge1.tif",profile,Resampling.nearest)
    sw_near=align(dd/f"{d}_swir16.tif",profile,Resampling.nearest)
    scl=align(dd/f"{d}_scl.tif",profile,Resampling.nearest).astype("int16")

    nir=nir_dn*SCALE+OFFSET; red=red_dn*SCALE+OFFSET; green=green_dn*SCALE+OFFSET
    re1=re_bil*SCALE+OFFSET; sw=sw_bil*SCALE+OFFSET
    re1n=re_near*SCALE+OFFSET; swn=sw_near*SCALE+OFFSET
    zero=(nir_dn==0)|(red_dn==0)|(green_dn==0)|(re_bil==0)|(sw_bil==0)
    bad0=np.isin(scl,BAD_BASE)|zero
    bads=np.isin(scl,BAD_STRICT)|zero
    eps=1e-6
    base={
        "ndvi":(nir-red)/(nir+red+eps),
        "gndvi":(nir-green)/(nir+green+eps),
        "ndre":(nir-re1)/(nir+re1+eps),
        "ndmi":(nir-sw)/(nir+sw+eps)}
    strict={k:v.copy() for k,v in base.items()}
    nearest={
        "ndre":(nir-re1n)/(nir+re1n+eps),
        "ndmi":(nir-swn)/(nir+swn+eps)}
    for k in base:
        base[k][bad0|~np.isfinite(base[k])]=np.nan
        strict[k][bads|~np.isfinite(strict[k])]=np.nan
    for k in nearest:
        nearest[k][bad0|~np.isfinite(nearest[k])]=np.nan

    # Processor replication: regenerate the published baseline and compare pixelwise.
    for k,a in base.items():
        with rasterio.open(dd/f"{d}_{k}.tif") as src:
            old=src.read(1).astype("float32"); old[old==src.nodata]=np.nan
        common=np.isfinite(a)&np.isfinite(old)
        diff=a[common]-old[common]
        rep_rows.append({"date":pd.to_datetime(d).date().isoformat(),"metric":k,
            "n_common_pixels":int(common.sum()),"replication_rmse":float(np.sqrt(np.mean(diff**2))) if diff.size else np.nan,
            "replication_mae":float(np.mean(np.abs(diff))) if diff.size else np.nan,
            "replication_max_abs":float(np.max(np.abs(diff))) if diff.size else np.nan,
            "baseline_valid_fraction":float(np.isfinite(a).mean()),
            "strict_valid_fraction":float(np.isfinite(strict[k]).mean()),
            "strict_delta_valid_fraction":float(np.isfinite(strict[k]).mean()-np.isfinite(a).mean())})

    pg=PILOTS.to_crs(profile["crs"])
    for _,r in pg.iterrows():
        gm=geometry_mask([r.geometry],out_shape=(profile["height"],profile["width"]),
                         transform=profile["transform"],invert=True)
        for k in base:
            vb=base[k][gm & np.isfinite(base[k])]
            vs=strict[k][gm & np.isfinite(strict[k])]
            poly_rows.append({"date":pd.to_datetime(d).date().isoformat(),"pilot_id":r["pilot_id"],
                "class4":r["class4"],"metric":k,"experiment":"STRICT_SCL_MASK",
                "baseline_n":len(vb),"variant_n":len(vs),
                "baseline_median":float(np.median(vb)) if len(vb) else np.nan,
                "variant_median":float(np.median(vs)) if len(vs) else np.nan,
                "delta_median":float(np.median(vs)-np.median(vb)) if len(vb) and len(vs) else np.nan,
                "delta_valid_fraction":float((len(vs)-len(vb))/len(vb)) if len(vb) else np.nan})
        for k in nearest:
            vb=base[k][gm & np.isfinite(base[k])]
            vn=nearest[k][gm & np.isfinite(nearest[k])]
            poly_rows.append({"date":pd.to_datetime(d).date().isoformat(),"pilot_id":r["pilot_id"],
                "class4":r["class4"],"metric":k,"experiment":"NEAREST_20M_RESAMPLING",
                "baseline_n":len(vb),"variant_n":len(vn),
                "baseline_median":float(np.median(vb)) if len(vb) else np.nan,
                "variant_median":float(np.median(vn)) if len(vn) else np.nan,
                "delta_median":float(np.median(vn)-np.median(vb)) if len(vb) and len(vn) else np.nan,
                "delta_valid_fraction":float((len(vn)-len(vb))/len(vb)) if len(vb) else np.nan})

    # Persist a controlled example for the date with known cloud/validity limitations.
    if d=="20231010":
        write_float(EX/"20231010_ndvi_strict_scl.tif",strict["ndvi"],profile)
        write_float(EX/"20231010_ndre_strict_scl.tif",strict["ndre"],profile)
        write_float(EX/"20231010_ndre_nearest20m.tif",nearest["ndre"],profile)
        write_float(EX/"20231010_ndmi_nearest20m.tif",nearest["ndmi"],profile)

rep=pd.DataFrame(rep_rows)
poly=pd.DataFrame(poly_rows)
rep.to_csv(QC/"reprocessing_replication_qc.csv",index=False)
poly.to_csv(QC/"reprocessing_polygon_effects.csv",index=False)
summary=poly.groupby(["experiment","metric"]).agg(
    n=("delta_median","count"),median_delta=("delta_median","median"),
    median_abs_delta=("delta_median",lambda x: np.nanmedian(np.abs(x))),
    p95_abs_delta=("delta_median",lambda x: np.nanpercentile(np.abs(x.dropna()),95) if x.notna().any() else np.nan),
    median_delta_valid_fraction=("delta_valid_fraction","median"),
    min_delta_valid_fraction=("delta_valid_fraction","min")).reset_index()
summary.to_csv(QC/"reprocessing_validation_summary.csv",index=False)
print("Baseline replication max RMSE:",rep["replication_rmse"].max())
print(summary.to_string(index=False))
print("Example reprocessed rasters:",EX)
