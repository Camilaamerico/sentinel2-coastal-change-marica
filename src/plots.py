from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import rasterio

from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
import matplotlib.patheffects as path_effects


# ============================================================
# General map helpers
# ============================================================

def add_north_arrow(ax):
    """
    Add a simple north arrow to the map.
    """

    ax.annotate(
        "N",
        xy=(0.92, 0.90),
        xytext=(0.92, 0.76),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        arrowprops=dict(
            facecolor="black",
            width=2,
            headwidth=8,
            headlength=10,
        ),
    )


def add_scale_bar(
    ax,
    pixel_size,
    bar_length_m=500,
):
    """
    Add a simple black scale bar in meters.
    """

    x0 = 0.06
    y0 = 0.08

    xlim = ax.get_xlim()

    axis_width_data = abs(
        xlim[1] - xlim[0]
    )

    bar_fraction = (
        bar_length_m
        / axis_width_data
    )

    ax.plot(
        [
            x0,
            x0 + bar_fraction,
        ],
        [
            y0,
            y0,
        ],
        transform=ax.transAxes,
        color="black",
        linewidth=3,
        solid_capstyle="butt",
    )

    ax.text(
        x0,
        y0 + 0.025,
        "0",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=8,
    )

    ax.text(
        x0 + bar_fraction,
        y0 + 0.025,
        f"{int(bar_length_m)} m",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=8,
    )


def add_white_scale_bar(
    ax,
    bar_length_m=1000,
):
    """
    Add a white scale bar with black outline.

    Useful over dark RGB imagery.
    """

    x0 = 0.06
    y0 = 0.08

    xlim = ax.get_xlim()

    axis_width_data = abs(
        xlim[1] - xlim[0]
    )

    bar_fraction = (
        bar_length_m
        / axis_width_data
    )

    ax.plot(
        [
            x0,
            x0 + bar_fraction,
        ],
        [
            y0,
            y0,
        ],
        transform=ax.transAxes,
        color="white",
        linewidth=4,
        solid_capstyle="butt",
        zorder=20,
        path_effects=[
            path_effects.Stroke(
                linewidth=6,
                foreground="black",
            ),
            path_effects.Normal(),
        ],
    )

    text_effect = [
        path_effects.withStroke(
            linewidth=2,
            foreground="black",
        )
    ]

    ax.text(
        x0,
        y0 + 0.025,
        "0",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=8,
        color="white",
        fontweight="bold",
        path_effects=text_effect,
        zorder=21,
    )

    ax.text(
        x0 + bar_fraction,
        y0 + 0.025,
        f"{int(bar_length_m)} m",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=8,
        color="white",
        fontweight="bold",
        path_effects=text_effect,
        zorder=21,
    )


# ============================================================
# Spectral-index temporal comparison
# ============================================================

def plot_index_comparison(
    raster_paths,
    years,
    index_name,
    output_path,
    vmin=-1,
    vmax=1,
    cmap="RdYlGn",
    product_name="Sentinel-2 Level-2A",
    epsg="EPSG:32723",
):
    """
    Plot a vertical comparison of one spectral index
    for multiple years using a fixed color scale.
    """

    output_path = Path(
        output_path
    )

    fig, axes = plt.subplots(
        len(raster_paths),
        1,
        figsize=(8, 10),
        dpi=300,
        sharex=True,
        sharey=True,
    )

    if len(raster_paths) == 1:
        axes = [axes]

    last_image = None

    for i, (
        ax,
        raster_path,
        year,
    ) in enumerate(
        zip(
            axes,
            raster_paths,
            years,
        )
    ):

        with rasterio.open(
            raster_path
        ) as src:

            data = src.read(1)
            bounds = src.bounds
            pixel_size = src.res[0]

        extent = [
            bounds.left,
            bounds.right,
            bounds.bottom,
            bounds.top,
        ]

        last_image = ax.imshow(
            data,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            extent=extent,
            origin="upper",
        )

        ax.set_title(
            str(year),
            fontsize=12,
            fontweight="bold",
            pad=6,
        )

        ax.set_ylabel(
            "Northing (m)"
        )

        if i == len(axes) - 1:
            ax.set_xlabel(
                "Easting (m)"
            )
        else:
            ax.set_xlabel("")

        add_north_arrow(
            ax
        )

        add_scale_bar(
            ax,
            pixel_size=pixel_size,
            bar_length_m=500,
        )

        ax.ticklabel_format(
            style="plain",
            axis="both",
            useOffset=False,
        )

        ax.grid(False)

    fig.suptitle(
        f"{index_name} temporal comparison",
        fontsize=16,
        fontweight="bold",
        y=0.965,
    )

    fig.subplots_adjust(
        left=0.12,
        right=0.94,
        top=0.90,
        bottom=0.18,
        hspace=0.18,
    )

    cbar_ax = fig.add_axes(
        [
            0.20,
            0.12,
            0.60,
            0.025,
        ]
    )

    cbar = fig.colorbar(
        last_image,
        cax=cbar_ax,
        orientation="horizontal",
    )

    cbar.set_label(
        index_name
    )

    metadata_text = (
        f"Data source: {product_name} | "
        f"Years: {', '.join(years)} | "
        f"CRS: {epsg}"
    )

    fig.text(
        0.5,
        0.05,
        metadata_text,
        ha="center",
        va="center",
        fontsize=9,
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        output_path,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )

    return output_path


# ============================================================
# Change-detection comparison
# ============================================================

def plot_change_comparison(
    raster_paths,
    period_labels,
    index_name,
    output_path,
    vmin=-0.4,
    vmax=0.4,
    cmap="RdYlGn",
    product_name="Sentinel-2 Level-2A",
    epsg="EPSG:32723",
):
    """
    Plot a vertical comparison of temporal change rasters
    using a fixed diverging color scale.
    """

    output_path = Path(
        output_path
    )

    pretty_labels = [
        label.replace(
            "-",
            " → ",
        )
        for label in period_labels
    ]

    fig, axes = plt.subplots(
        len(raster_paths),
        1,
        figsize=(8, 9.2),
        dpi=300,
        sharex=True,
        sharey=True,
    )

    if len(raster_paths) == 1:
        axes = [axes]

    last_image = None

    for i, (
        ax,
        raster_path,
        label,
    ) in enumerate(
        zip(
            axes,
            raster_paths,
            pretty_labels,
        )
    ):

        with rasterio.open(
            raster_path
        ) as src:

            data = src.read(1)
            bounds = src.bounds
            pixel_size = src.res[0]

        extent = [
            bounds.left,
            bounds.right,
            bounds.bottom,
            bounds.top,
        ]

        last_image = ax.imshow(
            data,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            extent=extent,
            origin="upper",
        )

        ax.set_title(
            label,
            fontsize=12,
            fontweight="bold",
            pad=6,
        )

        ax.set_ylabel(
            "Northing (m)"
        )

        if i == len(axes) - 1:
            ax.set_xlabel(
                "Easting (m)"
            )
        else:
            ax.set_xlabel("")

        add_north_arrow(
            ax
        )

        add_scale_bar(
            ax,
            pixel_size=pixel_size,
            bar_length_m=500,
        )

        ax.ticklabel_format(
            style="plain",
            axis="both",
            useOffset=False,
        )

        ax.grid(False)

    fig.suptitle(
        f"{index_name} change detection",
        fontsize=16,
        fontweight="bold",
        y=0.965,
    )

    fig.subplots_adjust(
        left=0.12,
        right=0.94,
        top=0.90,
        bottom=0.18,
        hspace=0.08,
    )

    cbar_ax = fig.add_axes(
        [
            0.20,
            0.105,
            0.60,
            0.025,
        ]
    )

    cbar = fig.colorbar(
        last_image,
        cax=cbar_ax,
        orientation="horizontal",
    )

    cbar.set_label(
        f"{index_name} change "
        f"(negative = decrease; "
        f"positive = increase)"
    )

    metadata_text = (
        f"Data source: {product_name} | "
        f"Periods: "
        f"{', '.join(pretty_labels)} | "
        f"CRS: {epsg}"
    )

    fig.text(
        0.5,
        0.04,
        metadata_text,
        ha="center",
        va="center",
        fontsize=9,
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        output_path,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )

    return output_path


# ============================================================
# Recanto spectral-index overview
# ============================================================

def plot_recanto_overview(
    state_raster_paths,
    state_labels,
    change_raster_paths,
    change_labels,
    index_name,
    output_path,
    state_vmin=-1,
    state_vmax=1,
    change_vmin=-0.4,
    change_vmax=0.4,
    state_cmap="Blues",
    change_cmap="RdBu",
    product_name="Sentinel-2 Level-2A",
    epsg="EPSG:32723",
):
    """
    Create a 3 x 2 overview figure for the Recanto sector.

    Left column:
        spectral index maps for 2019, 2022 and 2025.

    Right column:
        temporal change maps for the corresponding periods.
    """

    output_path = Path(
        output_path
    )

    fig, axes = plt.subplots(
        3,
        2,
        figsize=(10, 13),
        dpi=300,
        sharex=True,
        sharey=True,
    )

    last_state_image = None
    last_change_image = None

    for row in range(3):

        # --------------------------------------------------
        # Left column: spectral index state
        # --------------------------------------------------

        ax_state = axes[
            row,
            0,
        ]

        state_path = (
            state_raster_paths[
                row
            ]
        )

        state_label = (
            state_labels[
                row
            ]
        )

        with rasterio.open(
            state_path
        ) as src:

            state_data = src.read(1)
            state_bounds = src.bounds
            state_pixel_size = src.res[0]

        state_extent = [
            state_bounds.left,
            state_bounds.right,
            state_bounds.bottom,
            state_bounds.top,
        ]

        last_state_image = (
            ax_state.imshow(
                state_data,
                cmap=state_cmap,
                vmin=state_vmin,
                vmax=state_vmax,
                extent=state_extent,
                origin="upper",
            )
        )

        ax_state.set_title(
            state_label,
            fontsize=11,
            fontweight="bold",
            pad=6,
        )

        ax_state.set_ylabel(
            "Northing (m)"
        )

        ax_state.ticklabel_format(
            style="plain",
            axis="both",
            useOffset=False,
        )

        ax_state.xaxis.set_major_locator(
            MaxNLocator(
                nbins=4
            )
        )

        ax_state.yaxis.set_major_locator(
            MaxNLocator(
                nbins=4
            )
        )

        if row < 2:
            ax_state.tick_params(
                axis="x",
                labelbottom=False,
            )

        ax_state.grid(
            False
        )

        add_north_arrow(
            ax_state
        )

        add_scale_bar(
            ax_state,
            pixel_size=state_pixel_size,
            bar_length_m=200,
        )

        # --------------------------------------------------
        # Right column: temporal change
        # --------------------------------------------------

        ax_change = axes[
            row,
            1,
        ]

        change_path = (
            change_raster_paths[
                row
            ]
        )

        change_label = (
            change_labels[
                row
            ]
        )

        with rasterio.open(
            change_path
        ) as src:

            change_data = src.read(1)
            change_bounds = src.bounds
            change_pixel_size = src.res[0]

        change_extent = [
            change_bounds.left,
            change_bounds.right,
            change_bounds.bottom,
            change_bounds.top,
        ]

        last_change_image = (
            ax_change.imshow(
                change_data,
                cmap=change_cmap,
                vmin=change_vmin,
                vmax=change_vmax,
                extent=change_extent,
                origin="upper",
            )
        )

        ax_change.set_title(
            change_label,
            fontsize=11,
            fontweight="bold",
            pad=6,
        )

        ax_change.ticklabel_format(
            style="plain",
            axis="both",
            useOffset=False,
        )

        ax_change.xaxis.set_major_locator(
            MaxNLocator(
                nbins=4
            )
        )

        ax_change.yaxis.set_major_locator(
            MaxNLocator(
                nbins=4
            )
        )

        if row < 2:
            ax_change.tick_params(
                axis="x",
                labelbottom=False,
            )

        ax_change.tick_params(
            axis="y",
            labelleft=False,
        )

        ax_change.grid(
            False
        )

        add_north_arrow(
            ax_change
        )

        add_scale_bar(
            ax_change,
            pixel_size=change_pixel_size,
            bar_length_m=200,
        )

    axes[
        2,
        0,
    ].set_xlabel(
        "Easting (m)"
    )

    axes[
        2,
        1,
    ].set_xlabel(
        "Easting (m)"
    )

    fig.suptitle(
        (
            f"Recanto sector: "
            f"{index_name} and temporal change"
        ),
        fontsize=15,
        fontweight="bold",
        y=0.97,
    )

    fig.subplots_adjust(
        left=0.10,
        right=0.94,
        top=0.93,
        bottom=0.16,
        hspace=0.16,
        wspace=0.08,
    )

    cbar_ax_state = (
        fig.add_axes(
            [
                0.10,
                0.09,
                0.36,
                0.02,
            ]
        )
    )

    cbar_state = fig.colorbar(
        last_state_image,
        cax=cbar_ax_state,
        orientation="horizontal",
    )

    cbar_state.set_label(
        index_name
    )

    cbar_ax_change = (
        fig.add_axes(
            [
                0.58,
                0.09,
                0.36,
                0.02,
            ]
        )
    )

    cbar_change = fig.colorbar(
        last_change_image,
        cax=cbar_ax_change,
        orientation="horizontal",
    )

    cbar_change.set_label(
        f"{index_name} change "
        f"(negative = decrease; "
        f"positive = increase)"
    )

    metadata_text = (
        f"Data source: {product_name} | "
        f"Years: {', '.join(state_labels)} | "
        f"Change periods: "
        f"{', '.join(change_labels)} | "
        f"CRS: {epsg}"
    )

    fig.text(
        0.5,
        0.04,
        metadata_text,
        ha="center",
        va="center",
        fontsize=8.5,
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        output_path,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )

    return output_path


# ============================================================
# Recanto RGB overview + detailed water-land interfaces
# ============================================================

def plot_recanto_overview_zoom(
    rgb_raster_path,
    recanto_polygon_path,
    shoreline_paths,
    shoreline_labels,
    output_path,
    zoom_buffer=120,
):
    """
    Create a two-panel figure.

    Panel A:
        Sentinel-2 RGB overview of the Itaipuacu coastal
        study area, with the Recanto sector highlighted.

    Panel B:
        Detailed view of the Recanto sector showing
        MNDWI-derived water-land interfaces for
        2019, 2022 and 2025.
    """

    rgb_raster_path = Path(
        rgb_raster_path
    )

    recanto_polygon_path = Path(
        recanto_polygon_path
    )

    output_path = Path(
        output_path
    )

    # --------------------------------------------------
    # Read Sentinel-2 RGB
    # --------------------------------------------------

    with rasterio.open(
        rgb_raster_path
    ) as src:

        rgb = src.read(
            [1, 2, 3]
        )

        bounds = src.bounds
        raster_crs = src.crs
        pixel_size = abs(
            src.transform.a
        )

    # RGB GeoTIFF is uint8: 0-255.
    # Matplotlib RGB expects values from 0 to 1.
    rgb = np.transpose(
        rgb,
        (1, 2, 0),
    ).astype(
        np.float32
    )

    rgb /= 255.0

    # Pixels equal to zero in every channel are NoData.
    valid_rgb = np.any(
        rgb > 0,
        axis=2,
    )

    rgba = np.dstack(
        [
            rgb,
            valid_rgb.astype(
                np.float32
            ),
        ]
    )

    extent = [
        bounds.left,
        bounds.right,
        bounds.bottom,
        bounds.top,
    ]

    # --------------------------------------------------
    # Read Recanto focus AOI
    # --------------------------------------------------

    recanto = gpd.read_file(
        recanto_polygon_path
    )

    if recanto.crs != raster_crs:
        recanto = recanto.to_crs(
            raster_crs
        )

    # --------------------------------------------------
    # Read water-land interfaces
    # --------------------------------------------------

    if len(
        shoreline_paths
    ) != len(
        shoreline_labels
    ):
        raise ValueError(
            "shoreline_paths and shoreline_labels "
            "must have the same length."
        )

    colors = [
        "#E69F00",
        "#CC79A7",
        "#009E73",
    ]

    if len(
        shoreline_paths
    ) > len(
        colors
    ):
        raise ValueError(
            "More shoreline layers were supplied "
            "than available plotting colors."
        )

    shoreline_layers = []

    for (
        path,
        label,
        color,
    ) in zip(
        shoreline_paths,
        shoreline_labels,
        colors,
    ):

        shoreline = gpd.read_file(
            path
        )

        if shoreline.crs != raster_crs:
            shoreline = shoreline.to_crs(
                raster_crs
            )

        shoreline_layers.append(
            {
                "gdf": shoreline,
                "label": label,
                "color": color,
            }
        )

    # --------------------------------------------------
    # Determine Panel B extent from all waterlines
    # --------------------------------------------------

    shoreline_bounds = np.array(
        [
            layer[
                "gdf"
            ].total_bounds
            for layer
            in shoreline_layers
        ]
    )

    xmin = (
        shoreline_bounds[
            :,
            0,
        ].min()
    )

    ymin = (
        shoreline_bounds[
            :,
            1,
        ].min()
    )

    xmax = (
        shoreline_bounds[
            :,
            2,
        ].max()
    )

    ymax = (
        shoreline_bounds[
            :,
            3,
        ].max()
    )

    zoom_xmin = (
        xmin - zoom_buffer
    )

    zoom_xmax = (
        xmax + zoom_buffer
    )

    zoom_ymin = (
        ymin - zoom_buffer
    )

    zoom_ymax = (
        ymax + zoom_buffer
    )

    # --------------------------------------------------
    # Create figure
    # --------------------------------------------------

    fig = plt.figure(
        figsize=(12, 8.5),
        dpi=300,
    )

    grid = fig.add_gridspec(
        nrows=2,
        ncols=1,
        height_ratios=[
            0.85,
            1.35,
        ],
        hspace=0.28,
    )

    ax_overview = fig.add_subplot(
        grid[0]
    )

    ax_detail = fig.add_subplot(
        grid[1]
    )

    # ==================================================
    # PANEL A
    # ==================================================

    ax_overview.imshow(
        rgba,
        extent=extent,
        origin="upper",
    )

    recanto.boundary.plot(
        ax=ax_overview,
        color="red",
        linewidth=2.0,
        zorder=5,
    )

    recanto_centroid = (
        recanto.geometry
        .union_all()
        .centroid
    )

    ax_overview.annotate(
        "Recanto",
        xy=(
            recanto_centroid.x,
            recanto_centroid.y,
        ),
        xytext=(
            12,
            12,
        ),
        textcoords="offset points",
        fontsize=10,
        fontweight="bold",
        color="black",
        bbox={
            "boxstyle": "round,pad=0.25",
            "facecolor": "white",
            "edgecolor": "red",
            "alpha": 0.9,
        },
        arrowprops={
            "arrowstyle": "->",
            "color": "red",
            "linewidth": 1.4,
        },
        zorder=10,
    )

    ax_overview.set_title(
        (
            "A) Itaipuaçu coastal study area "
            "and Recanto sector"
        ),
        fontsize=12,
        fontweight="bold",
        pad=7,
    )

    ax_overview.set_xlabel(
        "Easting (m)"
    )

    ax_overview.set_ylabel(
        "Northing (m)"
    )

    ax_overview.ticklabel_format(
        style="plain",
        axis="both",
        useOffset=False,
    )

    ax_overview.xaxis.set_major_locator(
        MaxNLocator(
            nbins=7
        )
    )

    ax_overview.yaxis.set_major_locator(
        MaxNLocator(
            nbins=4
        )
    )

    ax_overview.grid(
        False
    )

    add_north_arrow(
        ax_overview
    )

    add_white_scale_bar(
        ax_overview,
        bar_length_m=1000,
    )

    # ==================================================
    # PANEL B
    # ==================================================

    ax_detail.imshow(
        rgba,
        extent=extent,
        origin="upper",
    )

    # --------------------------------------------------
    # Plot each interface twice:
    # white underlay + colored line
    # --------------------------------------------------

    for layer in shoreline_layers:

        layer[
            "gdf"
        ].plot(
            ax=ax_detail,
            color="white",
            linewidth=4.5,
            zorder=7,
        )

        layer[
            "gdf"
        ].plot(
            ax=ax_detail,
            color=layer[
                "color"
            ],
            linewidth=2.3,
            zorder=8,
        )

    ax_detail.set_xlim(
        zoom_xmin,
        zoom_xmax,
    )

    ax_detail.set_ylim(
        zoom_ymin,
        zoom_ymax,
    )

    ax_detail.set_title(
        (
            "B) MNDWI-derived water–land "
            "interface at Recanto"
        ),
        fontsize=12,
        fontweight="bold",
        pad=7,
    )

    ax_detail.set_xlabel(
        "Easting (m)"
    )

    ax_detail.set_ylabel(
        "Northing (m)"
    )

    ax_detail.ticklabel_format(
        style="plain",
        axis="both",
        useOffset=False,
    )

    ax_detail.xaxis.set_major_locator(
        MaxNLocator(
            nbins=5
        )
    )

    ax_detail.yaxis.set_major_locator(
        MaxNLocator(
            nbins=5
        )
    )

    ax_detail.grid(
        False
    )

    add_north_arrow(
        ax_detail
    )

    add_white_scale_bar(
    ax_detail,
    bar_length_m=200,
)

    # --------------------------------------------------
    # Legend
    # --------------------------------------------------

    legend_handles = []

    for layer in shoreline_layers:

        legend_handles.append(
            Line2D(
                [0],
                [0],
                color=layer[
                    "color"
                ],
                linewidth=3,
                label=layer[
                    "label"
                ],
            )
        )

    ax_detail.legend(
    handles=legend_handles,
    loc="lower right",
    bbox_to_anchor=(0.99, 0.08),
    fontsize=9,
    frameon=True,
    framealpha=0.9,
    edgecolor="0.4",
    )

    ax_detail.annotate(
    "Coastal structure",
    xy=(703700, 7458160),
    xytext=(703930, 7458130),
    fontsize=8.5,
    fontweight="bold",
    color="black",
    arrowprops={
        "arrowstyle": "->",
        "color": "black",
        "linewidth": 1.0,
    },
    bbox={
        "boxstyle": "round,pad=0.2",
        "facecolor": "white",
        "edgecolor": "0.4",
        "alpha": 0.85,
    },
    zorder=20,
)

    # --------------------------------------------------
    # Figure metadata
    # --------------------------------------------------

    fig.text(
        0.5,
        0.015,
        (
            "Background: Sentinel-2 Level-2A "
            "natural-color RGB, 26 June 2025 | "
            "Water–land interface: MNDWI > 0 | "
            "CRS: EPSG:32723"
        ),
        ha="center",
        va="bottom",
        fontsize=8.5,
    )

    # --------------------------------------------------
    # Save
    # --------------------------------------------------

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )

    print(
        f"Recanto overview figure saved: "
        f"{output_path}"
    )

    return output_path