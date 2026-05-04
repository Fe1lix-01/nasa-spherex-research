"""
Utilities for plotting SPHEREx cutout images.

This module creates a compact diagnostic figure for one target.  The figure
contains one panel per detector/band cutout, a synthetic RGB panel made from
combined detector pairs, and an information panel with target coordinates.

The public entry point is :func:`plot_images`.
"""

from __future__ import annotations

import os
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import PIL.ImageOps
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from astropy.utils.exceptions import AstropyWarning
from astropy.visualization import make_lupton_rgb
from astropy.wcs import WCS
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import BoxStyle, Circle, Rectangle

from .shared import create_object_name, open_file

# Type aliases used throughout the module.
ImageArray = np.ndarray
PhotometryRadii = Tuple[float, float, float]
BandPair = Tuple[str, str, str]


@dataclass(frozen=True)
class ImageCutout:
    """
    Normalized representation of one image cutout.

    Parameters
    ----------
    band:
        Band or detector name shown in the plot, for example ``"D1"``.
    hdu:
        FITS HDU-like object containing a 2-D ``data`` array and a FITS
        ``header`` usable by :class:`astropy.wcs.WCS`.
    phot_radii:
        Three radii in pixels: source-aperture radius, inner background radius,
        and outer background radius.  These are drawn as one red aperture circle
        and two blue background-annulus circles.
    """

    band: str
    hdu: Any
    phot_radii: PhotometryRadii


@dataclass(frozen=True)
class PlotConfig:
    """
    Configuration for the image diagnostic plot.

    Parameters
    ----------
    image_contrast:
        Percentile margin used for image scaling.  A value of ``10`` uses the
        10th and 90th percentiles when estimating the display stretch.
    rows, cols:
        Subplot grid dimensions.
    figure_size:
        Matplotlib figure size in inches.
    label_fontsize:
        Font size used for band labels.
    info_fontsize:
        Font size used for the target information panel.
    dpi:
        Output resolution used when saving the figure.
    """

    image_contrast: float = 10.0
    rows: int = 5
    cols: int = 6
    figure_size: Tuple[float, float] = (5.0, 5.0)
    label_fontsize: float = 3.0
    info_fontsize: float = 4.5
    dpi: int = 600


DEFAULT_RGB_BAND_PAIRS: Tuple[BandPair, ...] = (
    ("D1", "D2", "D12"),
    ("D3", "D4", "D34"),
    ("D5", "D6", "D56"),
)

REQUIRED_IMAGE_KEYS = {"hdu", "band", "phot_radii"}


def plot_images(
    ra: float,
    dec: float,
    images: Sequence[Mapping[str, Any]],
    image_size: float,
    image_contrast: float = 10,
    object_name: Optional[str] = None,
    output_dir: str | os.PathLike[str] = tempfile.gettempdir(),
    save_plot: bool = True,
    open_plot: bool = False,
    plot_format: str = "png",
) -> Optional[str]:
    """
    Create a diagnostic image grid for a target.

    The plot includes:

    * one grayscale cutout per input image;
    * aperture/background-radius overlays on each grayscale cutout;
    * a synthetic RGB image built from the combined ``D1+D2``, ``D3+D4`` and
      ``D5+D6`` images, when all six required bands are present;
    * a final information panel with target name, coordinates, image size and
      orientation note.

    Parameters
    ----------
    ra:
        Target right ascension in decimal degrees.
    dec:
        Target declination in decimal degrees.
    images:
        Sequence of dictionaries describing the cutouts to plot.  Each entry
        must contain:

        ``"hdu"``
            FITS HDU-like object with ``data`` and ``header`` attributes.
        ``"band"``
            Band label, for example ``"D1"``.
        ``"phot_radii"``
            Three numeric radii in pixels: aperture radius, background inner
            radius and background outer radius.

    image_size:
        Width/height of the cutout in arcseconds.  This value is displayed in
        the information panel.
    image_contrast:
        Percentile margin used for scaling grayscale and RGB images.  Must be in
        the interval ``[0, 50)``.  Higher values increase the contrast by using a
        narrower percentile range.
    object_name:
        Optional display and filename prefix.  If omitted, a coordinate-based
        name is generated from ``ra`` and ``dec``.
    output_dir:
        Directory where the image plot is written when ``save_plot=True``.
    save_plot:
        Save the generated plot to disk when ``True``.
    open_plot:
        Open the generated file after saving it.  This is ignored when
        ``save_plot=False``.
    plot_format:
        File format passed to Matplotlib, for example ``"png"`` or ``"pdf"``.

    Returns
    -------
    str or None
        Absolute path of the saved figure when ``save_plot=True``.  Returns
        ``None`` when no file is written.

    Raises
    ------
    ValueError
        If required image entries are missing, if image data are not 2-D arrays,
        if photometry radii are invalid, or if the RGB-composite detector bands
        are incomplete.
    """

    config = PlotConfig(image_contrast=float(image_contrast))
    cutouts = _normalize_cutouts(images)
    _validate_config(config)

    target_name = create_object_name(ra, dec, precision=2, shortform=False, prefix="J", decimal=False)
    source_name = object_name or target_name
    output_path = _build_output_path(source_name, output_dir, plot_format)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=AstropyWarning)
        figure = _create_figure(config)
        next_panel = _plot_cutout_panels(figure, cutouts, config, start_panel=1)
        next_panel = _plot_rgb_panel(figure, cutouts, config, next_panel)
        _plot_information_panel(figure, config, next_panel, source_name, ra, dec, image_size)

        saved_path: Optional[str] = None
        if save_plot:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            figure.savefig(output_path, dpi=config.dpi, bbox_inches="tight", format=plot_format)
            saved_path = str(output_path)

        plt.close(figure)

    if save_plot and open_plot and saved_path is not None:
        open_file(saved_path)

    return saved_path


def _normalize_cutouts(images: Sequence[Mapping[str, Any]]) -> List[ImageCutout]:
    """
    Convert input dictionaries into validated :class:`ImageCutout` instances.

    This function keeps the public API flexible while giving the implementation
    a stable internal representation.
    """

    if not images:
        raise ValueError("At least one image cutout is required.")

    cutouts: List[ImageCutout] = []
    for index, image in enumerate(images, start=1):
        missing_keys = REQUIRED_IMAGE_KEYS.difference(image.keys())
        if missing_keys:
            missing = ", ".join(sorted(missing_keys))
            raise ValueError(f"Image entry {index} is missing required key(s): {missing}")

        band = str(image["band"])
        hdu = image["hdu"]
        phot_radii = _normalize_photometry_radii(image["phot_radii"], band)
        _validate_hdu(hdu, band)
        cutouts.append(ImageCutout(band=band, hdu=hdu, phot_radii=phot_radii))

    return cutouts


def _normalize_photometry_radii(values: Iterable[Any], band: str) -> PhotometryRadii:
    """Return the three photometry radii as positive floats."""

    try:
        radii = tuple(float(value) for value in values)
    except TypeError as exc:
        raise ValueError(f"phot_radii for band {band!r} must contain three numeric values.") from exc

    if len(radii) != 3:
        raise ValueError(f"phot_radii for band {band!r} must contain exactly three values.")
    if any(radius <= 0 for radius in radii):
        raise ValueError(f"phot_radii for band {band!r} must all be positive.")

    return radii  # type: ignore[return-value]


def _validate_hdu(hdu: Any, band: str) -> None:
    """Validate that an HDU-like object contains usable 2-D image data."""

    if not hasattr(hdu, "data") or not hasattr(hdu, "header"):
        raise ValueError(f"HDU for band {band!r} must provide 'data' and 'header' attributes.")

    data = np.asarray(hdu.data)
    if data.ndim != 2:
        raise ValueError(f"HDU data for band {band!r} must be a 2-D image array; got shape {data.shape}.")
    if data.size == 0:
        raise ValueError(f"HDU data for band {band!r} is empty.")


def _validate_config(config: PlotConfig) -> None:
    """Validate plot configuration values that affect scaling and layout."""

    if not 0 <= config.image_contrast < 50:
        raise ValueError("image_contrast must be in the interval [0, 50).")
    if config.rows <= 0 or config.cols <= 0:
        raise ValueError("rows and cols must both be positive.")


def _create_figure(config: PlotConfig) -> Figure:
    """Create and configure the Matplotlib figure used for the diagnostic plot."""

    plt.rcParams.update({"font.family": "Arial"})
    figure = plt.figure(figsize=config.figure_size)
    figure.subplots_adjust(wspace=0, hspace=0.1, right=1.0)
    return figure


def _plot_cutout_panels(
    figure: Figure,
    cutouts: Sequence[ImageCutout],
    config: PlotConfig,
    start_panel: int,
) -> int:
    """
    Plot all individual grayscale cutouts.

    Returns the next free subplot index.
    """

    panel = start_panel
    for cutout in cutouts:
        _plot_single_cutout(figure, config, panel, cutout)
        print(f"Plotted {cutout.band} band image")
        panel += 1
    return panel


def _plot_single_cutout(figure: Figure, config: PlotConfig, panel: int, cutout: ImageCutout) -> None:
    """Plot one grayscale cutout with WCS projection and photometry overlays."""

    data = np.asarray(cutout.hdu.data, dtype=float)
    wcs = WCS(cutout.hdu.header)
    axis = figure.add_subplot(config.rows, config.cols, panel, projection=wcs)

    center_x, center_y = _image_center_xy(data)
    axis.scatter(center_x, center_y, s=0.2, c="red")
    _draw_photometry_radii(axis, center_x, center_y, cutout.phot_radii)
    _draw_panel_label(axis, cutout.band, config.label_fontsize, alpha=0.5)
    _draw_panel_border(axis)

    vmin, vmax = _robust_limits(data, config.image_contrast)
    axis.imshow(data, vmin=vmin, vmax=vmax, cmap="gray_r", origin="lower")
    axis.axis("off")


def _plot_rgb_panel(
    figure: Figure,
    cutouts: Sequence[ImageCutout],
    config: PlotConfig,
    panel: int,
) -> int:
    """
    Plot the synthetic RGB panel from detector-pair averages.

    The current SPHEREx convention is:

    * blue  = average of ``D1`` and ``D2``;
    * green = average of ``D3`` and ``D4``;
    * red   = average of ``D5`` and ``D6``.
    """

    image_data = {cutout.band: np.asarray(cutout.hdu.data, dtype=float) for cutout in cutouts}
    combined = _combine_band_pairs(image_data, DEFAULT_RGB_BAND_PAIRS)

    blue = combined["D12"]
    green = combined["D34"]
    red = combined["D56"]
    label = "D56-D34-D12"

    _plot_color_image(figure, config, panel, red, green, blue, label)
    print("Plotted color image")
    return panel + 1


def _combine_band_pairs(image_data: Mapping[str, ImageArray], band_pairs: Sequence[BandPair]) -> Dict[str, ImageArray]:
    """Average detector-pair images after center-cropping them to a common shape."""

    combined: Dict[str, ImageArray] = {}
    for band_1, band_2, combined_name in band_pairs:
        missing = [band for band in (band_1, band_2) if band not in image_data]
        if missing:
            missing_text = ", ".join(missing)
            raise ValueError(f"Cannot create RGB image because required band(s) are missing: {missing_text}")

        image_1, image_2 = crop_to_common_center(image_data[band_1], image_data[band_2])
        combined[combined_name] = np.nanmean(np.stack([image_1, image_2]), axis=0)

    return combined


def _plot_color_image(
    figure: Figure,
    config: PlotConfig,
    panel: int,
    red: ImageArray,
    green: ImageArray,
    blue: ImageArray,
    label: str,
    invert: bool = False,
) -> None:
    """Plot a PIL RGB image made from three 2-D science arrays."""

    red, green, blue = crop_to_common_center(red, green, blue)
    red_channel = _array_to_lupton_grayscale(red, config.image_contrast)
    green_channel = _array_to_lupton_grayscale(green, config.image_contrast)
    blue_channel = _array_to_lupton_grayscale(blue, config.image_contrast)

    if invert:
        red_channel = PIL.ImageOps.invert(red_channel)
        green_channel = PIL.ImageOps.invert(green_channel)
        blue_channel = PIL.ImageOps.invert(blue_channel)

    rgb_image = Image.merge("RGB", (red_channel, green_channel, blue_channel))
    axis = figure.add_subplot(config.rows, config.cols, panel)
    _draw_panel_label(axis, label, config.label_fontsize, alpha=0.7)
    _draw_panel_border(axis)
    axis.imshow(rgb_image, origin="lower")
    axis.axis("off")


def _plot_information_panel(
    figure: Figure,
    config: PlotConfig,
    panel: int,
    source_name: str,
    ra: float,
    dec: float,
    image_size: float,
) -> None:
    """Plot the final text panel containing target and cutout metadata."""

    axis = figure.add_subplot(config.rows, config.cols, panel)
    lines = [
        (0.80, source_name),
        (0.65, rf"$\alpha$ = {ra:.7f}"),
        (0.50, rf"$\delta$ = {dec:.7f}"),
        (0.35, f"Size = {int(image_size)} arcsec"),
        (0.20, "North up, East left"),
    ]

    for y_position, text in lines:
        axis.text(0.1, y_position, text, fontsize=config.info_fontsize, transform=axis.transAxes)

    axis.axis("off")


def _draw_photometry_radii(axis: Axes, center_x: float, center_y: float, radii: PhotometryRadii) -> None:
    """Draw source-aperture and background-annulus radii on an axis."""

    aperture_radius, background_inner_radius, background_outer_radius = radii
    circle_specs = [
        (aperture_radius, "red"),
        (background_inner_radius, "blue"),
        (background_outer_radius, "blue"),
    ]

    for radius, color in circle_specs:
        axis.add_patch(Circle((center_x, center_y), radius=radius, edgecolor=color, facecolor="none", lw=0.5))


def _draw_panel_label(axis: Axes, label: str, fontsize: float, alpha: float) -> None:
    """Draw the small white band-label box used in image panels."""

    axis.text(
        0.03,
        0.93,
        label,
        color="black",
        fontsize=fontsize,
        transform=axis.transAxes,
        bbox={
            "facecolor": "white",
            "alpha": alpha,
            "linewidth": 0.1,
            "boxstyle": BoxStyle("Square", pad=0.3),
        },
    )


def _draw_panel_border(axis: Axes) -> None:
    """Draw a thin border around an image panel."""

    axis.add_patch(Rectangle((0, 0), 1, 1, fill=False, lw=0.2, ec="black", transform=axis.transAxes))


def _image_center_xy(data: ImageArray) -> Tuple[float, float]:
    """
    Return the center of a 2-D image in Matplotlib x/y coordinates.

    Numpy arrays are shaped as ``(ny, nx)``.  Matplotlib positions use
    ``(x, y)``, therefore the order is intentionally reversed here.
    """

    ny, nx = data.shape
    return nx / 2.0, ny / 2.0


def crop_to_common_center(*arrays: ImageArray) -> Tuple[ImageArray, ...]:
    """
    Center-crop all arrays to the smallest common ``(ny, nx)`` shape.

    This is useful when detector cutouts differ by one or more pixels because of
    WCS rounding or edge effects.  The function never pads data; it only crops.
    """

    if not arrays:
        raise ValueError("At least one array is required.")

    shapes = [np.asarray(array).shape for array in arrays]
    if any(len(shape) != 2 for shape in shapes):
        raise ValueError(f"All arrays must be 2-D; got shapes: {shapes}")

    target_ny = min(shape[0] for shape in shapes)
    target_nx = min(shape[1] for shape in shapes)
    return tuple(_crop_center(np.asarray(array), target_ny, target_nx) for array in arrays)


def _crop_center(data: ImageArray, target_ny: int, target_nx: int) -> ImageArray:
    """Center-crop a 2-D array to ``target_ny`` by ``target_nx`` pixels."""

    ny, nx = data.shape
    start_y = max((ny - target_ny) // 2, 0)
    start_x = max((nx - target_nx) // 2, 0)
    return data[start_y: start_y + target_ny, start_x: start_x + target_nx]


def _array_to_lupton_grayscale(data: ImageArray, image_contrast: float) -> Image.Image:
    """Convert a 2-D image array to a PIL grayscale image using Lupton scaling."""

    vmin, vmax = _robust_limits(data, image_contrast)
    stretch = max(vmax - vmin, np.finfo(float).eps)
    rgb_array = make_lupton_rgb(data, data, data, minimum=vmin, stretch=stretch, Q=0)
    return Image.fromarray(rgb_array).convert("L")


def _robust_limits(data: ImageArray, image_contrast: float) -> Tuple[float, float]:
    """
    Calculate robust image-display limits.

    The lower limit is anchored to the median and median absolute deviation.
    The upper limit uses the distance between two percentiles controlled by
    ``image_contrast``.  This preserves the behavior of the original script
    while handling fully invalid or constant arrays more safely.
    """

    finite = np.asarray(data, dtype=float)[np.isfinite(data)]
    if finite.size == 0:
        return 0.0, 1.0

    lo = image_contrast
    hi = 100.0 - image_contrast
    median = float(np.nanmedian(finite))
    mad = float(np.nanmedian(np.abs(finite - median)))
    percentile_range = float(np.nanpercentile(finite, hi) - np.nanpercentile(finite, lo))

    vmin = median - 2.0 * mad
    vmax = median + 2.0 * percentile_range
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
        spread = float(np.nanstd(finite)) or 1.0
        vmin = median - spread
        vmax = median + spread
    return vmin, vmax


def _build_output_path(source_name: str, output_dir: str | os.PathLike[str], plot_format: str) -> Path:
    """Build the output filename used for saved diagnostic plots."""

    safe_name = source_name.strip() or "target"
    safe_name = safe_name.replace(os.sep, "_")
    if os.altsep:
        safe_name = safe_name.replace(os.altsep, "_")

    clean_format = plot_format.lower().lstrip(".") or "png"
    return Path(output_dir).expanduser().resolve() / f"{safe_name}_images.{clean_format}"
