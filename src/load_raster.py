from pathlib import Path
import re

import rasterio


def find_band_file(safe_dir, band, resolution):
    """
    Find a Sentinel-2 band file inside a SAFE product.

    Parameters
    ----------
    safe_dir : str or Path
        Path to the Sentinel-2 .SAFE directory.
    band : str
        Band name, for example "B04".
    resolution : str
        Spatial resolution, for example "10m".

    Returns
    -------
    Path
        Path to the matching JP2 band file.
    """

    safe_dir = Path(safe_dir)

    search_pattern = (
        safe_dir
        / "GRANULE"
        / "*"
        / "IMG_DATA"
        / f"R{resolution}"
        / f"*_{band}_{resolution}.jp2"
    )

    matches = list(
        safe_dir.glob(
            str(search_pattern.relative_to(safe_dir))
        )
    )

    if not matches:
        raise FileNotFoundError(
            f"Band {band} at {resolution} "
            f"not found in {safe_dir.name}"
        )

    return matches[0]


def extract_product_metadata(safe_dir):
    """
    Extract basic metadata from a Sentinel-2 Level-2A SAFE product.
    """

    safe_dir = Path(safe_dir)

    product_name = safe_dir.name

    date_match = re.search(
        r"MSIL2A_(\d{8})T",
        product_name
    )

    tile_match = re.search(
        r"_T(\d{2}[A-Z]{3})_",
        product_name
    )

    satellite = product_name[:3]

    acquisition_date = (
        date_match.group(1)
        if date_match
        else None
    )

    tile = (
        tile_match.group(1)
        if tile_match
        else None
    )

    b04_path = find_band_file(
        safe_dir,
        band="B04",
        resolution="10m"
    )

    with rasterio.open(b04_path) as src:
        metadata = {
            "product": product_name,
            "satellite": satellite,
            "acquisition_date": acquisition_date,
            "tile": tile,
            "crs": str(src.crs),
            "width": src.width,
            "height": src.height,
            "resolution_x": src.res[0],
            "resolution_y": src.res[1],
            "bounds": src.bounds,
        }

    return metadata

def find_scl_file(
    safe_dir,
    resolution="20m",
):
    """
    Find the Sentinel-2 Scene Classification Layer.
    """

    safe_dir = Path(safe_dir)

    pattern = (
        f"GRANULE/*/IMG_DATA/R{resolution}"
        f"/*_SCL_{resolution}.jp2"
    )

    matches = list(
        safe_dir.glob(pattern)
    )

    if not matches:
        raise FileNotFoundError(
            f"SCL {resolution} not found in {safe_dir}"
        )

    return matches[0]