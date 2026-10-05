import pandas as pd

from pathlib import Path

from rgb_utils import create_rgb_composite
from recanto_analysis import main as analyze_recanto
from water_mask import main as build_water_masks
from extract_waterline import main as extract_recanto_interfaces
from plots import (
    plot_index_comparison,
    plot_change_comparison,
    plot_recanto_overview_zoom,
)
from load_raster import extract_product_metadata
from preprocess import (
    clip_sentinel2_bands,
    resample_to_match,
    prepare_scl_mask,
)
from spectral_indices import (
    calculate_ndvi,
    calculate_ndwi,
    calculate_mndwi,
)
from change_detection import (
    create_common_valid_mask,
    calculate_difference,
    summarize_change_raster,
)


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"


def main():

    # --------------------------------------------------
    # 1. Locate Sentinel-2 products
    # --------------------------------------------------

    safe_products = sorted(
        RAW_DATA_DIR.glob("*.SAFE")
    )

    print(
        f"\nSAFE products found: "
        f"{len(safe_products)}"
    )

    years_found = [extract_product_metadata(p)["acquisition_date"][:4] for p in safe_products]
    if sorted(years_found) != ["2019", "2022", "2025"]:
        raise ValueError("Expected exactly one Sentinel-2 L2A SAFE product for each year: 2019, 2022, 2025. See README.md.")

    bands = {
        "B02": "10m",
        "B03": "10m",
        "B04": "10m",
        "B08": "10m",
        "B11": "20m",
        "B12": "20m",
    }

    aoi_path = (
        BASE_DIR
        / "data"
        / "aoi"
        / "itaipuacu_coastal_aoi.geojson"
    )

    # --------------------------------------------------
    # 2. Process each Sentinel-2 scene
    # --------------------------------------------------

    for safe_dir in safe_products:

        metadata = extract_product_metadata(
            safe_dir
        )

        print("\n-----------------------------")

        print(
            f"Product: "
            f"{metadata['product']}"
        )

        print(
            f"Satellite: "
            f"{metadata['satellite']}"
        )

        print(
            f"Acquisition date: "
            f"{metadata['acquisition_date']}"
        )

        print(
            f"Tile: "
            f"{metadata['tile']}"
        )

        print(
            f"CRS: "
            f"{metadata['crs']}"
        )

        print(
            f"Dimensions: "
            f"{metadata['width']} x "
            f"{metadata['height']}"
        )

        print(
            f"Resolution: "
            f"{metadata['resolution_x']} m"
        )

        print(
            f"Bounds: "
            f"{metadata['bounds']}"
        )

        year = (
            metadata[
                "acquisition_date"
            ][:4]
        )

        output_dir = (
            BASE_DIR
            / "data"
            / "processed"
            / year
        )

        print(
            f"\nClipping bands for "
            f"{year}..."
        )

        outputs = clip_sentinel2_bands(
            safe_dir=safe_dir,
            aoi_path=aoi_path,
            output_dir=output_dir,
            bands=bands,
        )

        for band, path in outputs.items():
            print(
                f"{band}: "
                f"{path}"
            )

        # --------------------------------------------------
        # 3. Resample SWIR bands from 20 m to 10 m
        # --------------------------------------------------

        reference_band = (
            output_dir
            / "B04_10m.tif"
        )

        for swir_band in [
            "B11",
            "B12",
        ]:

            source_band = (
                output_dir
                / f"{swir_band}_20m.tif"
            )

            resampled_band = (
                output_dir
                / f"{swir_band}_10m.tif"
            )

            resample_to_match(
                source_path=source_band,
                reference_path=reference_band,
                output_path=resampled_band,
            )

            print(
                f"{swir_band} "
                f"resampled to 10 m: "
                f"{resampled_band}"
            )

        # --------------------------------------------------
        # 4. Prepare SCL quality mask
        # --------------------------------------------------

        scl_path = prepare_scl_mask(
            safe_dir=safe_dir,
            aoi_path=aoi_path,
            output_dir=output_dir,
        )

        print(
            f"SCL prepared at 10 m: "
            f"{scl_path}"
        )

        # --------------------------------------------------
        # 5. Calculate spectral indices
        # --------------------------------------------------

        ndvi_path = (
            output_dir
            / "NDVI.tif"
        )

        ndwi_path = (
            output_dir
            / "NDWI.tif"
        )

        mndwi_path = (
            output_dir
            / "MNDWI.tif"
        )

        calculate_ndvi(
            red_path=(
                output_dir
                / "B04_10m.tif"
            ),
            nir_path=(
                output_dir
                / "B08_10m.tif"
            ),
            output_path=ndvi_path,
            scl_path=scl_path,
        )

        calculate_ndwi(
            green_path=(
                output_dir
                / "B03_10m.tif"
            ),
            nir_path=(
                output_dir
                / "B08_10m.tif"
            ),
            output_path=ndwi_path,
            scl_path=scl_path,
        )

        calculate_mndwi(
            green_path=(
                output_dir
                / "B03_10m.tif"
            ),
            swir1_path=(
                output_dir
                / "B11_10m.tif"
            ),
            output_path=mndwi_path,
            scl_path=scl_path,
        )

        print(
            f"NDVI: "
            f"{ndvi_path}"
        )

        print(
            f"NDWI: "
            f"{ndwi_path}"
        )

        print(
            f"MNDWI: "
            f"{mndwi_path}"
        )

    # --------------------------------------------------
    # 6. Create 2025 natural-color RGB composite
    # --------------------------------------------------

    rgb_2025_path = create_rgb_composite(
        red_path=(
            BASE_DIR
            / "data"
            / "processed"
            / "2025"
            / "B04_10m.tif"
        ),
        green_path=(
            BASE_DIR
            / "data"
            / "processed"
            / "2025"
            / "B03_10m.tif"
        ),
        blue_path=(
            BASE_DIR
            / "data"
            / "processed"
            / "2025"
            / "B02_10m.tif"
        ),
        scl_path=(
            BASE_DIR
            / "data"
            / "processed"
            / "2025"
            / "SCL_10m.tif"
        ),
        output_path=(
            BASE_DIR
            / "data"
            / "processed"
            / "2025"
            / "RGB_2025.tif"
        ),
        stretch_percentiles=(
            1,
            99,
        ),
    )

    print(
        f"\n2025 RGB composite: "
        f"{rgb_2025_path}"
    )

    # --------------------------------------------------
    # 7. Create Recanto overview + zoom figure
    # --------------------------------------------------

    # Build dependencies before plotting; works without pre-existing outputs.
    analyze_recanto()
    build_water_masks()
    extract_recanto_interfaces()

    recanto_aoi_path = (
        BASE_DIR
        / "data"
        / "aoi"
        / "recanto_focus_aoi.geojson"
    )

    waterline_2019_path = (
        BASE_DIR
        / "outputs"
        / "vectors"
        / "recanto_waterlines"
        / "waterline_mndwi_2019.geojson"
    )

    waterline_2022_path = (
        BASE_DIR
        / "outputs"
        / "vectors"
        / "recanto_waterlines"
        / "waterline_mndwi_2022.geojson"
    )

    waterline_2025_path = (
        BASE_DIR
        / "outputs"
        / "vectors"
        / "recanto_waterlines"
        / "waterline_mndwi_2025.geojson"
    )

    recanto_figure_path = (
        BASE_DIR
        / "outputs"
        / "figures"
        / "recanto_overview_zoom.png"
    )

    plot_recanto_overview_zoom(
        rgb_raster_path=rgb_2025_path,
        recanto_polygon_path=recanto_aoi_path,
        shoreline_paths=[
            waterline_2019_path,
            waterline_2022_path,
            waterline_2025_path,
        ],
        shoreline_labels=[
            "2019",
            "2022",
            "2025",
        ],
        output_path=recanto_figure_path,
        zoom_buffer=120,
    )

    print(
        f"Recanto A+B figure: "
        f"{recanto_figure_path}"
    )

    # --------------------------------------------------
    # 8. Build paths for temporal comparison
    # --------------------------------------------------

    years = [
        "2019",
        "2022",
        "2025",
    ]

    ndvi_paths = [
        (
            BASE_DIR
            / "data"
            / "processed"
            / year
            / "NDVI.tif"
        )
        for year in years
    ]

    ndwi_paths = [
        (
            BASE_DIR
            / "data"
            / "processed"
            / year
            / "NDWI.tif"
        )
        for year in years
    ]

    mndwi_paths = [
        (
            BASE_DIR
            / "data"
            / "processed"
            / year
            / "MNDWI.tif"
        )
        for year in years
    ]

    # --------------------------------------------------
    # 9. Generate temporal comparison figures
    # --------------------------------------------------

    plot_index_comparison(
        raster_paths=ndvi_paths,
        years=years,
        index_name="NDVI",
        output_path=(
            BASE_DIR
            / "outputs"
            / "figures"
            / "ndvi_comparison.png"
        ),
        cmap="RdYlGn",
    )

    plot_index_comparison(
        raster_paths=ndwi_paths,
        years=years,
        index_name="NDWI",
        output_path=(
            BASE_DIR
            / "outputs"
            / "figures"
            / "ndwi_comparison.png"
        ),
        cmap="Blues",
    )

    plot_index_comparison(
        raster_paths=mndwi_paths,
        years=years,
        index_name="MNDWI",
        output_path=(
            BASE_DIR
            / "outputs"
            / "figures"
            / "mndwi_comparison.png"
        ),
        cmap="Blues",
    )

    print(
        "\nComparison figures generated."
    )

    # --------------------------------------------------
    # 10. Configure temporal change analysis
    # --------------------------------------------------

    change_dir = (
        BASE_DIR
        / "data"
        / "processed"
        / "change"
    )

    change_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    periods = [
        ("2019", "2022"),
        ("2022", "2025"),
        ("2019", "2025"),
    ]

    indices = [
        "NDVI",
        "NDWI",
        "MNDWI",
    ]

    # --------------------------------------------------
    # 11. Create common valid masks
    # --------------------------------------------------

    common_mask_dir = (
        BASE_DIR
        / "data"
        / "processed"
        / "common_masks"
    )

    common_mask_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    common_masks = {}

    for index_name in indices:

        index_paths = [
            (
                BASE_DIR
                / "data"
                / "processed"
                / year
                / f"{index_name}.tif"
            )
            for year in years
        ]

        common_mask_path = (
            common_mask_dir
            / f"{index_name}_common_mask.tif"
        )

        create_common_valid_mask(
            raster_paths=index_paths,
            output_path=common_mask_path,
        )

        common_masks[
            index_name
        ] = common_mask_path

        print(
            f"{index_name} common mask: "
            f"{common_mask_path}"
        )

    # --------------------------------------------------
    # 12. Calculate temporal change rasters
    # --------------------------------------------------

    change_summary = []

    for index_name in indices:

        for (
            earlier_year,
            later_year,
        ) in periods:

            earlier_path = (
                BASE_DIR
                / "data"
                / "processed"
                / earlier_year
                / f"{index_name}.tif"
            )

            later_path = (
                BASE_DIR
                / "data"
                / "processed"
                / later_year
                / f"{index_name}.tif"
            )

            output_path = (
                change_dir
                / (
                    f"{index_name}_"
                    f"{later_year}_minus_"
                    f"{earlier_year}.tif"
                )
            )

            calculate_difference(
                earlier_path=earlier_path,
                later_path=later_path,
                output_path=output_path,
                common_mask_path=(
                    common_masks[
                        index_name
                    ]
                ),
            )

            summary = summarize_change_raster(
                raster_path=output_path,
                positive_threshold=0.2,
                negative_threshold=-0.2,
            )

            summary[
                "index"
            ] = index_name

            summary[
                "period"
            ] = (
                f"{earlier_year}-"
                f"{later_year}"
            )

            change_summary.append(
                summary
            )

            print(
                f"{index_name} change "
                f"{earlier_year}-"
                f"{later_year}: "
                f"{output_path}"
            )

    # --------------------------------------------------
    # 13. Export change statistics
    # --------------------------------------------------

    summary_df = pd.DataFrame(
        change_summary
    )

    summary_df = summary_df[
        [
            "index",
            "period",
            "n_pixels",
            "mean",
            "median",
            "std",
            "min",
            "p05",
            "p95",
            "max",
            "positive_change_pct",
            "negative_change_pct",
            "stable_pct",
            "positive_change_ha",
            "negative_change_ha",
            "stable_ha",
        ]
    ]

    summary_path = (
        BASE_DIR
        / "outputs"
        / "tables"
        / "change_summary.csv"
    )

    summary_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary_df.to_csv(
        summary_path,
        index=False,
    )

    print(
        f"\nChange summary saved to: "
        f"{summary_path}"
    )

    # --------------------------------------------------
    # 14. Generate change comparison figures
    # --------------------------------------------------

    change_period_labels = [
        "2019-2022",
        "2022-2025",
        "2019-2025",
    ]

    ndvi_change_paths = [
        (
            change_dir
            / "NDVI_2022_minus_2019.tif"
        ),
        (
            change_dir
            / "NDVI_2025_minus_2022.tif"
        ),
        (
            change_dir
            / "NDVI_2025_minus_2019.tif"
        ),
    ]

    ndwi_change_paths = [
        (
            change_dir
            / "NDWI_2022_minus_2019.tif"
        ),
        (
            change_dir
            / "NDWI_2025_minus_2022.tif"
        ),
        (
            change_dir
            / "NDWI_2025_minus_2019.tif"
        ),
    ]

    mndwi_change_paths = [
        (
            change_dir
            / "MNDWI_2022_minus_2019.tif"
        ),
        (
            change_dir
            / "MNDWI_2025_minus_2022.tif"
        ),
        (
            change_dir
            / "MNDWI_2025_minus_2019.tif"
        ),
    ]

    plot_change_comparison(
        raster_paths=ndvi_change_paths,
        period_labels=change_period_labels,
        index_name="NDVI",
        output_path=(
            BASE_DIR
            / "outputs"
            / "figures"
            / "ndvi_change_comparison.png"
        ),
        vmin=-0.4,
        vmax=0.4,
        cmap="RdYlGn",
    )

    plot_change_comparison(
        raster_paths=ndwi_change_paths,
        period_labels=change_period_labels,
        index_name="NDWI",
        output_path=(
            BASE_DIR
            / "outputs"
            / "figures"
            / "ndwi_change_comparison.png"
        ),
        vmin=-0.4,
        vmax=0.4,
        cmap="RdBu",
    )

    plot_change_comparison(
        raster_paths=mndwi_change_paths,
        period_labels=change_period_labels,
        index_name="MNDWI",
        output_path=(
            BASE_DIR
            / "outputs"
            / "figures"
            / "mndwi_change_comparison.png"
        ),
        vmin=-0.4,
        vmax=0.4,
        cmap="RdBu",
    )

    print(
        "\nChange comparison figures generated."
    )


if __name__ == "__main__":
    main()