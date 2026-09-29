from pathlib import Path
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling

BASE = Path(r"C:\Projetos\SAR_Optical_Perennial_Crops_Italy")
RAW = BASE / "data/raw/sentinel2"
OUT = BASE / "data/processed/sentinel2"
OUT.mkdir(parents=True, exist_ok=True)
BANDS = ["red", "green", "nir", "rededge1", "swir16", "scl"]
REFLECTANCE_SCALE = 0.0001
REFLECTANCE_OFFSET = -0.1

def mosaic_band(date_dir, band, out_dir):
    files = sorted(date_dir.glob(f"*/*_{band}.tif"))
    if not files:
        return None
    srcs = [rasterio.open(p) for p in files]
    arr, transform = merge(srcs)
    profile = srcs[0].profile.copy()
    profile.update(height=arr.shape[1], width=arr.shape[2],
                   transform=transform, count=1, compress="deflate",
                   tiled=True, BIGTIFF="IF_SAFER")
    out = out_dir / f"{date_dir.name}_{band}.tif"
    with rasterio.open(out, "w", **profile) as dst:
        dst.write(arr[0], 1)
    for s in srcs:
        s.close()
    return out
def align_to(path, ref_profile, resampling):
    with rasterio.open(path) as src:
        out = np.empty((ref_profile["height"], ref_profile["width"]), dtype=np.float32)
        reproject(
            source=src.read(1),
            destination=out,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref_profile["transform"],
            dst_crs=ref_profile["crs"],
            resampling=resampling,
        )
    return out

def write_float(path, arr, profile):
    p = profile.copy()
    p.update(dtype="float32", nodata=-9999.0, count=1,
             compress="deflate", tiled=True)
    out = np.where(np.isfinite(arr), arr, -9999.0).astype("float32")
    with rasterio.open(path, "w", **p) as dst:
        dst.write(out, 1)

for date_dir in sorted(p for p in RAW.iterdir() if p.is_dir()):
    out_dir = OUT / date_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)
    mosaics = {b: mosaic_band(date_dir, b, out_dir) for b in BANDS}
    if not all(mosaics[b] for b in ["red", "green", "nir", "rededge1", "swir16", "scl"]):
        print("Incomplete:", date_dir.name)
        continue
    with rasterio.open(mosaics["nir"]) as ref:
        profile = ref.profile.copy()
        nir_dn = ref.read(1).astype("float32")
    with rasterio.open(mosaics["red"]) as src:
        red_dn = src.read(1).astype("float32")
    with rasterio.open(mosaics["green"]) as src:
        green_dn = src.read(1).astype("float32")
    re1_dn = align_to(mosaics["rededge1"], profile, Resampling.bilinear)
    swir_dn = align_to(mosaics["swir16"], profile, Resampling.bilinear)
    scl = align_to(mosaics["scl"], profile, Resampling.nearest)

    nir = nir_dn * REFLECTANCE_SCALE + REFLECTANCE_OFFSET
    red = red_dn * REFLECTANCE_SCALE + REFLECTANCE_OFFSET
    green = green_dn * REFLECTANCE_SCALE + REFLECTANCE_OFFSET
    re1 = re1_dn * REFLECTANCE_SCALE + REFLECTANCE_OFFSET
    swir = swir_dn * REFLECTANCE_SCALE + REFLECTANCE_OFFSET

    bad = np.isin(scl.astype("int16"), [0, 1, 3, 8, 9, 10, 11])
    bad |= (nir_dn == 0) | (red_dn == 0) | (green_dn == 0) | (re1_dn == 0) | (swir_dn == 0)
    eps = 1e-6
    indices = {
        "ndvi": (nir - red) / (nir + red + eps),
        "ndre": (nir - re1) / (nir + re1 + eps),
        "ndmi": (nir - swir) / (nir + swir + eps),
        "gndvi": (nir - green) / (nir + green + eps),
    }
    for name, arr in indices.items():
        arr[bad | ~np.isfinite(arr)] = np.nan
        write_float(out_dir / f"{date_dir.name}_{name}.tif", arr, profile)
    print("Processed:", date_dir.name)
