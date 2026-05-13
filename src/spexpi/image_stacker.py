"""
Image stacking utilities for SPHEREx detector cutouts.

This module groups FITS cutouts by detector, subtracts the zodiacal-light
plane, masks pixels affected by selected FLAGS bits, and creates one mean
stack per detector. The returned cutouts are compatible with the plotting
interface used by ``image_plotter.py``.

Expected input FITS structure
-----------------------------
Each FITS file in ``data_dir`` is expected to contain at least the following
extensions:

``IMAGE``
    Science image plane. Its header must contain ``DETECTOR`` and should
    contain ``DATE-OBS`` for chronological sorting.

``FLAGS``
    Integer bit-mask plane. Pixels with any enabled fatal bit are excluded
    from the stack.

``ZODI``
    Zodiacal-light/background model plane. This is subtracted from ``IMAGE``
    before stacking.

The main public entry point is :func:`stack_images`.
"""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import DefaultDict, Iterable, MutableMapping, Optional, Sequence

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.wcs import WCS
from reproject import reproject_interp
from reproject.mosaicking import find_optimal_celestial_wcs

from .shared import create_object_name

# Default aperture/background radii in pixels. These are used only by the
# downstream plotting code to draw aperture overlays on the stacked images.
DEFAULT_APERTURE_RADIUS_PIX = 2.0
DEFAULT_BACKGROUND_INNER_RADIUS_PIX = 4.0
DEFAULT_BACKGROUND_OUTER_RADIUS_PIX = 6.0

# Detector FLAGS bits considered fatal for aperture/stacking purposes.
# Any pixel with at least one of these bits set is excluded from the mean stack.
DEFAULT_FATAL_FLAG_BITS = (
    0,
    1,
    2,
    4,
    6,
    7,
    9,
    10,
    11,
    14,
    15,
    17,
    19,
    22,
    24,
    26,
    27,
    28,
    29,
)

_REQUIRED_EXTENSIONS = ("IMAGE", "FLAGS", "ZODI")


@dataclass(frozen=True)
class DetectorCutout:
    """Intermediate cutout container for one exposure and one detector.

    Parameters
    ----------
    date_obs:
        Observation timestamp from the FITS header. Used for chronological
        sorting before stacking.
    data:
        ZODI-subtracted image cutout.
    header:
        FITS/WCS header associated with the cutout.
    flags:
        FLAGS cutout aligned with ``data``.
    source_file:
        Original FITS filename, retained for diagnostics.
    """

    date_obs: str
    data: np.ndarray
    header: fits.Header
    flags: np.ndarray
    source_file: str


@dataclass(frozen=True)
class StackResult:
    """Internal representation of one stacked detector image."""

    detector: str
    hdu: fits.PrimaryHDU
    n_input_images: int
    n_stacked_images: int


def _build_fatal_mask(fatal_flag_bits: Sequence[int]) -> np.uint32:
    """Return a bit mask with all selected fatal FLAGS bits enabled.

    Parameters
    ----------
    fatal_flag_bits:
        Iterable of integer bit positions. Bit ``b`` contributes ``1 << b``.

    Returns
    -------
    numpy.uint32
        Combined FLAGS bit mask.
    """

    return np.uint32(sum(1 << bit for bit in fatal_flag_bits))


def _as_uint_flags(flags: np.ndarray) -> np.ndarray:
    """Return FLAGS data as an unsigned integer array suitable for bit logic.

    ``reproject_interp`` may return floating-point arrays even when the source
    plane is an integer bit mask. For bitwise operations we need an integer
    dtype. Values are cast to ``uint32`` without changing the array shape.
    """

    flags_array = np.asarray(flags)
    if flags_array.dtype.kind not in ("i", "u", "b"):
        return flags_array.astype(np.uint32, copy=False)
    return flags_array.astype(np.uint32, copy=False)


def _crop_center(data: np.ndarray, output_shape: tuple[int, int]) -> np.ndarray:
    """Crop the central part of ``data`` to ``output_shape``.

    Cutouts created near image edges may differ by one pixel after reprojection.
    This helper makes them shape-compatible before stacking.

    Parameters
    ----------
    data:
        Two-dimensional input array.
    output_shape:
        Requested output shape as ``(ny, nx)``.

    Returns
    -------
    numpy.ndarray
        Center-cropped view/copy with the requested shape.

    Raises
    ------
    ValueError
        If ``data`` is smaller than ``output_shape`` in either dimension.
    """

    if data.ndim != 2:
        raise ValueError(f"Expected a 2D image array, got shape {data.shape!r}.")

    ny, nx = data.shape
    out_ny, out_nx = output_shape
    if out_ny > ny or out_nx > nx:
        raise ValueError(
            f"Cannot crop array with shape {data.shape!r} to larger shape {output_shape!r}."
        )

    start_y = (ny - out_ny) // 2
    start_x = (nx - out_nx) // 2
    return data[start_y: start_y + out_ny, start_x: start_x + out_nx]


def _photometry_radii_by_detector(
    detectors: Iterable[str],
    aperture_radius_pix: float,
    background_inner_radius_pix: float,
    background_outer_radius_pix: float,
) -> dict[str, tuple[float, float, float]]:
    """Create the aperture/background-radius mapping expected by plotters."""

    return {
        str(detector): (
            aperture_radius_pix,
            background_inner_radius_pix,
            background_outer_radius_pix,
        )
        for detector in detectors
    }


def _iter_fits_files(data_dir: str | os.PathLike[str]) -> list[Path]:
    """Return sorted FITS-like files from ``data_dir``.

    Non-FITS files are ignored. Sorting makes the execution deterministic.
    """

    directory = Path(data_dir)
    if not directory.exists():
        raise FileNotFoundError(f"Input directory does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {directory}")

    suffixes = {".fits", ".fit", ".fts", ".fits.gz", ".fit.gz", ".fts.gz"}
    files = [path for path in directory.iterdir() if path.is_file()]
    return sorted(path for path in files if any(str(path).lower().endswith(s) for s in suffixes))


def _validate_required_extensions(hdul: fits.HDUList, fits_path: Path) -> None:
    """Raise a clear error if an input FITS file misses a required extension."""

    available = {hdu.name for hdu in hdul}
    missing = [name for name in _REQUIRED_EXTENSIONS if name not in available]
    if missing:
        raise KeyError(f"{fits_path.name} is missing required FITS extension(s): {', '.join(missing)}")


def _reproject_plane_to_optimal_wcs(
    hdu: fits.ImageHDU | fits.PrimaryHDU,
    wcs: WCS,
    shape: tuple[int, int],
) -> np.ndarray:
    """Reproject one FITS image plane to the supplied WCS and shape."""

    reprojected, _ = reproject_interp(hdu, wcs, shape_out=shape)
    return reprojected


def _extract_detector_cutout(
    fits_path: Path,
    target: SkyCoord,
    image_size_arcsec: float,
) -> tuple[str, DetectorCutout]:
    """Read one FITS file and return a ZODI-subtracted detector cutout.

    Parameters
    ----------
    fits_path:
        Path to one FITS file.
    target:
        Target sky position.
    image_size_arcsec:
        Square cutout size in arcseconds.

    Returns
    -------
    tuple[str, DetectorCutout]
        Detector identifier and the extracted cutout.
    """

    with fits.open(fits_path, memmap=False) as hdul:
        _validate_required_extensions(hdul, fits_path)

        image_hdu = hdul["IMAGE"]
        flags_hdu = hdul["FLAGS"]
        zodi_hdu = hdul["ZODI"]

        detector = str(image_hdu.header.get("DETECTOR", "")).strip()
        if not detector:
            raise KeyError(f"{fits_path.name}: IMAGE header does not contain DETECTOR.")

        date_obs = str(image_hdu.header.get("DATE-OBS", ""))

        optimal_wcs, optimal_shape = find_optimal_celestial_wcs([image_hdu])
        cutout_size = image_size_arcsec * u.arcsec

        image = _reproject_plane_to_optimal_wcs(image_hdu, optimal_wcs, optimal_shape)
        image_cutout = Cutout2D(image, target, cutout_size, wcs=optimal_wcs, mode="partial")

        zodi = _reproject_plane_to_optimal_wcs(zodi_hdu, optimal_wcs, optimal_shape)
        zodi_cutout = Cutout2D(zodi, target, cutout_size, wcs=optimal_wcs, mode="partial")

        flags = _reproject_plane_to_optimal_wcs(flags_hdu, optimal_wcs, optimal_shape)
        flags_cutout = Cutout2D(
            _as_uint_flags(flags),
            target,
            cutout_size,
            wcs=optimal_wcs,
            mode="partial",
            fill_value=0,
        )

        science_minus_zodi = image_cutout.data - zodi_cutout.data
        cutout = DetectorCutout(
            date_obs=date_obs,
            data=science_minus_zodi,
            header=image_cutout.wcs.to_header(),
            flags=_as_uint_flags(flags_cutout.data),
            source_file=fits_path.name,
        )

    return detector, cutout


def _group_cutouts_by_detector(
    fits_files: Sequence[Path],
    target: SkyCoord,
    image_size_arcsec: float,
    verbose: bool,
) -> DefaultDict[str, list[DetectorCutout]]:
    """Load all FITS files and group extracted cutouts by detector."""

    detector_cutouts: DefaultDict[str, list[DetectorCutout]] = defaultdict(list)

    for fits_path in fits_files:
        detector, cutout = _extract_detector_cutout(fits_path, target, image_size_arcsec)
        detector_cutouts[detector].append(cutout)
        if verbose:
            print(f"Loaded {fits_path.name} -> detector D{detector}")

    return detector_cutouts


def _mean_stack_detector_cutouts(
    detector: str,
    cutouts: Sequence[DetectorCutout],
    fatal_mask: np.uint32,
    include_reference_image: bool,
) -> StackResult:
    """Create one mean image stack for a single detector.

    The first chronologically sorted cutout defines the output WCS/header and
    reference shape. By default it is also included in the mean stack. Set
    ``include_reference_image=False`` to reproduce the older behavior where the
    reference image was used only for shape/header alignment.
    """

    if not cutouts:
        raise ValueError(f"No cutouts supplied for detector {detector}.")

    sorted_cutouts = sorted(cutouts, key=lambda item: item.date_obs)
    reference = sorted_cutouts[0]
    reference_shape = reference.data.shape

    stacked = np.zeros(reference_shape, dtype=float)
    counts = np.zeros(reference_shape, dtype=float)

    input_cutouts = sorted_cutouts if include_reference_image else sorted_cutouts[1:]

    for cutout in input_cutouts:
        data = _crop_center(np.asarray(cutout.data, dtype=float), reference_shape)
        flags = _crop_center(_as_uint_flags(cutout.flags), reference_shape)

        valid_flags = (flags & fatal_mask) == 0
        valid_data = np.isfinite(data)
        valid_pixels = valid_flags & valid_data

        stacked[valid_pixels] += data[valid_pixels]
        counts[valid_pixels] += 1

    mean_image = np.full(reference_shape, np.nan, dtype=float)
    np.divide(stacked, counts, out=mean_image, where=counts > 0)

    header = reference.header.copy()
    header["NSTACK"] = (int(len(input_cutouts)), "Number of cutouts included in stack")
    header["NINPUT"] = (int(len(sorted_cutouts)), "Number of input cutouts for detector")
    header["INCLREF"] = (bool(include_reference_image), "Reference cutout included in mean stack")
    header["STACKTYP"] = ("MEAN", "Stack combination method")
    header["ZODISUB"] = (True, "IMAGE - ZODI before stacking")

    hdu = fits.PrimaryHDU(mean_image, header=header)
    return StackResult(
        detector=detector,
        hdu=hdu,
        n_input_images=len(sorted_cutouts),
        n_stacked_images=len(input_cutouts),
    )


def _save_stacked_hdu(
    result: StackResult,
    output_dir: str | os.PathLike[str],
    object_name: str,
    image_size_arcsec: float,
    overwrite: bool,
) -> Path:
    """Write one stacked detector image to disk and return the saved path."""

    directory = Path(output_dir + "/fits")
    directory.mkdir(parents=True, exist_ok=True)

    size_label = f"{image_size_arcsec:g}"
    filename = f"{object_name}_D{result.detector}_{size_label}_arcsec_cutout.fits"
    output_path = directory / filename
    result.hdu.writeto(output_path, overwrite=overwrite)
    return output_path


def stack_images(
    ra: float,
    dec: float,
    data_dir: str | os.PathLike[str],
    output_dir: str | os.PathLike[str],
    object_name: Optional[str] = None,
    image_size_arcsec: float = 100,
    save_fits: bool = False,
    aperture_radius_pix: float = DEFAULT_APERTURE_RADIUS_PIX,
    background_inner_radius_pix: float = DEFAULT_BACKGROUND_INNER_RADIUS_PIX,
    background_outer_radius_pix: float = DEFAULT_BACKGROUND_OUTER_RADIUS_PIX,
    fatal_flag_bits: Sequence[int] = DEFAULT_FATAL_FLAG_BITS,
    include_reference_image: bool = True,
    overwrite: bool = True,
    verbose: bool = True,
) -> list[MutableMapping[str, object]]:
    """Stack SPHEREx cutouts by detector and optionally save FITS products.

    Parameters
    ----------
    ra, dec:
        Target sky coordinates in decimal degrees.
    data_dir:
        Directory containing input FITS files. Files without FITS-like suffixes
        are ignored.
    output_dir:
        Directory where stacked FITS products are written when ``save_fits`` is
        ``True``.
    object_name:
        Optional source/object name used in output filenames. If omitted, a
        coordinate-based name is generated from ``ra`` and ``dec``.
    image_size_arcsec:
        Square cutout size in arcseconds.
    save_fits:
        If ``True``, write one stacked FITS file per detector.
    aperture_radius_pix, background_inner_radius_pix, background_outer_radius_pix:
        Aperture and background-annulus radii in pixels. These values are not
        used for the stacking itself; they are returned for downstream plotting.
    fatal_flag_bits:
        FLAGS bit positions that should exclude pixels from the stack.
    include_reference_image:
        If ``True`` (recommended), include the first chronologically sorted
        cutout in the mean stack. If ``False``, reproduce the older behavior
        where the first cutout only supplied the reference shape/header.
    overwrite:
        If ``True``, overwrite existing FITS outputs when ``save_fits`` is
        enabled.
    verbose:
        Print concise progress messages.

    Returns
    -------
    list[dict]
        One dictionary per detector, sorted by detector identifier. Each
        dictionary contains:

        ``hdu``
            Primary HDU containing the mean stacked image.
        ``band``
            Detector label such as ``"D1"``.
        ``phot_radii``
            Tuple ``(aperture_radius, bg_inner_radius, bg_outer_radius)`` for
            downstream plotting.

    Raises
    ------
    FileNotFoundError
        If ``data_dir`` does not exist or contains no FITS files.
    ValueError
        If no valid detector cutouts could be created.
    """

    if image_size_arcsec <= 0:
        raise ValueError("image_size_arcsec must be positive.")
    if aperture_radius_pix <= 0:
        raise ValueError("aperture_radius_pix must be positive.")
    if background_inner_radius_pix <= aperture_radius_pix:
        raise ValueError("background_inner_radius_pix must be larger than aperture_radius_pix.")
    if background_outer_radius_pix <= background_inner_radius_pix:
        raise ValueError("background_outer_radius_pix must be larger than background_inner_radius_pix.")

    fits_files = _iter_fits_files(data_dir)
    if not fits_files:
        raise FileNotFoundError(f"No FITS files found in input directory: {data_dir}")

    source_name = object_name or create_object_name(
        ra,
        dec,
        precision=2,
        shortform=False,
        prefix="J",
        decimal=False,
    )

    target = SkyCoord(ra, dec, unit="deg")
    fatal_mask = _build_fatal_mask(fatal_flag_bits)

    if verbose:
        print(f"Stacking {len(fits_files)} FITS file(s) for {source_name}")

    detector_cutouts = _group_cutouts_by_detector(
        fits_files=fits_files,
        target=target,
        image_size_arcsec=image_size_arcsec,
        verbose=verbose,
    )
    if not detector_cutouts:
        raise ValueError("No detector cutouts were created from the input FITS files.")

    phot_radii = _photometry_radii_by_detector(
        detector_cutouts.keys(),
        aperture_radius_pix,
        background_inner_radius_pix,
        background_outer_radius_pix,
    )

    stacked_cutouts: list[MutableMapping[str, object]] = []

    for detector, cutouts in sorted(detector_cutouts.items(), key=lambda item: item[0]):
        result = _mean_stack_detector_cutouts(
            detector=detector,
            cutouts=cutouts,
            fatal_mask=fatal_mask,
            include_reference_image=include_reference_image,
        )

        if save_fits:
            output_path = _save_stacked_hdu(
                result=result,
                output_dir=output_dir,
                object_name=source_name,
                image_size_arcsec=image_size_arcsec,
                overwrite=overwrite,
            )
            if verbose:
                print(
                    f"Saved detector D{detector} stack "
                    f"({result.n_stacked_images}/{result.n_input_images} cutouts) -> {output_path}"
                )
        elif verbose:
            print(
                f"Created detector D{detector} stack "
                f"({result.n_stacked_images}/{result.n_input_images} cutouts)"
            )

        stacked_cutouts.append(
            {
                "hdu": result.hdu,
                "band": f"D{detector}",
                "phot_radii": phot_radii[str(detector)],
            }
        )

    return stacked_cutouts
