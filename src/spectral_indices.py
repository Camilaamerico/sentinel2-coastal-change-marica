from pathlib import Path

import numpy as np
import rasterio


BOA_QUANTIFICATION_VALUE = 10000.0
BOA_ADD_OFFSET = -1000.0
NODATA_DN = 0

INVALID_SCL_CLASSES = {
    0,   # No data
    1,   # Saturated / defective
    3,   # Cloud shadow
    8,   # Medium probability cloud
    9,   # High probability cloud
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

    Formula:
        reflectance = (DN + offset) / quantification_value

    DN = 0 is treated as NoData.
    """

    digital_number = digital_number.astype(
        np.float32
    )

    reflectance = (
        digital_number + offset
    ) / quantification_value

    reflectance[
        digital_number == NODATA_DN
    ] = np.nan

    return reflectance


def calculate_normalized_difference(
    band_a_path,
    band_b_path,
    output_path,
    scl_path=None,
    exclude_water=False,
):
    """
    Calculate a normalized difference index:

        (A - B) / (A + B)

    Sentinel-2 Level-2A digital numbers are first
    converted to BOA reflectance.

    Pixels are considered valid only when:
    - both bands contain finite values;
    - both reflectances are non-negative;
    - the denominator is positive;
    - the SCL class is not invalid;
    - water can optionally be excluded.
    """

    band_a_path = Path(
        band_a_path
    )

    band_b_path = Path(
        band_b_path
    )

    output_path = Path(
        output_path
    )

    # --------------------------------------------------
    # Read first band
    # --------------------------------------------------

    with rasterio.open(
        band_a_path
    ) as src_a:

        band_a_dn = (
            src_a.read(1)
            .astype(np.float32)
        )

        metadata = (
            src_a.meta.copy()
        )

        transform_a = (
            src_a.transform
        )

        crs_a = (
            src_a.crs
        )

        shape_a = (
            src_a.shape
        )

    # --------------------------------------------------
    # Read second band and check alignment
    # --------------------------------------------------

    with rasterio.open(
        band_b_path
    ) as src_b:

        band_b_dn = (
            src_b.read(1)
            .astype(np.float32)
        )

        if src_b.shape != shape_a:
            raise ValueError(
                "Input bands do not have "
                "the same dimensions."
            )

        if src_b.transform != transform_a:
            raise ValueError(
                "Input bands are not "
                "spatially aligned."
            )

        if src_b.crs != crs_a:
            raise ValueError(
                "Input bands do not use "
                "the same CRS."
            )

    # --------------------------------------------------
    # Convert digital numbers to BOA reflectance
    # --------------------------------------------------

    band_a = dn_to_reflectance(
        band_a_dn
    )

    band_b = dn_to_reflectance(
        band_b_dn
    )

    denominator = (
        band_a + band_b
    )

    # --------------------------------------------------
    # Initial spectral validity mask
    # --------------------------------------------------

    valid_mask = (
        np.isfinite(band_a)
        & np.isfinite(band_b)
        & (band_a >= 0)
        & (band_b >= 0)
        & (denominator > 0)
    )

    # --------------------------------------------------
    # Apply Sentinel-2 Scene Classification Layer
    # --------------------------------------------------

    if scl_path is not None:

        scl_path = Path(
            scl_path
        )

        with rasterio.open(
            scl_path
        ) as src_scl:

            scl = src_scl.read(1)

            if src_scl.shape != shape_a:
                raise ValueError(
                    "SCL mask does not have "
                    "the same dimensions."
                )

            if src_scl.transform != transform_a:
                raise ValueError(
                    "SCL mask is not "
                    "spatially aligned."
                )

            if src_scl.crs != crs_a:
                raise ValueError(
                    "SCL mask does not use "
                    "the same CRS."
                )

        scl_valid = ~np.isin(
            scl,
            list(
                INVALID_SCL_CLASSES
            ),
        )

        valid_mask &= scl_valid

        # SCL class 6 = water
        if exclude_water:
            valid_mask &= (
                scl != 6
            )

    # --------------------------------------------------
    # Calculate normalized difference
    # --------------------------------------------------

    index = np.full(
        band_a.shape,
        np.nan,
        dtype=np.float32,
    )

    index[valid_mask] = (
        (
            band_a[valid_mask]
            - band_b[valid_mask]
        )
        /
        denominator[valid_mask]
    )

    # --------------------------------------------------
    # Save output
    # --------------------------------------------------

    metadata.update({
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "nodata": np.nan,
    })

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with rasterio.open(
        output_path,
        "w",
        **metadata
    ) as dst:

        dst.write(
            index,
            1,
        )

    return output_path


def calculate_ndvi(
    red_path,
    nir_path,
    output_path,
    scl_path=None,
):
    """
    Calculate NDVI:

        (NIR - Red) / (NIR + Red)

    Water pixels are excluded using SCL class 6.
    """

    return calculate_normalized_difference(
        band_a_path=nir_path,
        band_b_path=red_path,
        output_path=output_path,
        scl_path=scl_path,
        exclude_water=True,
    )


def calculate_ndwi(
    green_path,
    nir_path,
    output_path,
    scl_path=None,
):
    """
    Calculate NDWI:

        (Green - NIR) / (Green + NIR)

    Water pixels are retained.
    """

    return calculate_normalized_difference(
        band_a_path=green_path,
        band_b_path=nir_path,
        output_path=output_path,
        scl_path=scl_path,
        exclude_water=False,
    )


def calculate_mndwi(
    green_path,
    swir1_path,
    output_path,
    scl_path=None,
):
    """
    Calculate MNDWI:

        (Green - SWIR1) / (Green + SWIR1)

    Water pixels are retained.
    """

    return calculate_normalized_difference(
        band_a_path=green_path,
        band_b_path=swir1_path,
        output_path=output_path,
        scl_path=scl_path,
        exclude_water=False,
    )