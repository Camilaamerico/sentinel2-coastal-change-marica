from pathlib import Path

import numpy as np
import rasterio


def create_common_valid_mask(
    raster_paths,
    output_path,
):
    """
    Create a common valid-data mask across multiple rasters.

    A pixel is valid only if it contains a finite value
    in every raster.
    """

    raster_paths = [
        Path(path)
        for path in raster_paths
    ]

    output_path = Path(
        output_path
    )

    if not raster_paths:
        raise ValueError(
            "No raster paths were provided."
        )

    with rasterio.open(
        raster_paths[0]
    ) as src:

        common_mask = np.isfinite(
            src.read(1)
        )

        metadata = (
            src.meta.copy()
        )

        reference_shape = (
            src.shape
        )

        reference_transform = (
            src.transform
        )

        reference_crs = (
            src.crs
        )

    for raster_path in raster_paths[1:]:

        with rasterio.open(
            raster_path
        ) as src:

            if src.shape != reference_shape:
                raise ValueError(
                    "Input rasters do not have "
                    "the same dimensions."
                )

            if (
                src.transform
                != reference_transform
            ):
                raise ValueError(
                    "Input rasters are not "
                    "spatially aligned."
                )

            if src.crs != reference_crs:
                raise ValueError(
                    "Input rasters do not use "
                    "the same CRS."
                )

            data = src.read(1)

            common_mask &= (
                np.isfinite(data)
            )

    mask_uint8 = (
        common_mask.astype(
            np.uint8
        )
    )

    metadata.update({
        "driver": "GTiff",
        "dtype": "uint8",
        "count": 1,
        "nodata": 0,
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
            mask_uint8,
            1,
        )

    return output_path


def calculate_difference(
    earlier_path,
    later_path,
    output_path,
    common_mask_path=None,
):
    """
    Calculate temporal raster difference:

        later - earlier

    Positive values indicate an increase.
    Negative values indicate a decrease.

    If a common mask is supplied, only pixels valid
    across all comparison dates are retained.
    """

    earlier_path = Path(
        earlier_path
    )

    later_path = Path(
        later_path
    )

    output_path = Path(
        output_path
    )

    with rasterio.open(
        earlier_path
    ) as src_earlier:

        earlier = (
            src_earlier.read(1)
            .astype(np.float32)
        )

        metadata = (
            src_earlier.meta.copy()
        )

        earlier_transform = (
            src_earlier.transform
        )

        earlier_crs = (
            src_earlier.crs
        )

        earlier_shape = (
            src_earlier.shape
        )

    with rasterio.open(
        later_path
    ) as src_later:

        later = (
            src_later.read(1)
            .astype(np.float32)
        )

        if (
            src_later.shape
            != earlier_shape
        ):
            raise ValueError(
                "Input rasters do not have "
                "the same dimensions."
            )

        if (
            src_later.transform
            != earlier_transform
        ):
            raise ValueError(
                "Input rasters are not "
                "spatially aligned."
            )

        if (
            src_later.crs
            != earlier_crs
        ):
            raise ValueError(
                "Input rasters do not use "
                "the same CRS."
            )

    valid_mask = (
        np.isfinite(earlier)
        & np.isfinite(later)
    )

    if common_mask_path is not None:

        common_mask_path = Path(
            common_mask_path
        )

        with rasterio.open(
            common_mask_path
        ) as src_mask:

            common_mask = (
                src_mask.read(1)
                .astype(bool)
            )

            if (
                src_mask.shape
                != earlier_shape
            ):
                raise ValueError(
                    "Common mask does not have "
                    "the same dimensions."
                )

            if (
                src_mask.transform
                != earlier_transform
            ):
                raise ValueError(
                    "Common mask is not "
                    "spatially aligned."
                )

            if (
                src_mask.crs
                != earlier_crs
            ):
                raise ValueError(
                    "Common mask does not use "
                    "the same CRS."
                )

        valid_mask &= common_mask

    difference = np.full(
        earlier.shape,
        np.nan,
        dtype=np.float32,
    )

    difference[valid_mask] = (
        later[valid_mask]
        - earlier[valid_mask]
    )

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
            difference,
            1,
        )

    return output_path


def summarize_change_raster(
    raster_path,
    positive_threshold=0.2,
    negative_threshold=-0.2,
):
    """
    Calculate descriptive statistics for a change raster.
    """

    raster_path = Path(
        raster_path
    )

    with rasterio.open(
        raster_path
    ) as src:

        data = (
            src.read(1)
            .astype(np.float32)
        )

        pixel_width = abs(
            src.transform.a
        )

        pixel_height = abs(
            src.transform.e
        )

    valid = data[
        np.isfinite(data)
    ]

    if valid.size == 0:
        raise ValueError(
            f"No valid pixels found in {raster_path}"
        )

    positive_mask = (
        valid >= positive_threshold
    )

    negative_mask = (
        valid <= negative_threshold
    )

    stable_mask = (
        (valid > negative_threshold)
        & (valid < positive_threshold)
    )

    positive_pixels = np.sum(
        positive_mask
    )

    negative_pixels = np.sum(
        negative_mask
    )

    stable_pixels = np.sum(
        stable_mask
    )

    positive_change = (
        positive_pixels
        / valid.size
        * 100
    )

    negative_change = (
        negative_pixels
        / valid.size
        * 100
    )

    stable = (
        stable_pixels
        / valid.size
        * 100
    )

    pixel_area_m2 = (
        pixel_width
        * pixel_height
    )

    pixel_area_ha = (
        pixel_area_m2
        / 10000
    )

    return {
        "n_pixels": int(
            valid.size
        ),

        "mean": float(
            np.mean(valid)
        ),

        "median": float(
            np.median(valid)
        ),

        "std": float(
            np.std(valid)
        ),

        "min": float(
            np.min(valid)
        ),

        "p05": float(
            np.percentile(
                valid,
                5,
            )
        ),

        "p95": float(
            np.percentile(
                valid,
                95,
            )
        ),

        "max": float(
            np.max(valid)
        ),

        "positive_change_pct": float(
            positive_change
        ),

        "negative_change_pct": float(
            negative_change
        ),

        "stable_pct": float(
            stable
        ),

        "positive_change_ha": float(
            positive_pixels
            * pixel_area_ha
        ),

        "negative_change_ha": float(
            negative_pixels
            * pixel_area_ha
        ),

        "stable_ha": float(
            stable_pixels
            * pixel_area_ha
        ),
    }