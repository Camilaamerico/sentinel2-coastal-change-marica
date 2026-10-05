from pathlib import Path

import pandas as pd

from preprocess import clip_raster_to_aoi
from change_detection import (
    create_common_valid_mask,
    calculate_difference,
    summarize_change_raster,
)
from plots import plot_recanto_overview

BASE_DIR = Path(__file__).resolve().parent.parent

YEARS = [
    "2019",
    "2022",
    "2025",
]

INDICES = [
    "NDWI",
    "MNDWI",
]

PERIODS = [
    ("2019", "2022"),
    ("2022", "2025"),
    ("2019", "2025"),
]


def main():
    recanto_aoi = (
        BASE_DIR
        / "data"
        / "aoi"
        / "recanto_focus_aoi.geojson"
    )

    output_root = (
        BASE_DIR
        / "data"
        / "processed"
        / "recanto"
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary_rows = []

    # --------------------------------------------------
    # 1. Clip NDWI and MNDWI to Recanto AOI
    # --------------------------------------------------

    clipped_paths = {}

    for index_name in INDICES:

        clipped_paths[index_name] = {}

        for year in YEARS:

            source_path = (
                BASE_DIR
                / "data"
                / "processed"
                / year
                / f"{index_name}.tif"
            )

            year_dir = (
                output_root
                / year
            )

            year_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            output_path = (
                year_dir
                / f"{index_name}.tif"
            )

            clip_raster_to_aoi(
                raster_path=source_path,
                aoi_path=recanto_aoi,
                output_path=output_path,
            )

            clipped_paths[index_name][
                year
            ] = output_path

            print(
                f"{index_name} {year}: "
                f"{output_path}"
            )

    # --------------------------------------------------
    # 2. Common valid mask for each index
    # --------------------------------------------------

    common_masks = {}

    mask_dir = (
        output_root
        / "common_masks"
    )

    mask_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for index_name in INDICES:

        index_paths = [
            clipped_paths[index_name][year]
            for year in YEARS
        ]

        mask_path = (
            mask_dir
            / f"{index_name}_common_mask.tif"
        )

        create_common_valid_mask(
            raster_paths=index_paths,
            output_path=mask_path,
        )

        common_masks[
            index_name
        ] = mask_path

        print(
            f"{index_name} common mask: "
            f"{mask_path}"
        )

    # --------------------------------------------------
    # 3. Change detection
    # --------------------------------------------------

    change_dir = (
        output_root
        / "change"
    )

    change_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for index_name in INDICES:

        for earlier_year, later_year in PERIODS:

            earlier_path = (
                clipped_paths[
                    index_name
                ][
                    earlier_year
                ]
            )

            later_path = (
                clipped_paths[
                    index_name
                ][
                    later_year
                ]
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
                f"{earlier_year}-{later_year}"
            )

            summary_rows.append(
                summary
            )

            print(
                f"{index_name} "
                f"{earlier_year}-{later_year}: "
                f"{output_path}"
            )

    # --------------------------------------------------
    # 4. Export local statistics
    # --------------------------------------------------

    summary_df = pd.DataFrame(
        summary_rows
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
        / "recanto_change_summary.csv"
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
        f"\nRecanto summary saved to: "
        f"{summary_path}"
    )

    # --------------------------------------------------
    # 5. Recanto overview figure (MNDWI)
    # --------------------------------------------------

    mndwi_state_paths = [
        output_root / "2019" / "MNDWI.tif",
        output_root / "2022" / "MNDWI.tif",
        output_root / "2025" / "MNDWI.tif",
    ]

    mndwi_state_labels = [
        "2019",
        "2022",
        "2025",
    ]

    mndwi_change_paths = [
        change_dir / "MNDWI_2022_minus_2019.tif",
        change_dir / "MNDWI_2025_minus_2022.tif",
        change_dir / "MNDWI_2025_minus_2019.tif",
    ]

    mndwi_change_labels = [
        "2019 → 2022",
        "2022 → 2025",
        "2019 → 2025",
    ]

    figure_path = (
        BASE_DIR
        / "outputs"
        / "figures"
        / "recanto_mndwi_overview.png"
    )

    plot_recanto_overview(
        state_raster_paths=mndwi_state_paths,
        state_labels=mndwi_state_labels,
        change_raster_paths=mndwi_change_paths,
        change_labels=mndwi_change_labels,
        index_name="MNDWI",
        output_path=figure_path,
        state_vmin=-1,
        state_vmax=1,
        change_vmin=-0.4,
        change_vmax=0.4,
        state_cmap="Blues",
        change_cmap="RdBu",
    )

    print(
        f"Recanto overview figure saved to: "
        f"{figure_path}"
    )
    
if __name__ == "__main__":
    main()