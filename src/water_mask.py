"""Rebuild the per-date MNDWI > 0 masks used by the Recanto interfaces."""
from pathlib import Path

import numpy as np
import rasterio

BASE_DIR = Path(__file__).resolve().parent.parent


def create_water_mask(index_path, output_path):
    """Use 1 for water, 0 for non-water and 255 for invalid observations."""
    with rasterio.open(index_path) as src:
        index = src.read(1, masked=True)
        valid = ~np.ma.getmaskarray(index) & np.isfinite(index.data)
        result = np.full(index.shape, 255, dtype=np.uint8)
        result[valid] = (index.data[valid] > 0).astype(np.uint8)
        profile = src.profile.copy()
    profile.update(dtype="uint8", count=1, nodata=255)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(result, 1)
    return output_path


def main():
    for year in ("2019", "2022", "2025"):
        folder = BASE_DIR / "data" / "processed" / "recanto" / year
        create_water_mask(folder / "MNDWI.tif", folder / "water_mask_mndwi.tif")


if __name__ == "__main__":
    main()
