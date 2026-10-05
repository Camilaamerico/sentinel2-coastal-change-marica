from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.warp import reproject, Resampling
from load_raster import (
    find_band_file,
    find_scl_file,
)

def clip_raster_to_aoi(
    raster_path,
    aoi_path,
    output_path,
):
    """
    Clip a raster using a vector AOI.

    The AOI is automatically reprojected
    to match the raster CRS.
    """

    raster_path = Path(raster_path)
    aoi_path = Path(aoi_path)
    output_path = Path(output_path)

    aoi = gpd.read_file(aoi_path)

    with rasterio.open(raster_path) as src:
        if aoi.crs != src.crs:
            aoi = aoi.to_crs(src.crs)

        geometries = [
            feature["geometry"]
            for feature in aoi.__geo_interface__["features"]
        ]

        clipped_image, clipped_transform = mask(
            src,
            geometries,
            crop=True
        )

        clipped_meta = src.meta.copy()

        clipped_meta.update({
            "driver": "GTiff",
            "height": clipped_image.shape[1],
            "width": clipped_image.shape[2],
            "transform": clipped_transform,
        })

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with rasterio.open(
        output_path,
        "w",
        **clipped_meta
    ) as dst:
        dst.write(clipped_image)

    return output_path

def clip_sentinel2_bands(
    safe_dir,
    aoi_path,
    output_dir,
    bands,
):
    """
    Clip multiple Sentinel-2 bands to the same AOI.

    Parameters
    ----------
    safe_dir : str or Path
        Path to the Sentinel-2 SAFE product.
    aoi_path : str or Path
        Vector AOI file.
    output_dir : str or Path
        Directory where clipped rasters will be saved.
    bands : dict
        Dictionary in the format:
        {
            "B02": "10m",
            "B03": "10m",
            ...
        }
    """

    from load_raster import find_band_file

    safe_dir = Path(safe_dir)
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    outputs = {}

    for band, resolution in bands.items():
        raster_path = find_band_file(
            safe_dir,
            band=band,
            resolution=resolution
        )

        output_path = (
            output_dir
            / f"{band}_{resolution}.tif"
        )

        clip_raster_to_aoi(
            raster_path=raster_path,
            aoi_path=aoi_path,
            output_path=output_path,
        )

        outputs[band] = output_path

    return outputs

def resample_to_match(
    source_path,
    reference_path,
    output_path,
):
    """
    Resample a raster to match the grid of a reference raster.
    """

    source_path = Path(source_path)
    reference_path = Path(reference_path)
    output_path = Path(output_path)

    with rasterio.open(reference_path) as ref:
        ref_meta = ref.meta.copy()
        ref_transform = ref.transform
        ref_crs = ref.crs
        ref_width = ref.width
        ref_height = ref.height

    with rasterio.open(source_path) as src:
        source_data = src.read(1)

        destination = np.empty(
            (ref_height, ref_width),
            dtype=np.float32
        )

        reproject(
            source=source_data,
            destination=destination,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            resampling=Resampling.bilinear,
        )

        output_meta = src.meta.copy()

        output_meta.update({
            "driver": "GTiff",
            "height": ref_height,
            "width": ref_width,
            "transform": ref_transform,
            "crs": ref_crs,
            "dtype": "float32",
        })

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with rasterio.open(
        output_path,
        "w",
        **output_meta
    ) as dst:
        dst.write(
            destination.astype(np.float32),
            1
        )

    return output_path

def prepare_scl_mask(
    safe_dir,
    aoi_path,
    output_dir,
):
    """
    Clip Sentinel-2 SCL at 20 m and resample it
    to the 10 m analysis grid using nearest neighbour.
    """

    output_dir = Path(output_dir)

    scl_source = find_scl_file(
        safe_dir=safe_dir,
        resolution="20m",
    )

    scl_20m = (
        output_dir
        / "SCL_20m.tif"
    )

    scl_10m = (
        output_dir
        / "SCL_10m.tif"
    )

    clip_raster_to_aoi(
        raster_path=scl_source,
        aoi_path=aoi_path,
        output_path=scl_20m,
    )

    reference_path = (
        output_dir
        / "B04_10m.tif"
    )

    with rasterio.open(
        scl_20m
    ) as src:

        source_data = src.read(1)

        source_transform = src.transform
        source_crs = src.crs

    with rasterio.open(
        reference_path
    ) as ref:

        destination = np.zeros(
            (
                ref.height,
                ref.width,
            ),
            dtype=np.uint8,
        )

        destination_transform = (
            ref.transform
        )

        destination_crs = (
            ref.crs
        )

        metadata = (
            ref.meta.copy()
        )

    reproject(
        source=source_data,
        destination=destination,
        src_transform=source_transform,
        src_crs=source_crs,
        dst_transform=destination_transform,
        dst_crs=destination_crs,
        resampling=Resampling.nearest,
    )

    metadata.update({
        "driver": "GTiff",
        "dtype": "uint8",
        "count": 1,
        "nodata": 0,
    })

    with rasterio.open(
        scl_10m,
        "w",
        **metadata
    ) as dst:

        dst.write(
            destination,
            1,
        )

    return scl_10m