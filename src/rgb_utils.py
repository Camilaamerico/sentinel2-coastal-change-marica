from pathlib import Path

import numpy as np
import rasterio


BOA_QUANTIFICATION_VALUE = 10000.0
BOA_ADD_OFFSET = -1000.0
NODATA_DN = 0

INVALID_SCL_CLASSES = {
    0,   # No data
    1,   # Saturated / defective
    3,   # Cloud shadows
    8,   # Cloud medium probability
    9,   # Cloud high probability
    10,  # Thin cirrus
    11,  # Snow / ice
}


def dn_to_reflectance(
    digital_number,
    offset=BOA_ADD_OFFSET,
    quantification_value=BOA_QUANTIFICATION_VALUE,
):
    """
    Convert Sentinel-2 Level-2A digital numbers
    to bottom-of-atmosphere reflectance.
    """

    digital_number = digital_number.astype(np.float32)

    reflectance = (
        digital_number + offset
    ) / quantification_value

    reflectance[digital_number == NODATA_DN] = np.nan

    return reflectance


def _read_single_band(path):
    path = Path(path)

    with rasterio.open(path) as src:
        data = src.read(1).astype(np.float32)
        meta = src.meta.copy()
        transform = src.transform
        crs = src.crs
        shape = src.shape

    return data, meta, transform, crs, shape


def _validate_same_grid(
    transform_a,
    crs_a,
    shape_a,
    transform_b,
    crs_b,
    shape_b,
    label_a="A",
    label_b="B",
):
    if shape_a != shape_b:
        raise ValueError(
            f"Inputs {label_a} and {label_b} "
            "do not have the same dimensions."
        )

    if transform_a != transform_b:
        raise ValueError(
            f"Inputs {label_a} and {label_b} "
            "are not spatially aligned."
        )

    if crs_a != crs_b:
        raise ValueError(
            f"Inputs {label_a} and {label_b} "
            "do not use the same CRS."
        )


def create_rgb_composite(
    red_path,
    green_path,
    blue_path,
    output_path,
    scl_path=None,
    stretch_percentiles=(1, 99),
):
    """
    Create an RGB GeoTIFF from Sentinel-2 bands:

        R = B04
        G = B03
        B = B02

    The function converts DN to BOA reflectance,
    optionally applies SCL masking, and saves an
    8-bit RGB image stretched for visualization.
    """

    red_dn, meta, transform, crs, shape = _read_single_band(red_path)
    green_dn, _, transform_g, crs_g, shape_g = _read_single_band(green_path)
    blue_dn, _, transform_b, crs_b, shape_b = _read_single_band(blue_path)

    _validate_same_grid(
        transform, crs, shape,
        transform_g, crs_g, shape_g,
        label_a="red", label_b="green",
    )

    _validate_same_grid(
        transform, crs, shape,
        transform_b, crs_b, shape_b,
        label_a="red", label_b="blue",
    )

    red = dn_to_reflectance(red_dn)
    green = dn_to_reflectance(green_dn)
    blue = dn_to_reflectance(blue_dn)

    valid_mask = (
        np.isfinite(red)
        & np.isfinite(green)
        & np.isfinite(blue)
        & (red >= 0)
        & (green >= 0)
        & (blue >= 0)
    )

    if scl_path is not None:
        scl_path = Path(scl_path)

        with rasterio.open(scl_path) as src_scl:
            scl = src_scl.read(1)

            if src_scl.shape != shape:
                raise ValueError(
                    "SCL mask does not have the same dimensions."
                )

            if src_scl.transform != transform:
                raise ValueError(
                    "SCL mask is not spatially aligned."
                )

            if src_scl.crs != crs:
                raise ValueError(
                    "SCL mask does not use the same CRS."
                )

        scl_valid = ~np.isin(
            scl,
            list(INVALID_SCL_CLASSES),
        )

        valid_mask &= scl_valid

    rgb = np.stack(
        [red, green, blue],
        axis=0,
    )

    rgb_out = np.zeros_like(
        rgb,
        dtype=np.uint8,
    )

    p_low, p_high = stretch_percentiles

    for i in range(3):
        band = rgb[i]

        valid_values = band[valid_mask]

        if valid_values.size == 0:
            raise ValueError(
                "No valid pixels available to create RGB."
            )

        low = np.percentile(valid_values, p_low)
        high = np.percentile(valid_values, p_high)

        stretched = np.clip(
            (band - low) / (high - low),
            0,
            1,
        )

        stretched[~valid_mask] = 0

        rgb_out[i] = (
            stretched * 255
        ).astype(np.uint8)

    meta.update({
        "driver": "GTiff",
        "dtype": "uint8",
        "count": 3,
        "nodata": 0,
    })

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with rasterio.open(
        output_path,
        "w",
        **meta,
    ) as dst:
        dst.write(rgb_out)

    return output_path