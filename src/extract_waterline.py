from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio

from rasterio.features import shapes
from shapely.geometry import shape
from shapely.ops import unary_union


BASE_DIR = Path(__file__).resolve().parent.parent

YEARS = [
    "2019",
    "2022",
    "2025",
]


def extract_waterline(
    water_mask_path,
    aoi_path,
    output_path,
    edge_buffer_m=20,
):
    """
    Extract an approximate water-land interface from
    a binary water mask.

    Expected raster:
        1 = water
        0 = non-water

    The outer AOI boundary is removed so that only the
    internal water-land interface remains.
    """

    water_mask_path = Path(
        water_mask_path
    )

    aoi_path = Path(
        aoi_path
    )

    output_path = Path(
        output_path
    )

    # --------------------------------------------------
    # Read binary water mask
    # --------------------------------------------------

    with rasterio.open(
        water_mask_path
    ) as src:

        data = src.read(1)

        transform = src.transform
        raster_crs = src.crs

    water = (
        data == 1
    )

    # --------------------------------------------------
    # Convert water pixels to polygons
    # --------------------------------------------------

    polygons = []

    for geom, value in shapes(
        data.astype(np.uint8),
        mask=water,
        transform=transform,
    ):
        if value == 1:
            polygons.append(
                shape(geom)
            )

    if not polygons:
        raise ValueError(
            f"No water polygons found in "
            f"{water_mask_path}"
        )

    # --------------------------------------------------
    # Merge water polygons
    # --------------------------------------------------

    merged_water = unary_union(
        polygons
    )

    # Keep only the largest connected water body.
    # This removes small isolated water-like patches.
    if merged_water.geom_type == "MultiPolygon":

        water_polygon = max(
            merged_water.geoms,
            key=lambda geom: geom.area,
        )

    else:
        water_polygon = merged_water

    # --------------------------------------------------
    # Read AOI
    # --------------------------------------------------

    aoi = gpd.read_file(
        aoi_path
    )

    if aoi.crs != raster_crs:
        aoi = aoi.to_crs(
            raster_crs
        )

    aoi_geometry = unary_union(
        aoi.geometry
    )

    # --------------------------------------------------
    # Extract water polygon boundary
    # --------------------------------------------------

    water_boundary = (
        water_polygon.boundary
    )

    # --------------------------------------------------
    # Remove artificial edges produced by AOI clipping
    # --------------------------------------------------

    aoi_edge_zone = (
        aoi_geometry.boundary.buffer(
            edge_buffer_m
        )
    )

    waterline = (
        water_boundary.difference(
            aoi_edge_zone
        )
    )

    # --------------------------------------------------
    # Save vector
    # --------------------------------------------------

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    waterline_gdf = gpd.GeoDataFrame(
        {
            "source": ["MNDWI"],
            "threshold": [0.0],
        },
        geometry=[
            waterline
        ],
        crs=raster_crs,
    )

    waterline_gdf.to_file(
        output_path,
        driver="GeoJSON",
    )

    return output_path


def main():

    recanto_aoi = (
        BASE_DIR
        / "data"
        / "aoi"
        / "recanto_focus_aoi.geojson"
    )

    output_dir = (
        BASE_DIR
        / "outputs"
        / "vectors"
        / "recanto_waterlines"
    )

    for year in YEARS:

        mask_path = (
            BASE_DIR
            / "data"
            / "processed"
            / "recanto"
            / year
            / "water_mask_mndwi.tif"
        )

        output_path = (
            output_dir
            / f"waterline_mndwi_{year}.geojson"
        )

        extract_waterline(
            water_mask_path=mask_path,
            aoi_path=recanto_aoi,
            output_path=output_path,
            edge_buffer_m=20,
        )

        print(
            f"{year} water-land interface: "
            f"{output_path}"
        )


if __name__ == "__main__":
    main()