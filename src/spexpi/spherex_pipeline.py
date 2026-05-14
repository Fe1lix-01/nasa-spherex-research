from __future__ import annotations

import concurrent.futures
import csv
import json
import logging
import math
import re
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
import pyvo
import requests
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.stats import SigmaClip
from astropy.table import Table
from astropy.time import Time
from astropy.units import Unit
from astropy.wcs import WCS
from matplotlib.colors import to_rgba
from matplotlib.lines import Line2D
from matplotlib.ticker import ScalarFormatter
from photutils.aperture import CircularAnnulus, CircularAperture, ApertureStats, aperture_photometry
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import shift as ndi_shift
from tqdm.auto import tqdm

logging.getLogger("astropy").setLevel(logging.WARNING)


@dataclass
class PipelineConfig:
    """
    User-facing configuration for the SPHEREx aperture/PSF extraction pipeline.

    The SPHEREx data release is deliberately not a configurable parameter.  The
    pipeline infers it from the downloaded image URLs or local file paths (for
    example, paths containing ``/spherex/qr2/``).  Calibration S3 paths are then
    built from that inferred release so image data and calibration files remain
    consistent.
    """

    # ------------------------------------------------------------------
    # IRSA query and parallel execution
    # ------------------------------------------------------------------
    tap_url: str = "https://irsa.ipac.caltech.edu/TAP"
    """IRSA TAP service URL used to discover SPHEREx image artifacts."""

    cutout_size_arcsec: int = 180
    """Angular size of the requested IRSA HTTP cutout, in arcseconds."""

    max_workers: int = 8
    """Maximum number of worker threads used for download/open operations."""

    retries: int = 3
    """Number of attempts for transient download/open failures."""

    retry_delay_sec: float = 5.0
    """Delay between retry attempts, in seconds."""

    # ------------------------------------------------------------------
    # Optional astrometric propagation for high proper-motion targets
    # ------------------------------------------------------------------
    reference_epoch_yr: float | None = None
    """Reference epoch of the input coordinates, as a decimal year; None disables propagation."""

    pmra_masyr: float | None = None
    """Proper motion in right ascension, mu_alpha*cos(delta), in mas/yr."""

    pmdec_masyr: float | None = None
    """Proper motion in declination, mu_delta, in mas/yr."""

    log_epoch_projection: bool = False
    """Print per-cutout propagated coordinates when proper-motion propagation is active."""

    # ------------------------------------------------------------------
    # Download and local cache settings
    # ------------------------------------------------------------------
    download_dir: str = "spherex_downloads"
    """Base directory containing one cached FITS subdirectory per object."""

    redownload_existing_files: bool = False
    """If True, overwrite cached FITS cutouts instead of reusing them."""

    show_download_progress: bool = True
    """Show tqdm progress bars for download and file-opening operations."""

    request_timeout_sec: float = 120.0
    """HTTP request timeout, in seconds, for IRSA cutout downloads."""

    download_backend: str = "http"
    """Cutout backend: 'http' uses IRSA cutouts; 's3'/'s3_cutout' extract local cutouts from S3 parent FITS files."""

    s3_bucket: str = "nasa-irsa-spherex"
    """Public S3 bucket containing SPHEREx image and calibration products."""

    s3_cutout_size_px: int = 32
    """Linear size, in detector pixels, of locally written S3 cutouts."""

    s3_cutout_min_size_px: int = 16
    """Minimum allowed S3 cutout size, in pixels."""

    s3_cutout_fallback_to_http: bool = True
    """If True, fall back to IRSA HTTP cutouts when S3 cutout extraction fails."""

    s3_cutout_update_alt_wcs: bool = True
    """Write CRPIX1A/CRPIX2A parent-detector offsets into S3-generated cutouts."""

    query_irsa_for_cutouts: bool = True
    """If True, discover cutouts with IRSA TAP; if False, use cached files only."""

    cached_cutout_glob: str = "*.fits"
    """Glob pattern used when reading already cached local cutouts."""

    # ------------------------------------------------------------------
    # Solid-angle pixel map (SAPM) calibration
    # ------------------------------------------------------------------
    cache_sapm_files: bool = True
    """Cache detector solid-angle pixel maps locally after first use."""

    sapm_cache_dir: str = "spherex_calibration_files/spherex_sapm_cache"
    """Base directory for cached solid-angle pixel maps, grouped by inferred release."""

    redownload_sapm_files: bool = False
    """If True, refresh cached solid-angle pixel maps from S3."""

    sapm_collection: str = "cal-sapm-v2-2025-164"
    """Calibration collection name for the solid-angle pixel maps."""

    # ------------------------------------------------------------------
    # Aperture photometry and local background estimation
    # ------------------------------------------------------------------
    aperture_radii_pix: tuple[float, ...] = (1.0, 2.0, 3.0)
    """Aperture radii, in pixels, measured for each cutout."""

    selected_aperture_radius_pix: float = 2.0
    """Fallback aperture radius selected when building the final aperture spectrum."""

    selected_aperture_radius_by_detector: Mapping[int, float] | None = None
    """Optional detector-specific selected aperture radii, in pixels.

    Example: ``{1: 1.0, 2: 1.0, 3: 2.0, 4: 2.0, 5: 3.0, 6: 3.0}``.
    Detectors omitted from the mapping fall back to ``selected_aperture_radius_pix``.
    Detector-specific selected radii are measured automatically even when they
    are not listed in ``aperture_radii_pix``.
    """

    annulus_inner_scale: float = 2.0
    """Inner annulus radius as a multiple of the aperture radius."""

    annulus_outer_scale: float = 3.0
    """Outer annulus radius as a multiple of the aperture radius."""

    bg_method: str = "median"
    """Background estimator used in the annulus: 'mean', 'median', or 'mode'."""

    sigma_clip_sigma: float = 3.0
    """Sigma threshold used when clipping background-annulus pixels."""

    sigma_clip_maxiters: int = 5
    """Maximum number of sigma-clipping iterations for background estimation."""

    subtract_zodi: bool = True
    """Subtract the ZODI extension before photometry when it is available."""

    # ------------------------------------------------------------------
    # Photometry mode
    # ------------------------------------------------------------------
    photometry_method: str = "aperture"
    """Photometry mode: 'aperture', 'psf', or 'both'. If 'both', the pipeline writes independent aperture and PSF spectra/plots in one run."""

    # ------------------------------------------------------------------
    # PSF photometry
    # ------------------------------------------------------------------
    psf_kernel_radius_native: int = 5
    """Half-size of the rebinned native-pixel PSF kernel."""

    psf_shift_sign: float = 1.0
    """Sign convention applied to the subpixel PSF shift."""

    psf_fit_background_gradient: bool = False
    """If True, include linear x/y background-gradient terms in the PSF fit."""

    psf_min_valid_pixels: int = 6
    """Minimum number of unmasked pixels required for a valid PSF fit."""

    psf_max_reduced_chi2: float | None = None
    """Optional maximum reduced chi-square above which PSF measurements are rejected."""

    enable_psf_local_grid_search: bool = True
    """If True, refine the PSF centroid with a local grid search around the WCS position."""

    psf_local_grid_half_range_pix: float = 1.0
    """Half-width of the PSF centroid grid search, in pixels."""

    psf_local_grid_step_pix: float = 0.5
    """Step size of the PSF centroid grid search, in pixels."""

    psf_local_grid_metric: str = "snr"
    """Metric used to choose the best PSF grid position: 'snr' or 'chi2'."""

    psf_grid_search_enabled_detectors: tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    """Detector numbers for which PSF local grid search is enabled."""

    # ------------------------------------------------------------------
    # Pixel flags, flux sanitation, and outlier rejection
    # ------------------------------------------------------------------
    bad_flag_bits: tuple[int, ...] = (0, 1, 2, 4, 6, 7, 9, 10, 11, 14, 15, 17, 19, 22, 24, 26, 27, 28, 29)
    """SPHEREx FLAGS bits treated as fatal and excluded from photometry."""

    aperture_flag_count_bits: tuple[int, ...] = (0, 1, 2, 4, 6, 7, 9, 10, 11, 14, 15, 17, 19, 22, 24, 26, 27, 28, 29)
    """FLAGS bits counted inside apertures for diagnostics."""

    sanitize_flux: bool = True
    """Remove non-finite flux/error values, zero placeholders, and invalid uncertainties before binning."""

    keep_negative_flux: bool = True
    """Keep negative background-subtracted fluxes; recommended for unbiased faint-source spectra."""

    remove_outliers: bool = False
    """Apply detector-wise wavelength-bin outlier rejection before final binning."""

    outlier_detectors: tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    """Detector numbers on which outlier rejection is applied."""

    outlier_nbr_of_bins: int = 8
    """Number of wavelength bins per detector used for local outlier statistics."""

    outlier_sigma: float = 3.0
    """Sigma threshold for MAD-based outlier rejection."""

    # ------------------------------------------------------------------
    # Spectral oversampling reduction
    # ------------------------------------------------------------------
    reduce_oversampling: bool = True
    """Bin repeated SPHEREx measurements to reduce spectral oversampling."""

    use_spectral_channels_for_binning: bool = False
    """Use spectral_channels calibration files for bin centers/edges when available."""

    spectral_channels_bin_by: str = "integrate"
    """Binning mode for spectral_channels: 'integrate', 'edges', or 'nearest'."""

    spectral_channels_min_points_per_bin: int = 1
    """Minimum number of measurements required in a spectral-channel bin."""

    spectral_channels_integrate_errors: str = "quadrature"
    """Uncertainty propagation for integrated bins: 'quadrature' or 'weighted'."""

    spectral_channels_collection: str | None = "cal-sch-v1-2026-106"
    """Optional spectral_channels calibration collection name used to build default S3 paths."""

    spectral_channels_s3_template: str | None = None
    """Optional S3 template for spectral_channels; may include {data_release} and {collection}."""

    spectral_channels_cache_dir: str = "spherex_calibration_files/spherex_spectral_channels_cache"
    """Base directory for cached spectral_channels calibration files."""

    redownload_spectral_channels: bool = False
    """If True, refresh cached spectral_channels calibration files from S3."""

    # ------------------------------------------------------------------
    # Output products and plotting
    # ------------------------------------------------------------------
    output_dir: str = "spherex_spectra"
    """Base output directory for spectra, plots, and optional manifests."""

    clip_flux_at_wavelength: float | None = None
    """Clip flux at wavelength (in microns)."""

    save_raw_measurements: bool = False
    """If True, write the per-cutout measurement table to FITS."""

    save_manifest: bool = False
    """If True, write CSV/JSONL processing manifests for cutouts and measurements."""

    manifest_format: str = "both"
    """Manifest output format: 'csv', 'jsonl', or 'both'."""

    plot_flux_lambda: bool = True
    """If True, plot spectra as F_lambda; otherwise plot the stored F_nu flux density."""

    plot_spectrum: bool = True
    """If True, create a diagnostic spectrum plot."""

    plot_format: str = "pdf"
    """File extension/format for saved diagnostic plots."""

    plot_color: str = "k"
    """Matplotlib color for the final diagnostic spectrum plot."""

    plot_spline: bool = True
    """If True, plot a smooth guide line over the spectrum plot."""

    spline_mode: str = "binned_median"
    """Spline mode for diagnostic plots: 'binned_median' for a broad-shape guide, or 'interpolate' to connect all points."""

    spline_n_bins: int = 35
    """Number of wavelength bins used by spline_mode='binned_median'. Lower values produce a smoother broad-shape guide."""

    spline_min_points_per_bin: int = 2
    """Minimum number of valid points required in a wavelength bin for the broad-shape spline."""

    spline_sigma_clip: float | None = 3.0
    """Optional sigma-clipping threshold inside each spline wavelength bin; None disables clipping."""

    plot_unbinned_points_with_binned_spline: bool = False
    """If True, plot unbinned points and overlay a dense PCHIP spline computed from the final binned spectrum."""

    plot_binned_points_with_unbinned_overlay: bool = False
    """If True together with plot_unbinned_points_with_binned_spline, also show the exact binned spectrum points used as spline anchors."""

    spline_density: int = 1000
    """Number of dense wavelength samples used to draw the spectrum spline/guide line."""

    plot_spectral_channel_overlay: bool = False
    """If True, overlay spectral-channel bin ranges on the spectrum plot."""

    plot_spectral_channel_overlay_detectors: tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    """Detector numbers whose spectral-channel bins are shown on the plot."""

    plot_spectral_channel_overlay_wl_min: float | None = None
    """Minimum wavelength, in microns, for the spectral-channel overlay."""

    plot_spectral_channel_overlay_wl_max: float | None = None
    """Maximum wavelength, in microns, for the spectral-channel overlay."""

    plot_vertical_line: boolean = False
    """If True, plot a vertical line at the wavelength specified using ``vertical_line_position``."""

    vertical_line_position: float = 0.0
    """Position of the vertical line in microns."""


def validate_config(cfg: PipelineConfig) -> None:
    """
    Validate the most important configuration values before the pipeline starts.

    The checks are intentionally lightweight: they catch common typos such as an
    unsupported download backend or photometry method without trying to validate
    every scientific choice.
    """
    backend = str(cfg.download_backend).lower().strip()
    if backend not in ("http", "s3", "s3_cutout"):
        raise ValueError(f"Unsupported download_backend={cfg.download_backend!r}; use 'http' or 's3_cutout'.")

    method = str(cfg.photometry_method).lower().strip()
    if method not in ("aperture", "psf", "both"):
        raise ValueError(f"Unsupported photometry_method={cfg.photometry_method!r}; use 'aperture', 'psf', or 'both'.")

    bg_method = str(cfg.bg_method).lower().strip()
    if bg_method not in ("mean", "median", "mode"):
        raise ValueError(f"Unsupported bg_method={cfg.bg_method!r}; use 'mean', 'median', or 'mode'.")

    if cfg.retries < 1:
        raise ValueError("cfg.retries must be at least 1.")

    if cfg.max_workers < 1:
        raise ValueError("cfg.max_workers must be at least 1.")

    if not cfg.aperture_radii_pix:
        raise ValueError("cfg.aperture_radii_pix must contain at least one radius.")

    if cfg.selected_aperture_radius_pix <= 0:
        raise ValueError("cfg.selected_aperture_radius_pix must be positive.")

    if cfg.selected_aperture_radius_by_detector is not None:
        for detector, radius in cfg.selected_aperture_radius_by_detector.items():
            detector = int(detector)
            if detector < 1 or detector > 6:
                raise ValueError("cfg.selected_aperture_radius_by_detector keys must be detector numbers 1..6.")
            if float(radius) <= 0:
                raise ValueError("cfg.selected_aperture_radius_by_detector radii must be positive.")

    if cfg.s3_cutout_size_px < cfg.s3_cutout_min_size_px:
        raise ValueError("cfg.s3_cutout_size_px must be >= cfg.s3_cutout_min_size_px.")


def get_selected_aperture_radius_pix(cfg: PipelineConfig, detector: int | None = None) -> float:
    """Return the aperture radius selected for one detector, falling back to the global value."""
    if detector is not None and cfg.selected_aperture_radius_by_detector is not None:
        try:
            radius = cfg.selected_aperture_radius_by_detector.get(int(detector))
        except AttributeError:
            radius = dict(cfg.selected_aperture_radius_by_detector).get(int(detector))
        if radius is not None:
            return float(radius)
    return float(cfg.selected_aperture_radius_pix)


def get_aperture_radii_for_detector(cfg: PipelineConfig, detector: int) -> tuple[float, ...]:
    """Return all aperture radii to measure for one detector.

    The configured ``aperture_radii_pix`` are preserved, and the detector-specific
    selected radius is appended when needed so the final spectrum can always be
    built from the requested radius.
    """
    radii: list[float] = []
    for radius in tuple(cfg.aperture_radii_pix):
        r = float(radius)
        if not any(np.isclose(r, existing) for existing in radii):
            radii.append(r)

    selected = get_selected_aperture_radius_pix(cfg, detector)
    if not any(np.isclose(selected, existing) for existing in radii):
        radii.append(selected)

    return tuple(radii)


def aperture_radius_matches_detector_selection(row: dict, aperture_radius_pix) -> bool:
    """Return True when an aperture measurement matches the requested selected radius."""
    measured_radius = float(row["aperture_radius_pix"])
    detector = int(row.get("detector", 0))

    if aperture_radius_pix is None:
        return True

    if isinstance(aperture_radius_pix, Mapping):
        target_radius = aperture_radius_pix.get(detector)
        if target_radius is None:
            return False
    else:
        target_radius = float(aperture_radius_pix)

    return bool(np.isclose(measured_radius, float(target_radius)))


def ensure_output_directories(base_dir: str) -> None:
    """Create the standard output subdirectories used by the pipeline."""
    Path(base_dir, "fits").mkdir(parents=True, exist_ok=True)
    Path(base_dir, "plots").mkdir(parents=True, exist_ok=True)


def make_object_name(ra: float, dec: float, object_name: str | None = None) -> str:
    """Return a provided object name or build a compact IAU-like name from RA/Dec."""
    if object_name:
        return object_name
    c = SkyCoord(ra, dec, unit="deg")
    return "J" + c.to_string("hmsdms", sep="", precision=1).replace(" ", "")


def safe_filename(text: str, max_len: int = 120) -> str:
    """Create a filesystem-safe filename component."""
    text = str(text).strip()
    text = re.sub(r"[^\w.\-+]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return (text or "object")[:max_len]


def get_object_download_dir(cfg: PipelineConfig, object_name: str) -> Path:
    """Return the dedicated download/cache directory for one object."""
    path = Path(cfg.download_dir) / safe_filename(object_name)
    path.mkdir(parents=True, exist_ok=True)
    return path


def filename_from_uri(uri: str, cutout_index: int) -> str:
    """Derive a stable local filename from the remote URI."""
    parsed = urllib.parse.urlparse(str(uri))
    base = Path(parsed.path).name or f"cutout_{cutout_index:05d}.fits"
    if not base.lower().endswith((".fits", ".fit", ".fz")):
        base = f"{base}.fits"
    return f"{int(cutout_index):05d}_{safe_filename(base)}"


def s3_key_from_irsa_uri(uri: str) -> str:
    """Map an IRSA SPHEREx HTTP/cutout URI to a key inside the SPHEREx S3 bucket."""
    text = str(uri or "").strip()
    if not text:
        raise ValueError("Empty URI; cannot derive S3 key.")
    parsed = urllib.parse.urlparse(text)

    if parsed.scheme == "s3":
        return parsed.path.lstrip("/")

    path = parsed.path or text
    for marker in ("/ibe/data/spherex/", "/data/spherex/"):
        idx = path.find(marker)
        if idx >= 0:
            key = path[idx + len(marker):].lstrip("/")
            if key:
                return key

    stripped = path.lstrip("/")
    if stripped.startswith(("qr1/", "qr2/", "qr2_deep/", "cal-", "level2_")):
        return stripped

    raise ValueError(f"Cannot map URI to SPHEREx S3 key: {uri}")


def _row_value(row, name: str, default=np.nan):
    """Small helper that works for astropy rows and plain dicts."""
    try:
        if hasattr(row, "colnames") and name not in row.colnames:
            return default
        return row[name]
    except Exception:
        try:
            return row.get(name, default)
        except Exception:
            return default


def _copy_hdu_with_optional_2d_cutout(hdu, image_shape, x0: int, x1: int, y0: int, y1: int, update_alt_wcs: bool):
    """Copy one HDU, cutting matching 2D detector images and preserving parent coordinates."""
    data = hdu.data
    header = hdu.header.copy()
    is_matching_2d = (
        data is not None
        and getattr(data, "ndim", None) == 2
        and tuple(data.shape) == tuple(image_shape)
    )

    if is_matching_2d:
        data_out = np.asarray(data)[y0:y1, x0:x1]
        if "CRPIX1" in header:
            header["CRPIX1"] = float(header["CRPIX1"]) - float(x0)
        if "CRPIX2" in header:
            header["CRPIX2"] = float(header["CRPIX2"]) - float(y0)

        if update_alt_wcs:
            header["CRPIX1A"] = (1.0 - float(x0), "Alt-WCS parent-detector X offset for cutout")
            header["CRPIX2A"] = (1.0 - float(y0), "Alt-WCS parent-detector Y offset for cutout")
            header["SPXORX0"] = (int(x0), "Original detector X0 for S3 cutout")
            header["SPXORY0"] = (int(y0), "Original detector Y0 for S3 cutout")
            header["SPXORX1"] = (int(x1), "Original detector X1 for S3 cutout, exclusive")
            header["SPXORY1"] = (int(y1), "Original detector Y1 for S3 cutout, exclusive")

        if isinstance(hdu, fits.PrimaryHDU):
            return fits.PrimaryHDU(data=data_out, header=header)
        return fits.ImageHDU(data=data_out, header=header, name=hdu.name)

    return hdu.copy()


def stamp_data_release_in_fits(path: str | Path, data_release: str) -> None:
    """Best-effort insertion of inferred DATAREL into a local FITS file."""
    release = normalize_data_release(data_release)
    if release == "unknown":
        return
    try:
        with fits.open(path, mode="update", memmap=False) as hdul:
            for hdu in hdul:
                try:
                    hdu.header["DATAREL"] = (release, "SPHEREx data release inferred from source URL")
                except Exception:
                    pass
            hdul.flush()
    except Exception:
        # Do not fail the download if the file cannot be stamped.
        pass


def download_uri_to_file_http(uri: str, local_path: Path, cfg: PipelineConfig) -> Path:
    """Download a remote IRSA cutout URI with the original HTTP streaming method."""
    tmp_path = local_path.with_suffix(local_path.suffix + ".part")
    with requests.get(str(uri), stream=True, timeout=cfg.request_timeout_sec) as response:
        response.raise_for_status()
        with open(tmp_path, "wb") as fh:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fh.write(chunk)
    tmp_path.replace(local_path)
    stamp_data_release_in_fits(local_path, infer_data_release_from_uri(uri))
    return local_path


def download_uri_to_file_s3_cutout(uri: str, local_path: Path, cfg: PipelineConfig, ra: float, dec: float) -> Path:
    """S3 parent-FITS cutout extraction into a compact local FITS file."""
    key = s3_key_from_irsa_uri(uri)
    s3_uri = f"s3://{cfg.s3_bucket}/{key}"
    tmp_path = local_path.with_suffix(local_path.suffix + ".part")
    size = max(int(cfg.s3_cutout_min_size_px), int(cfg.s3_cutout_size_px))

    with fits.open(
        s3_uri,
        use_fsspec=True,
        fsspec_kwargs={"anon": True},
        memmap=False,
        lazy_load_hdus=False,
    ) as hdul:
        if "IMAGE" not in hdul:
            raise RuntimeError(f"S3 FITS has no IMAGE extension: {s3_uri}")

        image_hdu = hdul["IMAGE"]
        image = np.asarray(image_hdu.data)
        if image.ndim != 2:
            raise RuntimeError(f"S3 IMAGE extension is not 2D: shape={image.shape}")

        header = image_hdu.header
        obs_mjd = mjd_from_header(header)
        adj_ra, adj_dec, projection_status = project_to_epoch(
            ref_ra_deg=ra,
            ref_dec_deg=dec,
            ref_epoch_yr=cfg.reference_epoch_yr,
            pmra_masyr=cfg.pmra_masyr,
            pmdec_masyr=cfg.pmdec_masyr,
            target_mjd=obs_mjd,
        )

        wcs = WCS(header)
        target = SkyCoord(adj_ra * u.deg, adj_dec * u.deg, frame="icrs")
        xpix, ypix = wcs.world_to_pixel(target)
        if not (np.isfinite(xpix) and np.isfinite(ypix)):
            raise RuntimeError(f"Target projected outside usable WCS: x={xpix}, y={ypix}")

        ny, nx = image.shape
        half = size // 2
        cx = int(round(float(xpix)))
        cy = int(round(float(ypix)))
        x0 = max(0, cx - half)
        y0 = max(0, cy - half)
        x1 = min(nx, x0 + size)
        y1 = min(ny, y0 + size)
        x0 = max(0, x1 - size)
        y0 = max(0, y1 - size)

        if x1 <= x0 or y1 <= y0:
            raise RuntimeError(
                f"Computed empty S3 cutout bounds for {s3_uri}: "
                f"x=[{x0}:{x1}), y=[{y0}:{y1}), shape={image.shape}"
            )

        # Cut every detector-sized 2D extension with the same parent slices so
        # IMAGE, VARIANCE, FLAGS, and ZODI remain pixel-aligned.
        out_hdus = [
            _copy_hdu_with_optional_2d_cutout(
                hdu,
                image_shape=image.shape,
                x0=x0,
                x1=x1,
                y0=y0,
                y1=y1,
                update_alt_wcs=cfg.s3_cutout_update_alt_wcs,
            )
            for hdu in hdul
        ]

        out_list = fits.HDUList(out_hdus)
        try:
            out_img = out_list["IMAGE"]
            out_img.header["SPXS3KEY"] = (key[:68], "SPHEREx S3 object key, truncated")
            out_img.header["SPXPMRA"] = (float(adj_ra), "RA used for S3 cutout")
            out_img.header["SPXPMDEC"] = (float(adj_dec), "Dec used for S3 cutout")
            out_img.header["SPXPMST"] = (projection_status[:68], "Position projection status")

            # Persist the inferred release into every HDU. This is essential
            # for cached cutouts because their local filenames often no
            # longer contain the original /spherex/<release>/ URL segment.
            s3_release = infer_data_release_from_uri(uri)
            if s3_release != "unknown":
                for out_hdu in out_list:
                    try:
                        out_hdu.header["DATAREL"] = (s3_release, "SPHEREx data release inferred from source URL")
                    except Exception:
                        pass
        except Exception:
            pass

        out_list.writeto(tmp_path, overwrite=True)

    tmp_path.replace(local_path)
    return local_path


def download_uri_to_file(uri: str, local_path: Path, cfg: PipelineConfig, ra: float | None = None, dec: float | None = None) -> Path:
    """Ensure a remote FITS cutout is available locally, using HTTP or S3 cutout extraction."""
    local_path.parent.mkdir(parents=True, exist_ok=True)

    if local_path.exists() and local_path.stat().st_size > 0 and not cfg.redownload_existing_files:
        # If this file was cached by an older version, it may not yet carry
        # DATAREL.  Stamp it opportunistically when the source URI still
        # contains the release, then reuse the cached file.
        stamp_data_release_in_fits(local_path, infer_data_release_from_uri(uri))
        return local_path

    backend = str(getattr(cfg, "download_backend", "http") or "http").lower().strip()
    if backend in ("s3", "s3_cutout"):
        if ra is None or dec is None:
            raise ValueError("S3 cutout backend requires target ra/dec.")
        try:
            return download_uri_to_file_s3_cutout(uri, local_path, cfg, float(ra), float(dec))
        except Exception:
            if not cfg.s3_cutout_fallback_to_http:
                raise
            return download_uri_to_file_http(uri, local_path, cfg)

    return download_uri_to_file_http(uri, local_path, cfg)


def prepare_cutout_row_file(row, object_download_dir: Path, cfg: PipelineConfig, ra: float | None = None, dec: float | None = None) -> dict:
    """Ensure one cutout is available locally and return a row-like dict with local_uri."""
    uri = str(_row_value(row, "uri", ""))
    cutout_index = int(_row_value(row, "cutout_index", 0))
    local_file = object_download_dir / filename_from_uri(uri, cutout_index)
    existed_before = local_file.exists() and local_file.stat().st_size > 0
    backend = str(getattr(cfg, "download_backend", "http") or "http").lower().strip()

    last_exc = None
    for attempt in range(cfg.retries):
        try:
            download_uri_to_file(uri, local_file, cfg, ra=ra, dec=dec)
            if existed_before and not cfg.redownload_existing_files:
                status = "cached"
            elif backend in ("s3", "s3_cutout"):
                status = "downloaded_s3_cutout"
            else:
                status = "downloaded_http"
            return {
                "uri": uri,
                "local_uri": str(local_file),
                "cutout_index": cutout_index,
                "time_bounds_lower": _row_value(row, "time_bounds_lower", np.nan),
                "time_bounds_upper": _row_value(row, "time_bounds_upper", np.nan),
                "download_backend": backend,
                "download_status": status,
                "data_release": infer_data_release_from_uri(uri)
                if infer_data_release_from_uri(uri) != "unknown"
                else infer_data_release_from_fits(local_file),
            }
        except Exception as exc:
            last_exc = exc
            if attempt < cfg.retries - 1:
                time.sleep(cfg.retry_delay_sec)

    return {
        "uri": uri,
        "local_uri": str(local_file),
        "cutout_index": cutout_index,
        "time_bounds_lower": _row_value(row, "time_bounds_lower", np.nan),
        "time_bounds_upper": _row_value(row, "time_bounds_upper", np.nan),
        "download_backend": backend,
        "download_status": f"download_failed:{type(last_exc).__name__}",
        "download_error": str(last_exc),
        "data_release": infer_data_release_from_uri(uri)
        if infer_data_release_from_uri(uri) != "unknown"
        else infer_data_release_from_fits(local_file),
    }


def normalize_data_release(release: object) -> str:
    """Return a canonical lower-case SPHEREx data-release token."""
    text = str(release or "").strip().lower().replace("-", "_").replace(" ", "_")
    if "qr2_deep" in text or text in {"spherex_qr2_deep", "qr2deep"}:
        return "qr2_deep"
    if "qr2" in text or text == "spherex_qr2":
        return "qr2"
    if "qr1" in text or text == "spherex_qr1":
        return "qr1"
    return "unknown"


def infer_data_release_from_uri(uri: str) -> str:
    """Infer the SPHEREx data release from an IRSA/S3/local path or URL."""
    text = str(uri or "").lower().replace("\\", "/")
    # Check qr2_deep first because it also contains the substring "qr2".
    if "/spherex/qr2_deep/" in text or "spherex_qr2_deep" in text or "/qr2_deep/" in text:
        return "qr2_deep"
    if "/spherex/qr2/" in text or "spherex_qr2" in text or "/qr2/" in text or text.startswith("qr2/"):
        return "qr2"
    if "/spherex/qr1/" in text or "spherex_qr1" in text or "/qr1/" in text or text.startswith("qr1/"):
        return "qr1"
    return "unknown"


def infer_data_release_from_header(header) -> str:
    """Infer the data release from common FITS header keywords when present."""
    if header is None:
        return "unknown"
    for key in ("DATAREL", "DATA_REL", "OBS_COLLECTION", "OBS-COLL", "COLLECTION", "OBSCOL"):
        try:
            release = normalize_data_release(header.get(key))
            if release != "unknown":
                return release
        except Exception:
            continue
    return "unknown"


def infer_data_release_from_fits(path: str | Path) -> str:
    """Infer the data release from a local FITS path and, if needed, its headers."""
    release = infer_data_release_from_uri(str(path))
    if release != "unknown":
        return release
    try:
        with fits.open(path, memmap=False) as hdul:
            for hdu in hdul:
                release = infer_data_release_from_header(getattr(hdu, "header", None))
                if release != "unknown":
                    return release
    except Exception:
        pass
    return "qr2"


def set_runtime_data_release(cfg: PipelineConfig, release: str) -> str:
    """Store the inferred release on the config object for calibration lookup."""
    release = normalize_data_release(release)
    if release != "unknown":
        setattr(cfg, "_active_data_release", release)
    return release


def get_runtime_data_release(cfg: PipelineConfig, fallback: str = "unknown") -> str:
    """Return the inferred release stored during the current pipeline run."""
    release = normalize_data_release(getattr(cfg, "_active_data_release", None))
    if release != "unknown":
        return release
    return normalize_data_release(fallback)


def infer_unique_data_release(rows: list[dict]) -> str:
    """Infer a single release from row dictionaries, returning 'mixed' or 'unknown' when needed."""
    releases = {normalize_data_release(r.get("data_release")) for r in rows}
    releases.discard("unknown")
    if len(releases) == 1:
        return next(iter(releases))
    if len(releases) > 1:
        return "mixed"
    return "unknown"


def download_cutout_files_parallel(cutout_table: Table, object_name: str, cfg: PipelineConfig, ra: float | None = None, dec: float | None = None) -> list[dict]:
    """Download all cutouts into the object-specific cache directory."""
    object_download_dir = get_object_download_dir(cfg, object_name)
    rows = []
    total = len(cutout_table)

    # Print detected data release once for this batch.
    releases = {
        infer_data_release_from_uri(str(_row_value(row, "uri", "")))
        for row in cutout_table
    }
    releases.discard("unknown")

    if len(releases) == 1:
        print(f"SPHEREx data release for this download batch: {next(iter(releases))}")
    elif len(releases) > 1:
        print(f"WARNING: mixed SPHEREx data releases in this batch: {sorted(releases)}")
    else:
        print("WARNING: could not infer SPHEREx data release from cutout URLs.")

    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg.max_workers) as executor:
        futures = [
            executor.submit(prepare_cutout_row_file, row, object_download_dir, cfg, ra, dec)
            for row in cutout_table
        ]

        iterator = concurrent.futures.as_completed(futures)
        if cfg.show_download_progress and tqdm is not None:
            iterator = tqdm(iterator, total=total, desc=f"Downloading {object_name}", unit="file")

        for future in iterator:
            rows.append(future.result())

    rows.sort(key=lambda r: r.get("cutout_index", 0))
    return rows


def flux_to_flux_lambda(wavelength, flux, density_unit=u.AA):
    """Convert flux density from F_nu units to F_lambda at the supplied wavelengths."""
    return flux.to(
        u.erg / u.s / u.cm ** 2 / density_unit,
        equivalencies=u.spectral_density(wavelength),
    )


def make_sapm_s3_paths(cfg: PipelineConfig, data_release: str) -> dict[int, str]:
    """Build public S3 keys for detector solid-angle pixel maps for one release."""
    release = normalize_data_release(data_release)
    if release == "unknown":
        raise ValueError("Cannot build SAPM S3 paths because the SPHEREx data release is unknown.")
    dataset_type = "solid_angle_pixel_map"
    return {
        det: (
            f"nasa-irsa-spherex/{release}/{dataset_type}/"
            f"{cfg.sapm_collection}/{det}/"
            f"{dataset_type}_D{det}_spx_{cfg.sapm_collection}.fits"
        )
        for det in range(1, 7)
    }


def get_sapm_cache_dir(cfg: PipelineConfig, data_release: str) -> Path:
    """Return local directory for cached SAPM detector files for one release."""
    release = normalize_data_release(data_release)
    if release == "unknown":
        raise ValueError("Cannot choose SAPM cache directory because the SPHEREx data release is unknown.")
    path = Path(cfg.sapm_cache_dir) / release / cfg.sapm_collection
    path.mkdir(parents=True, exist_ok=True)
    return path


def sapm_local_path(detector: int, cfg: PipelineConfig, data_release: str) -> Path:
    """Return local cached filename for one detector SAPM file."""
    return get_sapm_cache_dir(cfg, data_release) / f"solid_angle_pixel_map_D{int(detector)}_spx_{cfg.sapm_collection}.fits"


def prepare_cached_cutout_rows(object_name: str, cfg: PipelineConfig) -> list[dict]:
    """
    Build row dictionaries directly from local cached cutouts without querying IRSA.

    Files are read from:
        cfg.download_dir / safe_filename(object_name)

    The filename order is used as the cutout order.
    """
    object_download_dir = get_object_download_dir(cfg, object_name)
    files = sorted(
        p for p in object_download_dir.glob(cfg.cached_cutout_glob)
        if p.is_file() and not p.name.endswith(".part")
    )

    rows = []
    iterator = files
    if cfg.show_download_progress and tqdm is not None:
        iterator = tqdm(files, total=len(files), desc=f"Reading cached list for {object_name}", unit="file")

    for idx, path in enumerate(iterator, start=1):
        rows.append({
            "uri": str(path),
            "local_uri": str(path),
            "cutout_index": idx,
            "time_bounds_lower": np.nan,
            "time_bounds_upper": np.nan,
            "download_status": "local_cache",
            "data_release": infer_data_release_from_fits(path),
        })

    return rows


def query_spherex_cutouts(ra: float, dec: float, cfg: PipelineConfig) -> Table:
    """Query IRSA TAP for SPHEREx cutout URLs covering the target position."""
    service = pyvo.dal.TAPService(cfg.tap_url)
    cutout_size_deg = (cfg.cutout_size_arcsec * u.arcsec).to(u.deg).value
    query = f"""
    SELECT
        'https://irsa.ipac.caltech.edu/' || a.uri || '?center={ra},{dec}d&size={cutout_size_deg:7f}' AS uri,
        p.time_bounds_lower,
        p.time_bounds_upper
    FROM spherex.artifact a
    JOIN spherex.plane p ON a.planeid = p.planeid
    WHERE 1 = CONTAINS(POINT('ICRS', {ra}, {dec}), p.poly)
    ORDER BY p.time_bounds_lower
    """
    table = service.search(query).to_table()
    table["cutout_index"] = np.arange(1, len(table) + 1)
    return table


def load_sapm(detector: int, cfg: PipelineConfig, data_release: str):
    """
    Load the solid-angle pixel map for one detector and one inferred release.

    If cfg.cache_sapm_files=True, the SAPM file is cached locally and reused.
    """
    detector = int(detector)
    release = normalize_data_release(data_release)
    if release == "unknown":
        raise ValueError("Cannot load SAPM calibration because the SPHEREx data release is unknown.")
    s3_path = make_sapm_s3_paths(cfg, release)[detector]
    local_path = sapm_local_path(detector, cfg, release)

    if cfg.cache_sapm_files:
        if local_path.exists() and local_path.stat().st_size > 0 and not cfg.redownload_sapm_files:
            with fits.open(local_path) as hdul:
                return hdul["IMAGE"].data.astype(float), hdul["IMAGE"].header.copy()

        local_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = local_path.with_suffix(local_path.suffix + ".part")

        with fits.open(f"s3://{s3_path}", fsspec_kwargs={"anon": True}) as hdul:
            hdul.writeto(tmp_path, overwrite=True)

        tmp_path.replace(local_path)

        with fits.open(local_path) as hdul:
            return hdul["IMAGE"].data.astype(float), hdul["IMAGE"].header.copy()

    with fits.open(f"s3://{s3_path}", fsspec_kwargs={"anon": True}) as hdul:
        return hdul["IMAGE"].data.astype(float), hdul["IMAGE"].header.copy()


def detector_from_header(header) -> int:
    """Extract the SPHEREx detector number from the most common header keywords."""
    if "DETECTOR" in header:
        return int(header["DETECTOR"])
    if "BAND" in header:
        return int(header["BAND"])
    raise KeyError("Could not determine SPHEREx detector from header.")


def _finite_or_none(value):
    """Return a JSON/CSV-friendly scalar, preserving strings and finite numbers."""
    try:
        if value is None:
            return None
        if isinstance(value, (str, int, bool)):
            return value
        if isinstance(value, np.generic):
            value = value.item()
        if isinstance(value, float):
            return value if np.isfinite(value) else None
        return value
    except Exception:
        return str(value)


def project_to_epoch(ref_ra_deg: float,
                     ref_dec_deg: float,
                     ref_epoch_yr: float | None,
                     pmra_masyr: float | None,
                     pmdec_masyr: float | None,
                     target_mjd: float | None) -> tuple[float, float, str]:
    """Project a reference ICRS position to one SPHEREx exposure epoch."""
    if ref_epoch_yr is None or target_mjd is None:
        return float(ref_ra_deg), float(ref_dec_deg), "not_applied_missing_epoch"
    try:
        if not np.isfinite(float(target_mjd)) or not np.isfinite(float(ref_epoch_yr)):
            return float(ref_ra_deg), float(ref_dec_deg), "not_applied_nonfinite_epoch"
    except Exception:
        return float(ref_ra_deg), float(ref_dec_deg), "not_applied_bad_epoch"

    pmra = 0.0 if pmra_masyr is None or not np.isfinite(float(pmra_masyr)) else float(pmra_masyr)
    pmdec = 0.0 if pmdec_masyr is None or not np.isfinite(float(pmdec_masyr)) else float(pmdec_masyr)

    try:
        c0 = SkyCoord(
            ra=float(ref_ra_deg) * u.deg,
            dec=float(ref_dec_deg) * u.deg,
            pm_ra_cosdec=pmra * u.mas / u.yr,
            pm_dec=pmdec * u.mas / u.yr,
            distance=100.0 * u.pc,
            obstime=Time(float(ref_epoch_yr), format="decimalyear"),
            frame="icrs",
        )
        c_obs = c0.apply_space_motion(new_obstime=Time(float(target_mjd), format="mjd"))
        return float(c_obs.ra.deg), float(c_obs.dec.deg), "astropy"
    except Exception as exc:
        try:
            t_jyear = Time(float(target_mjd), format="mjd").jyear
            dt_yr = float(t_jyear - float(ref_epoch_yr))
            cos_dec = math.cos(math.radians(float(ref_dec_deg)))
            deg_per_mas = 1.0 / (1000.0 * 3600.0)
            dra_deg = (pmra / max(abs(cos_dec), 1e-12)) * deg_per_mas * dt_yr
            ddec_deg = pmdec * deg_per_mas * dt_yr
            ra_new = (float(ref_ra_deg) + dra_deg) % 360.0
            dec_new = max(min(float(ref_dec_deg) + ddec_deg, 90.0), -90.0)
            return float(ra_new), float(dec_new), f"manual_pm_fallback:{type(exc).__name__}"
        except Exception as exc2:
            return float(ref_ra_deg), float(ref_dec_deg), f"failed:{type(exc2).__name__}"


def mjd_from_header(header):
    """Best-effort extraction of observation MJD from a SPHEREx IMAGE header."""
    for key in ("MJD-AVG", "MJD_EPOCH_AVG", "MJD", "MJDAVG", "DATE-AVG"):
        value = header.get(key)
        if value is None:
            continue
        try:
            if key == "DATE-AVG":
                return float(Time(value, format="isot").mjd)
            return float(value)
        except Exception:
            continue
    return np.nan


def append_manifest_rows(rows: list[dict], object_name: str, cfg: PipelineConfig, basename: str = "processing_manifest") -> None:
    """Write provenance/diagnostic rows as CSV and/or JSONL."""
    if not rows or not cfg.save_manifest:
        return
    fmt = str(cfg.manifest_format).lower().strip()
    if fmt in ("", "none", "off", "false"):
        return
    ensure_output_directories(cfg.output_dir)
    manifest_dir = Path(cfg.output_dir, "fits")
    manifest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = safe_filename(object_name)

    clean_rows = []
    for row in rows:
        clean_rows.append({str(k): _finite_or_none(v) for k, v in row.items()})

    if fmt in ("csv", "both"):
        csv_path = manifest_dir / f"{safe_name}_{basename}.csv"
        fieldnames = sorted({k for r in clean_rows for k in r.keys()})
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(clean_rows)
        print(f"Saved manifest CSV: {csv_path}")

    if fmt in ("jsonl", "both"):
        jsonl_path = manifest_dir / f"{safe_name}_{basename}.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as fh:
            for row in clean_rows:
                fh.write(json.dumps(row, allow_nan=False, default=str) + "\n")
        print(f"Saved manifest JSONL: {jsonl_path}")


def build_cutout_manifest_rows(prepared_rows: list[dict], cutouts: list[dict], object_name: str, cfg: PipelineConfig) -> list[dict]:
    """Merge download/open/projection diagnostics into one cutout-level manifest."""
    by_index = {int(r.get("cutout_index", -1)): r for r in prepared_rows}
    rows = []
    for cutout in cutouts:
        idx = int(cutout.get("cutout_index", -1))
        prep = by_index.get(idx, {})
        rows.append({
            "object_name": object_name,
            "reference_ra_deg": cutout.get("reference_ra_deg", np.nan),
            "reference_dec_deg": cutout.get("reference_dec_deg", np.nan),
            "reference_epoch_yr": cfg.reference_epoch_yr,
            "pmra_masyr": cfg.pmra_masyr,
            "pmdec_masyr": cfg.pmdec_masyr,
            "input_ra_deg": cutout.get("input_ra_deg", np.nan),
            "input_dec_deg": cutout.get("input_dec_deg", np.nan),
            "epoch_projection_status": cutout.get("epoch_projection_status", ""),
            "epoch_projection_sep_arcsec": cutout.get("epoch_projection_sep_arcsec", np.nan),
            "mjd_avg": cutout.get("mjd_avg", np.nan),
            "data_release": cutout.get("data_release", prep.get("data_release", "unknown")),
            "cutout_index": idx,
            "detector": cutout.get("detector", np.nan),
            "central_wavelength_um": cutout.get("central_wavelength_um", np.nan),
            "x_src": cutout.get("x_src", np.nan),
            "y_src": cutout.get("y_src", np.nan),
            "image_shape": cutout.get("image_shape", ""),
            "uri": cutout.get("uri", prep.get("uri", "")),
            "local_uri": cutout.get("local_uri", prep.get("local_uri", "")),
            "download_backend": prep.get("download_backend", getattr(cfg, "download_backend", "")),
            "download_status": cutout.get("download_status", prep.get("download_status", "")),
            "download_error": prep.get("download_error", ""),
            "open_status": cutout.get("status", "ok" if "image_hdu" in cutout else "unknown"),
        })
    return rows


def process_cutout_row(row, ra: float, dec: float, cfg: PipelineConfig):
    """
    Open a locally cached FITS cutout and prepare it for photometry.
    """
    last_exc = None
    open_path = row.get("local_uri", row.get("uri"))

    for attempt in range(cfg.retries):
        try:
            with fits.open(open_path) as hdul:
                image_hdu = hdul["IMAGE"].copy()
                flags_hdu = hdul["FLAGS"].copy() if "FLAGS" in hdul else None
                var_hdu = hdul["VARIANCE"].copy() if "VARIANCE" in hdul else None
                zodi_hdu = hdul["ZODI"].copy() if "ZODI" in hdul else None
                psf_hdu = hdul["PSF"].copy() if "PSF" in hdul else None

                header = image_hdu.header
                detector = detector_from_header(header)
                data_release = normalize_data_release(row.get("data_release", "unknown"))
                if data_release == "unknown":
                    data_release = infer_data_release_from_header(header)
                if data_release == "unknown":
                    data_release = infer_data_release_from_uri(str(row.get("uri", open_path)))
                if data_release == "unknown":
                    data_release = infer_data_release_from_uri(str(open_path))
                if data_release != "unknown":
                    set_runtime_data_release(cfg, data_release)
                    # Back-fill DATAREL into older cached FITS files when the
                    # release was inferred from the path/row but missing in
                    # the header. This makes future cached runs self-contained.
                    if infer_data_release_from_header(header) == "unknown":
                        stamp_data_release_in_fits(open_path, data_release)

                spatial_wcs = WCS(header)
                spectral_wcs = WCS(header=header, fobj=hdul, key="W")
                spectral_wcs.sip = None

                obs_mjd = mjd_from_header(header)
                adj_ra, adj_dec, projection_status = project_to_epoch(
                    ref_ra_deg=ra,
                    ref_dec_deg=dec,
                    ref_epoch_yr=cfg.reference_epoch_yr,
                    pmra_masyr=cfg.pmra_masyr,
                    pmdec_masyr=cfg.pmdec_masyr,
                    target_mjd=obs_mjd,
                )
                if cfg.log_epoch_projection and projection_status != "not_applied_missing_epoch":
                    print(
                        f"Cutout {int(row['cutout_index'])}: epoch-adjusted coords "
                        f"RA={adj_ra:.9f}, Dec={adj_dec:.9f}, MJD={obs_mjd}, status={projection_status}"
                    )

                target = SkyCoord(ra=adj_ra, dec=adj_dec, unit="deg", frame="icrs")
                x_src, y_src = spatial_wcs.world_to_pixel(target)
                wl_src, _ = spectral_wcs.pixel_to_world(x_src, y_src)

                try:
                    sep_as = SkyCoord(ra, dec, unit="deg").separation(SkyCoord(adj_ra, adj_dec, unit="deg")).arcsec
                except Exception:
                    sep_as = np.nan

                return {
                    "uri": str(row.get("uri", open_path)),
                    "local_uri": str(open_path),
                    "download_status": row.get("download_status", ""),
                    "data_release": data_release,
                    "cutout_index": int(row["cutout_index"]),
                    "time_bounds_lower": row.get("time_bounds_lower", np.nan),
                    "time_bounds_upper": row.get("time_bounds_upper", np.nan),
                    "detector": detector,
                    "mjd_avg": obs_mjd,
                    "reference_ra_deg": float(ra),
                    "reference_dec_deg": float(dec),
                    "input_ra_deg": float(adj_ra),
                    "input_dec_deg": float(adj_dec),
                    "epoch_projection_status": projection_status,
                    "epoch_projection_sep_arcsec": float(sep_as) if np.isfinite(sep_as) else np.nan,
                    "image_shape": f"{image_hdu.data.shape[0]}x{image_hdu.data.shape[1]}",
                    "image_hdu": image_hdu,
                    "flags_hdu": flags_hdu,
                    "variance_hdu": var_hdu,
                    "zodi_hdu": zodi_hdu,
                    "psf_hdu": psf_hdu,
                    "x_src": float(x_src),
                    "y_src": float(y_src),
                    "central_wavelength_um": float(wl_src.to(u.um).value),
                }
        except Exception as exc:
            last_exc = exc
            if attempt < cfg.retries - 1:
                time.sleep(cfg.retry_delay_sec)

    return {
        "uri": str(row.get("uri", open_path)),
        "local_uri": str(open_path),
        "data_release": normalize_data_release(row.get("data_release", infer_data_release_from_uri(str(open_path)))),
        "cutout_index": int(row["cutout_index"]),
        "status": f"open_failed:{type(last_exc).__name__}",
    }


def open_cutouts_parallel(prepared_rows: list[dict], ra: float, dec: float, cfg: PipelineConfig) -> list[dict]:
    """
    Open locally cached cutouts in parallel and extract HDUs/metadata.
    """
    rows = []
    total = len(prepared_rows)

    with concurrent.futures.ThreadPoolExecutor(max_workers=cfg.max_workers) as executor:
        futures = [executor.submit(process_cutout_row, row, ra, dec, cfg) for row in prepared_rows]

        iterator = concurrent.futures.as_completed(futures)
        if cfg.show_download_progress and tqdm is not None:
            iterator = tqdm(iterator, total=total, desc="Opening cached FITS", unit="file")

        for future in iterator:
            rows.append(future.result())

    rows.sort(key=lambda r: r.get("cutout_index", 0))
    return rows


def get_cutout_parent_slices(image_header, image_shape, parent_shape):
    """
    Return matching image and parent-detector slices for a SPHEREx cutout.

    SPHEREx cutouts carry alternate-WCS reference keywords (CRPIX1A/CRPIX2A)
    that encode the offset between the cutout pixel grid and the parent detector
    pixel grid.  The parent detector coordinates are recovered with:

        x_parent = 1 + x_cutout - CRPIX1A
        y_parent = 1 + y_cutout - CRPIX2A

    where x_cutout/y_cutout are zero-based numpy pixel coordinates.  Therefore
    the parent-array slice origin is approximately 1 - CRPIX*A.

    Returns
    -------
    image_slices, parent_slices, info
        image_slices and parent_slices are two-element tuples suitable for
        numpy array indexing: (yslice, xslice).  The returned slices have the
        same shape and are clipped to the valid parent-detector bounds.
    """
    ny, nx = int(image_shape[0]), int(image_shape[1])
    parent_ny, parent_nx = int(parent_shape[0]), int(parent_shape[1])

    if "CRPIX1A" not in image_header or "CRPIX2A" not in image_header:
        # Conservative fallback for older/non-standard files.  This preserves
        # the previous behavior but makes the fallback explicit in diagnostics.
        sy = min(parent_ny, ny)
        sx = min(parent_nx, nx)
        info = {
            "sapm_status": "fallback_missing_crpix_a",
            "sapm_x0_parent": 0,
            "sapm_y0_parent": 0,
            "sapm_x1_parent": int(sx),
            "sapm_y1_parent": int(sy),
            "sapm_x0_image": 0,
            "sapm_y0_image": 0,
            "sapm_x1_image": int(sx),
            "sapm_y1_image": int(sy),
        }
        return (slice(0, sy), slice(0, sx)), (slice(0, sy), slice(0, sx)), info

    x0_parent = int(np.rint(1.0 - float(image_header["CRPIX1A"])))
    y0_parent = int(np.rint(1.0 - float(image_header["CRPIX2A"])))
    x1_parent = x0_parent + nx
    y1_parent = y0_parent + ny

    # Clip overlap to the parent detector image.
    px0 = max(0, x0_parent)
    py0 = max(0, y0_parent)
    px1 = min(parent_nx, x1_parent)
    py1 = min(parent_ny, y1_parent)

    if px1 <= px0 or py1 <= py0:
        raise ValueError(
            "Cutout does not overlap parent detector SAPM map: "
            f"cutout parent bounds x=[{x0_parent},{x1_parent}), "
            f"y=[{y0_parent},{y1_parent}), parent shape={parent_shape}"
        )

    # Matching image-region slice after parent-bound clipping.
    ix0 = px0 - x0_parent
    iy0 = py0 - y0_parent
    ix1 = ix0 + (px1 - px0)
    iy1 = iy0 + (py1 - py0)

    info = {
        "sapm_status": "ok",
        "sapm_x0_parent": int(px0),
        "sapm_y0_parent": int(py0),
        "sapm_x1_parent": int(px1),
        "sapm_y1_parent": int(py1),
        "sapm_x0_image": int(ix0),
        "sapm_y0_image": int(iy0),
        "sapm_x1_image": int(ix1),
        "sapm_y1_image": int(iy1),
        "sapm_crpix1a": float(image_header["CRPIX1A"]),
        "sapm_crpix2a": float(image_header["CRPIX2A"]),
    }
    return (slice(iy0, iy1), slice(ix0, ix1)), (slice(py0, py1), slice(px0, px1)), info


def extract_sapm_for_cutout(sapm_data, image_header, image_shape):
    """
    Extract the SAPM subarray corresponding to an IMAGE cutout.

    The SAPM calibration file is a full-detector map.  For a small IRSA cutout,
    the SAPM array must be sliced at the parent-detector coordinates encoded by
    CRPIX1A/CRPIX2A, not simply at [:ny, :nx].
    """
    image_slices, sapm_slices, info = get_cutout_parent_slices(
        image_header=image_header,
        image_shape=image_shape,
        parent_shape=sapm_data.shape,
    )
    sapm_use = np.asarray(sapm_data, dtype=float)[sapm_slices]
    if sapm_use.shape != (
            image_slices[0].stop - image_slices[0].start,
            image_slices[1].stop - image_slices[1].start,
    ):
        raise ValueError(
            f"SAPM cutout shape mismatch: sapm={sapm_use.shape}, "
            f"image slices={image_slices}"
        )
    return sapm_use, image_slices, info


def convert_to_ujy(image_data, image_header, sapm_data, sapm_header):
    """Convert an IMAGE array from surface-brightness units to per-pixel uJy."""
    bunit = Unit(image_header.get("BUNIT", "MJy/sr"))
    sapm_unit = Unit(sapm_header.get("BUNIT", "arcsec2"))
    return ((image_data * bunit).to(u.uJy / u.arcsec ** 2) * (sapm_data * sapm_unit)).value


def convert_variance_to_ujy2(var_data, image_header, sapm_data, sapm_header):
    """Convert a VARIANCE array consistently with convert_to_ujy, returning uJy^2."""
    bunit = Unit(image_header.get("BUNIT", "MJy/sr"))
    sapm_unit = Unit(sapm_header.get("BUNIT", "arcsec2"))
    scale = ((1.0 * bunit).to(u.uJy / u.arcsec ** 2) * (sapm_data * sapm_unit)).value
    return np.asarray(var_data, dtype=float) * scale ** 2


def make_bad_pixel_mask(flags, flux, bad_flag_bits: Iterable[int]):
    """Return a boolean mask for pixels carrying any configured fatal flag bit or non-finite flux."""
    bad_mask = np.zeros_like(flux, dtype=bool)

    if flags is not None:
        mask_value = sum(1 << int(bit) for bit in bad_flag_bits)
        bad_mask |= (np.asarray(flags) & mask_value) != 0

    bad_mask |= ~np.isfinite(flux)
    return bad_mask


def count_bad_aperture_flags(flags, x, y, radius_pix, flag_bits):
    """Count flagged pixels inside a circular aperture using center inclusion."""
    if flags is None:
        return 0
    aperture = CircularAperture((x, y), r=radius_pix)
    ap_mask = aperture.to_mask(method="center").to_image(flags.shape)
    if ap_mask is None:
        return 0
    ap_flags = np.asarray(flags)[ap_mask > 0]
    mask_value = sum(1 << int(bit) for bit in flag_bits)
    return int(np.count_nonzero((ap_flags & mask_value) != 0))


def extract_spherex_psf_kernel(hdul, x, y, cfg: PipelineConfig):
    """
    Extract a native-pixel SPHEREx PSF kernel from the PSF extension.
    """
    if "PSF" not in hdul:
        raise ValueError("No PSF extension present in this cutout.")

    psf_cube = hdul["PSF"].data
    psf_header = hdul["PSF"].header
    oversamp = int(psf_header.get("OVERSAMP", 10))

    if psf_cube is None or psf_cube.ndim != 3:
        raise ValueError(f"Expected 3D PSF cube, got shape {None if psf_cube is None else psf_cube.shape}")

    ny, nx = hdul["IMAGE"].data.shape
    nplanes = psf_cube.shape[0]
    ngrid = int(round(np.sqrt(nplanes)))
    if ngrid * ngrid != nplanes:
        ngrid = 11

    zone_x = min(ngrid - 1, max(0, int(np.floor(x / nx * ngrid))))
    zone_y = min(ngrid - 1, max(0, int(np.floor(y / ny * ngrid))))
    plane = min(nplanes - 1, zone_y * ngrid + zone_x)

    psf_super = np.asarray(psf_cube[plane], dtype=float).copy()
    psf_super = np.nan_to_num(psf_super, nan=0.0, posinf=0.0, neginf=0.0)
    psf_super = np.clip(psf_super, 0.0, None)

    total = np.nansum(psf_super)
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Selected PSF plane has non-positive sum.")
    psf_super /= total

    frac_x = x - np.floor(x)
    frac_y = y - np.floor(y)
    shift_x = cfg.psf_shift_sign * frac_x * oversamp
    shift_y = cfg.psf_shift_sign * frac_y * oversamp

    psf_super = ndi_shift(psf_super, shift=(shift_y, shift_x), order=3, mode="constant", cval=0.0, prefilter=True)
    psf_super = np.clip(np.nan_to_num(psf_super, nan=0.0), 0.0, None)

    total = np.nansum(psf_super)
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Shifted PSF has non-positive sum.")
    psf_super /= total

    cy = psf_super.shape[0] // 2
    cx = psf_super.shape[1] // 2
    r_super = int(cfg.psf_kernel_radius_native * oversamp)

    y1 = max(0, cy - r_super)
    y2 = min(psf_super.shape[0], cy + r_super + 1)
    x1 = max(0, cx - r_super)
    x2 = min(psf_super.shape[1], cx + r_super + 1)
    cut = psf_super[y1:y2, x1:x2]

    size_y = (cut.shape[0] // oversamp) * oversamp
    size_x = (cut.shape[1] // oversamp) * oversamp
    size = min(size_y, size_x)
    cut = cut[:size, :size]

    if cut.size == 0 or size < oversamp:
        raise ValueError("PSF crop too small after oversampling alignment.")

    new_n = size // oversamp
    psf_native = cut.reshape(new_n, oversamp, new_n, oversamp).sum(axis=(1, 3))

    total = np.nansum(psf_native)
    if not np.isfinite(total) or total <= 0:
        raise ValueError("Native PSF has non-positive sum.")
    psf_native /= total
    return psf_native


def psf_flux_fit(flux_ujy, var_ujy2, flags, x, y, psf_kernel, cfg: PipelineConfig):
    """
    Weighted linear PSF photometry in uJy.

    Model:
        image = flux * psf + background [+ dx + dy]
    """
    if not np.isfinite(x) or not np.isfinite(y):
        return np.nan, np.nan, {"psf_status": "bad_position"}

    psf = np.asarray(psf_kernel, dtype=float).copy()
    psf_sum = np.nansum(psf)
    if not np.isfinite(psf_sum) or psf_sum <= 0:
        return np.nan, np.nan, {"psf_status": "bad_psf"}
    psf /= psf_sum

    ph, pw = psf.shape
    x0 = int(np.round(x))
    y0 = int(np.round(y))

    left_w = pw // 2
    right_w = pw - left_w
    left_h = ph // 2
    right_h = ph - left_h

    x1 = max(0, x0 - left_w)
    x2 = min(flux_ujy.shape[1], x0 + right_w)
    y1 = max(0, y0 - left_h)
    y2 = min(flux_ujy.shape[0], y0 + right_h)

    cut = flux_ujy[y1:y2, x1:x2].astype(float)

    psf_x1 = left_w - (x0 - x1)
    psf_y1 = left_h - (y0 - y1)
    psf_x2 = psf_x1 + cut.shape[1]
    psf_y2 = psf_y1 + cut.shape[0]
    psf_cut = psf[psf_y1:psf_y2, psf_x1:psf_x2]

    if cut.shape != psf_cut.shape:
        return np.nan, np.nan, {
            "psf_status": "shape_mismatch",
            "psf_cut_shape_y": int(psf_cut.shape[0]),
            "psf_cut_shape_x": int(psf_cut.shape[1]),
            "data_cut_shape_y": int(cut.shape[0]),
            "data_cut_shape_x": int(cut.shape[1]),
        }

    if var_ujy2 is not None:
        var_cut = var_ujy2[y1:y2, x1:x2].astype(float)
    else:
        finite = np.isfinite(cut)
        local_var = np.nanvar(cut[finite]) if np.count_nonzero(finite) > 3 else np.nan
        var_cut = np.full(cut.shape, local_var, dtype=float)

    valid = np.isfinite(cut) & np.isfinite(psf_cut) & np.isfinite(var_cut) & (var_cut > 0)
    if flags is not None:
        flag_cut = flags[y1:y2, x1:x2]
        fatal_mask = sum(1 << int(bit) for bit in cfg.bad_flag_bits)
        valid &= ((flag_cut & fatal_mask) == 0)

    n_valid = int(np.count_nonzero(valid))
    if n_valid < int(cfg.psf_min_valid_pixels):
        return np.nan, np.nan, {"psf_status": "too_few_valid_pixels", "psf_n_valid": n_valid}

    yy, xx = np.indices(cut.shape)
    dx = xx - (x - x1)
    dy = yy - (y - y1)

    cols = [psf_cut[valid], np.ones(n_valid)]
    if cfg.psf_fit_background_gradient:
        cols.extend([dx[valid], dy[valid]])

    A = np.vstack(cols).T
    yvec = cut[valid]
    w = 1.0 / var_cut[valid]

    Aw = A * np.sqrt(w)[:, None]
    yw = yvec * np.sqrt(w)

    try:
        normal = Aw.T @ Aw
        cov = np.linalg.inv(normal)
        pars = cov @ (Aw.T @ yw)
    except np.linalg.LinAlgError:
        return np.nan, np.nan, {"psf_status": "singular_fit", "psf_n_valid": n_valid}

    flux_uJy = float(pars[0])
    err_uJy = float(np.sqrt(cov[0, 0])) if cov[0, 0] > 0 else np.nan

    model = A @ pars
    chi2 = float(np.sum(((yvec - model) ** 2) * w))
    ndof = int(len(yvec) - len(pars))
    red_chi2 = chi2 / ndof if ndof > 0 else np.nan

    info = {
        "psf_status": "ok",
        "psf_n_valid": n_valid,
        "psf_chi2": chi2,
        "psf_reduced_chi2": float(red_chi2) if np.isfinite(red_chi2) else np.nan,
        "psf_background_const": float(pars[1]) if len(pars) > 1 else np.nan,
        "psf_background_dx": float(pars[2]) if len(pars) > 2 else np.nan,
        "psf_background_dy": float(pars[3]) if len(pars) > 3 else np.nan,
        "psf_kernel_sum": float(np.nansum(psf_kernel)),
        "psf_kernel_shape_y": int(psf.shape[0]),
        "psf_kernel_shape_x": int(psf.shape[1]),
    }

    if cfg.psf_max_reduced_chi2 is not None and np.isfinite(red_chi2):
        if red_chi2 > cfg.psf_max_reduced_chi2:
            info["psf_status"] = "rejected_high_reduced_chi2"
            return np.nan, np.nan, info

    return flux_uJy, err_uJy, info


def psf_flux_fit_with_local_grid_search(hdul_like, flux_ujy, var_ujy2, flags, x, y, detector, cfg: PipelineConfig):
    """
    PSF photometry with optional local grid search around the input position.

    The PSF kernel is rebuilt at each trial position because the subpixel phase
    changes the shifted/downsampled PSF. The best trial is selected by either:
    - "snr": highest signed flux/error
    - "chi2": lowest reduced chi-square

    Returns
    -------
    flux_uJy, err_uJy, info
    """
    detector = int(detector)

    if (not cfg.enable_psf_local_grid_search) or detector not in tuple(cfg.psf_grid_search_enabled_detectors):
        psf_kernel = extract_spherex_psf_kernel(hdul_like, x, y, cfg)
        flux_uJy, err_uJy, info = psf_flux_fit(flux_ujy, var_ujy2, flags, x, y, psf_kernel, cfg)
        info = dict(info)
        info.update({
            "psf_grid_status": "disabled",
            "psf_x_init": float(x),
            "psf_y_init": float(y),
            "psf_x_fit": float(x),
            "psf_y_fit": float(y),
            "psf_fit_offset_pix": 0.0,
        })
        return flux_uJy, err_uJy, info

    half = max(0.0, float(cfg.psf_local_grid_half_range_pix))
    step = max(1e-6, float(cfg.psf_local_grid_step_pix))
    offsets = np.arange(-half, half + 0.5 * step, step)

    best = None
    best_score = None
    n_trials = 0
    n_valid = 0
    metric = str(cfg.psf_local_grid_metric).lower()

    for dy in offsets:
        for dx in offsets:
            x_try = float(x + dx)
            y_try = float(y + dy)

            if not (0 <= x_try < flux_ujy.shape[1] and 0 <= y_try < flux_ujy.shape[0]):
                continue

            n_trials += 1

            try:
                psf_kernel = extract_spherex_psf_kernel(hdul_like, x_try, y_try, cfg)
                flux_try, err_try, info_try = psf_flux_fit(
                    flux_ujy,
                    var_ujy2,
                    flags,
                    x_try,
                    y_try,
                    psf_kernel,
                    cfg,
                )
            except Exception as exc:
                continue

            if info_try.get("psf_status") != "ok":
                continue

            if not (np.isfinite(flux_try) and np.isfinite(err_try) and err_try > 0):
                continue

            n_valid += 1

            if metric == "chi2":
                score = info_try.get("psf_reduced_chi2", np.inf)
                better = best is None or (np.isfinite(score) and score < best_score)
            else:
                score = flux_try / err_try
                better = best is None or (np.isfinite(score) and score > best_score)

            if better:
                best = (x_try, y_try, flux_try, err_try, info_try)
                best_score = float(score)

    if best is None:
        # Fall back to the unshifted position.
        try:
            psf_kernel = extract_spherex_psf_kernel(hdul_like, x, y, cfg)
            flux_uJy, err_uJy, info = psf_flux_fit(flux_ujy, var_ujy2, flags, x, y, psf_kernel, cfg)
        except Exception as exc:
            return np.nan, np.nan, {
                "psf_status": f"psf_error:{type(exc).__name__}",
                "psf_grid_status": "no_valid_trials",
                "psf_grid_n_trials": int(n_trials),
                "psf_grid_n_valid": int(n_valid),
                "psf_x_init": float(x),
                "psf_y_init": float(y),
                "psf_x_fit": float(x),
                "psf_y_fit": float(y),
                "psf_fit_offset_pix": 0.0,
            }

        info = dict(info)
        info.update({
            "psf_grid_status": "fallback_initial_position",
            "psf_grid_n_trials": int(n_trials),
            "psf_grid_n_valid": int(n_valid),
            "psf_x_init": float(x),
            "psf_y_init": float(y),
            "psf_x_fit": float(x),
            "psf_y_fit": float(y),
            "psf_fit_offset_pix": 0.0,
        })
        return flux_uJy, err_uJy, info

    x_best, y_best, flux_best, err_best, info_best = best
    info_best = dict(info_best)
    info_best.update({
        "psf_grid_status": "ok",
        "psf_grid_metric": metric,
        "psf_grid_best_score": float(best_score) if np.isfinite(best_score) else np.nan,
        "psf_grid_n_trials": int(n_trials),
        "psf_grid_n_valid": int(n_valid),
        "psf_x_init": float(x),
        "psf_y_init": float(y),
        "psf_x_fit": float(x_best),
        "psf_y_fit": float(y_best),
        "psf_fit_offset_pix": float(np.hypot(x_best - x, y_best - y)),
    })

    return flux_best, err_best, info_best


def aperture_flux_one_radius(flux_ujy, var_ujy2, flags, x, y, radius_pix,
                             cfg: PipelineConfig, remove_known_sources=True):
    """
    Measure background-subtracted circular-aperture flux for one cutout.

    The input image is already in uJy per pixel. The local background is
    estimated in an annulus, optionally sigma-clipped, then subtracted from the
    aperture sum. Negative fluxes are kept by default because they are valid
    noisy measurements for faint sources.
    """
    if not np.isfinite(x) or not np.isfinite(y):
        return np.nan, np.nan, np.nan, 0
    ny, nx = flux_ujy.shape
    if x < 0 or y < 0 or x >= nx or y >= ny:
        return np.nan, np.nan, np.nan, 0

    r = float(radius_pix)
    aperture = CircularAperture((x, y), r=r)
    annulus = CircularAnnulus((x, y), r_in=cfg.annulus_inner_scale * r, r_out=cfg.annulus_outer_scale * r)

    bad_mask = make_bad_pixel_mask(flags, flux_ujy, cfg.bad_flag_bits)

    if remove_known_sources:
        bkg_mask = make_bad_pixel_mask(flags, flux_ujy, cfg.bad_flag_bits + (21,))
    else:
        bkg_mask = bad_mask

    sigclip = SigmaClip(sigma=cfg.sigma_clip_sigma, maxiters=cfg.sigma_clip_maxiters)
    stats = ApertureStats(flux_ujy, annulus, mask=bkg_mask, sigma_clip=sigclip)

    if cfg.bg_method == "mean":
        bkg_per_pix = stats.mean
    elif cfg.bg_method == "median":
        bkg_per_pix = stats.median
    elif cfg.bg_method == "mode":
        bkg_per_pix = stats.mode
    else:
        raise ValueError(f"Unsupported background method: {cfg.bg_method}")

    if bkg_per_pix is None or not np.isfinite(bkg_per_pix):
        if remove_known_sources:
            return aperture_flux_one_radius(flux_ujy, var_ujy2, flags, x, y, radius_pix, cfg,
                                            remove_known_sources=False)
        return np.nan, np.nan, np.nan, count_bad_aperture_flags(flags, x, y, r, cfg.aperture_flag_count_bits)

    ap_weight = aperture.to_mask(method="exact").to_image(flux_ujy.shape)
    if ap_weight is None:
        return np.nan, np.nan, np.nan, count_bad_aperture_flags(flags, x, y, r, cfg.aperture_flag_count_bits)

    valid_weight = np.where(bad_mask, 0.0, ap_weight)
    ap_area = float(np.nansum(valid_weight))
    if not np.isfinite(ap_area) or ap_area <= 0:
        return np.nan, np.nan, np.nan, count_bad_aperture_flags(flags, x, y, r, cfg.aperture_flag_count_bits)

    phot = aperture_photometry(flux_ujy, aperture, mask=bad_mask, method="exact")
    flux = float(phot["aperture_sum"][0]) - float(bkg_per_pix) * ap_area

    if var_ujy2 is not None:
        var_mask = bad_mask | ~np.isfinite(var_ujy2)
        vtab = aperture_photometry(var_ujy2, aperture, mask=var_mask, method="exact")
        var_sum = float(vtab["aperture_sum"][0])
    else:
        var_sum = 0.0

    ann_mask_img = annulus.to_mask(method="center").to_image(flux_ujy.shape)
    n_bg = int(np.count_nonzero((ann_mask_img > 0) & (~bad_mask))) if ann_mask_img is not None else 0

    if n_bg > 0 and stats.std is not None and np.isfinite(stats.std):
        var_bkg_per_pix = float(stats.std) ** 2 / n_bg
    else:
        var_bkg_per_pix = 0.0

    if var_ujy2 is None and stats.std is not None and np.isfinite(stats.std):
        var_sum = float(stats.std) ** 2 * ap_area

    total_var = var_sum + ap_area ** 2 * var_bkg_per_pix
    err = float(np.sqrt(total_var)) if total_var >= 0 else np.nan
    n_bad = count_bad_aperture_flags(flags, x, y, r, cfg.aperture_flag_count_bits)

    if flux < 0 and not cfg.keep_negative_flux:
        flux, err = np.nan, np.nan

    return flux, err, ap_area, n_bad


def measure_cutout_photometry(row: dict, sapm_cache: dict, cfg: PipelineConfig) -> list[dict]:
    """
    Measure aperture and/or PSF photometry for one cutout.
    """
    if "image_hdu" not in row:
        return []

    image_hdu = row["image_hdu"]
    image = np.asarray(image_hdu.data, dtype=float)
    header = image_hdu.header
    detector = int(row["detector"])
    data_release = normalize_data_release(row.get("data_release", get_runtime_data_release(cfg)))
    if data_release == "unknown":
        data_release = infer_data_release_from_header(header)
    if data_release == "unknown":
        raise ValueError("Cannot measure cutout because the SPHEREx data release is unknown.")

    sapm_key = (data_release, detector)
    if sapm_key not in sapm_cache:
        sapm_cache[sapm_key] = load_sapm(detector, cfg, data_release)
    sapm_data, sapm_header = sapm_cache[sapm_key]

    sapm_use, image_slices, sapm_info = extract_sapm_for_cutout(
        sapm_data,
        header,
        image.shape,
    )
    image = image[image_slices]

    flux_ujy = convert_to_ujy(image, header, sapm_use, sapm_header)

    if cfg.subtract_zodi and row.get("zodi_hdu") is not None:
        zodi = np.asarray(row["zodi_hdu"].data, dtype=float)[image_slices]
        flux_ujy -= convert_to_ujy(zodi, header, sapm_use, sapm_header)

    var_ujy2 = None
    if row.get("variance_hdu") is not None:
        var = np.asarray(row["variance_hdu"].data, dtype=float)[image_slices]
        var_ujy2 = convert_variance_to_ujy2(var, header, sapm_use, sapm_header)

    flags = None
    if row.get("flags_hdu") is not None:
        flags = np.asarray(row["flags_hdu"].data)[image_slices]

    # If the image was clipped because the cutout partially crossed a detector
    # boundary, shift the source coordinates into the clipped cutout frame.
    x = float(row["x_src"]) - float(image_slices[1].start)
    y = float(row["y_src"]) - float(image_slices[0].start)

    measurements = []
    method = str(cfg.photometry_method).lower()

    if method in ("aperture", "both"):
        for radius in get_aperture_radii_for_detector(cfg, detector):
            flux_uJy, err_uJy, area_pix, n_bad = aperture_flux_one_radius(flux_ujy, var_ujy2, flags, x, y, radius, cfg)
            measurements.append({
                "wavelength": float(row["central_wavelength_um"]),
                "flux": flux_uJy * 1e-6 if np.isfinite(flux_uJy) else np.nan,
                "err": err_uJy * 1e-6 if np.isfinite(err_uJy) else np.nan,
                "flux_uJy": flux_uJy,
                "err_uJy": err_uJy,
                "detector": detector,
                "photometry_method": "aperture",
                "aperture_radius_pix": float(radius),
                "aperture_area_pix": area_pix,
                "n_bad_aperture_pixels": int(n_bad),
                "x": x,
                "y": y,
                "time_bounds_lower": row.get("time_bounds_lower", np.nan),
                "cutout_index": int(row.get("cutout_index", -1)),
                "uri": row.get("uri", ""),
                "local_uri": row.get("local_uri", ""),
                "download_status": row.get("download_status", ""),
                "data_release": data_release,
                "mjd_avg": row.get("mjd_avg", np.nan),
                "reference_ra_deg": row.get("reference_ra_deg", np.nan),
                "reference_dec_deg": row.get("reference_dec_deg", np.nan),
                "input_ra_deg": row.get("input_ra_deg", np.nan),
                "input_dec_deg": row.get("input_dec_deg", np.nan),
                "epoch_projection_status": row.get("epoch_projection_status", ""),
                "epoch_projection_sep_arcsec": row.get("epoch_projection_sep_arcsec", np.nan),
                **sapm_info,
                "status": "ok" if np.isfinite(flux_uJy) and np.isfinite(err_uJy) and err_uJy > 0 else "bad_photometry",
            })

    if method in ("psf", "both"):
        psf_flux_uJy = np.nan
        psf_err_uJy = np.nan
        psf_info = {"psf_status": "not_run"}

        try:
            if row.get("psf_hdu") is None:
                raise ValueError("No PSF HDU available.")
            hdul_like = fits.HDUList([fits.PrimaryHDU(), image_hdu, row["psf_hdu"]])
            psf_flux_uJy, psf_err_uJy, psf_info = psf_flux_fit_with_local_grid_search(
                hdul_like,
                flux_ujy,
                var_ujy2,
                flags,
                x,
                y,
                detector=detector,
                cfg=cfg,
            )
        except Exception as exc:
            psf_info = {"psf_status": f"psf_error:{type(exc).__name__}"}

        measurements.append({
            "wavelength": float(row["central_wavelength_um"]),
            "flux": psf_flux_uJy * 1e-6 if np.isfinite(psf_flux_uJy) else np.nan,
            "err": psf_err_uJy * 1e-6 if np.isfinite(psf_err_uJy) else np.nan,
            "flux_uJy": psf_flux_uJy,
            "err_uJy": psf_err_uJy,
            "detector": detector,
            "photometry_method": "psf",
            "aperture_radius_pix": np.nan,
            "aperture_area_pix": np.nan,
            "n_bad_aperture_pixels": count_bad_aperture_flags(
                flags,
                x,
                y,
                get_selected_aperture_radius_pix(cfg, detector),
                cfg.aperture_flag_count_bits,
            ),
            "x": psf_info.get("psf_x_fit", x),
            "y": psf_info.get("psf_y_fit", y),
            "x_init": x,
            "y_init": y,
            "time_bounds_lower": row.get("time_bounds_lower", np.nan),
            "cutout_index": int(row.get("cutout_index", -1)),
            "uri": row.get("uri", ""),
            "local_uri": row.get("local_uri", ""),
            "download_status": row.get("download_status", ""),
            "data_release": data_release,
            "mjd_avg": row.get("mjd_avg", np.nan),
            "reference_ra_deg": row.get("reference_ra_deg", np.nan),
            "reference_dec_deg": row.get("reference_dec_deg", np.nan),
            "input_ra_deg": row.get("input_ra_deg", np.nan),
            "input_dec_deg": row.get("input_dec_deg", np.nan),
            "epoch_projection_status": row.get("epoch_projection_status", ""),
            "epoch_projection_sep_arcsec": row.get("epoch_projection_sep_arcsec", np.nan),
            **sapm_info,
            "status": "ok" if np.isfinite(psf_flux_uJy) and np.isfinite(psf_err_uJy) and psf_err_uJy > 0 and psf_info.get("psf_status") == "ok" else "bad_photometry",
            **psf_info,
        })

    return measurements


def remove_outliers_per_detector(wl, flux, err, det, det_to_check, nbr_of_bins=8, sigma=3.0):
    """
    Remove strong per-detector outliers in coarse wavelength bins.

    The filter uses a median/MAD criterion independently in each detector band.
    Detectors not listed in ``det_to_check`` pass through unchanged.
    """
    ranges = {
        1: (0.75, 1.11),
        2: (1.11, 1.64),
        3: (1.64, 2.42),
        4: (2.42, 3.82),
        5: (3.82, 4.42),
        6: (4.42, 5.00),
    }
    out = [[], [], [], []]

    for d in np.unique(det):
        md = det == d
        wd, fd, ed = wl[md], flux[md], err[md]
        if len(wd) == 0:
            continue

        if int(d) not in det_to_check:
            out[0].extend(wd)
            out[1].extend(fd)
            out[2].extend(ed)
            out[3].extend([d] * len(wd))
            continue

        lo, hi = ranges.get(int(d), (np.nanmin(wd), np.nanmax(wd)))
        edges = np.linspace(lo, hi, int(nbr_of_bins) + 1)

        for i in range(len(edges) - 1):
            m = (wd >= edges[i]) & (wd < edges[i + 1])
            if not np.any(m):
                continue

            wb, fb, eb = wd[m], fd[m], ed[m]
            finite = np.isfinite(fb) & np.isfinite(eb) & (eb > 0)
            if not np.any(finite):
                continue

            med = np.nanmedian(fb[finite])
            mad = np.nanmedian(np.abs(fb[finite] - med))
            good = np.zeros_like(fb, dtype=bool)

            # If MAD is zero, avoid rejecting all equal-valued points.
            if not np.isfinite(mad) or mad == 0:
                good[finite] = True
            else:
                good[finite] = np.abs(fb[finite] - med) < float(sigma) * 1.4826 * mad

            out[0].extend(wb[good])
            out[1].extend(fb[good])
            out[2].extend(eb[good])
            out[3].extend([d] * np.count_nonzero(good))

    return tuple(map(np.array, out))


def get_spectral_channels_cache_dir(cfg: PipelineConfig, data_release: str) -> Path:
    """Return local cache directory for spectral_channels calibration files."""
    release = normalize_data_release(data_release)
    if release == "unknown":
        raise ValueError("Cannot choose spectral_channels cache directory because the SPHEREx data release is unknown.")
    path = Path(cfg.spectral_channels_cache_dir) / release
    if cfg.spectral_channels_collection:
        path = path / cfg.spectral_channels_collection
    path.mkdir(parents=True, exist_ok=True)
    return path


def _default_spectral_channels_s3_candidates(cfg: PipelineConfig, data_release: str) -> list[str]:
    """
    Build candidate S3 paths for the spectral_channels calibration file.

    Because SPHEREx calibration collection names may change, this only generates
    default candidates when cfg.spectral_channels_collection is supplied.
    """
    release = normalize_data_release(data_release)
    if release == "unknown":
        return []
    coll = cfg.spectral_channels_collection
    if not coll:
        return []

    return [
        (
            f"nasa-irsa-spherex/{release}/spectral_channels/"
            f"{coll}/spectral_channels_spx_{coll}.fits.gz"
        ),
        (
            f"nasa-irsa-spherex/{release}/spectral_channels/"
            f"{coll}/spectral_channels_{coll}.fits.gz"
        ),
    ]


def _render_spectral_channels_template(cfg: PipelineConfig, data_release: str) -> str | None:
    """Render user-supplied spectral_channels S3 template."""
    if cfg.spectral_channels_s3_template is None:
        return None
    release = normalize_data_release(data_release)
    if release == "unknown":
        return None
    return cfg.spectral_channels_s3_template.format(
        data_release=release,
        collection=cfg.spectral_channels_collection or "",
    )


def load_spectral_channels_calibration(cfg: PipelineConfig, data_release: str | None = None):
    """
    Load spectral_channels calibration from local cache or S3.

    Returns an astropy Table when possible, otherwise None.
    """
    release = get_runtime_data_release(cfg, data_release or "unknown")
    if release == "unknown":
        logging.warning("Cannot load spectral_channels calibration because the SPHEREx data release is unknown.")
        return None
    cache_dir = get_spectral_channels_cache_dir(cfg, release)

    local_candidates = sorted(cache_dir.glob("*.fits")) + sorted(cache_dir.glob("*.fits.gz"))
    if local_candidates and not cfg.redownload_spectral_channels:
        return read_spectral_channels_file(local_candidates[0])

    candidates = []
    rendered = _render_spectral_channels_template(cfg, release)

    if rendered:
        candidates.append(rendered)
    candidates.extend(_default_spectral_channels_s3_candidates(cfg, release))

    for s3_path in candidates:
        local_path = cache_dir / Path(s3_path).name
        tmp_path = local_path.with_suffix(local_path.suffix + ".part")
        try:
            with fits.open(f"s3://{s3_path}", fsspec_kwargs={"anon": True}) as hdul:
                hdul.writeto(tmp_path, overwrite=True)
            tmp_path.replace(local_path)
            return read_spectral_channels_file(local_path)
        except Exception as exc:
            logging.warning("Could not load spectral_channels from %s: %s", s3_path, exc)
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass

    return None


def read_spectral_channels_file(path: str | Path):
    """
    Read a spectral_channels FITS file into an astropy Table.

    The function is intentionally permissive because calibration layouts can vary:
    - if a binary table HDU exists, use the first one;
    - otherwise convert the first 2D image into a table-like detector/channel grid.
    """
    with fits.open(path) as hdul:
        for hdu in hdul:
            if isinstance(hdu, fits.BinTableHDU) and hdu.data is not None:
                return Table(hdu.data)

        for hdu in hdul:
            data = getattr(hdu, "data", None)
            if data is None:
                continue
            arr = np.asarray(data)
            if arr.ndim == 2:
                # Interpret as detectors x channels or channels x detectors.
                rows = []
                if 6 in arr.shape:
                    if arr.shape[0] == 6:
                        for det in range(1, 7):
                            for ch, wl in enumerate(arr[det - 1], start=1):
                                rows.append({"DETECTOR": det, "CHANNEL": ch, "WAVELENGTH": float(wl)})
                    else:
                        for det in range(1, 7):
                            for ch, wl in enumerate(arr[:, det - 1], start=1):
                                rows.append({"DETECTOR": det, "CHANNEL": ch, "WAVELENGTH": float(wl)})
                    return Table(rows=rows)

    return None


def _find_column_name(table: Table, candidates: tuple[str, ...]):
    """Find a table column by case-insensitive candidate names."""
    lower_to_name = {name.lower(): name for name in table.colnames}
    for cand in candidates:
        if cand.lower() in lower_to_name:
            return lower_to_name[cand.lower()]
    return None


def spectral_channel_edges_for_detector(table: Table, detector: int):
    """
    Extract wavelength bin edges/centers for one detector from a spectral_channels table.

    Supported layouts:
    - detector/channel rows with center wavelength
    - explicit min/max wavelength columns
    - detector-specific columns such as D1, DET1, BAND1, WAVE_D1
    """
    if table is None or len(table) == 0:
        return None, None

    det_col = _find_column_name(table, ("DETECTOR", "DET", "BAND"))
    ch_col = _find_column_name(table, ("CHANNEL", "CHAN", "CH", "CHANNEL_ID"))
    center_col = _find_column_name(
        table,
        ("WAVELENGTH", "WAVE", "LAMBDA", "LAMBDA_C", "WAVECEN", "WAVE_CEN", "LAMBDA_CEN", "WAVE_CENTER")
    )
    lo_col = _find_column_name(
        table,
        ("WAVE_MIN", "LAMBDA_MIN", "WAVEMIN", "LAM_MIN", "WAVE_LO", "LAMBDA_LO", "WAVELENGTH_MIN")
    )
    hi_col = _find_column_name(
        table,
        ("WAVE_MAX", "LAMBDA_MAX", "WAVEMAX", "LAM_MAX", "WAVE_HI", "LAMBDA_HI", "WAVELENGTH_MAX")
    )

    det_specific_col = _find_column_name(
        table,
        (
            f"D{int(detector)}",
            f"DET{int(detector)}",
            f"DETECTOR{int(detector)}",
            f"BAND{int(detector)}",
            f"LAMBDA_D{int(detector)}",
            f"WAVE_D{int(detector)}",
        )
    )

    if det_specific_col is not None and center_col is None:
        centers = np.asarray(table[det_specific_col], dtype=float)
        centers = centers[np.isfinite(centers)]
        if len(centers) >= 2:
            centers = np.sort(centers)
            mids = 0.5 * (centers[:-1] + centers[1:])
            first = centers[0] - (mids[0] - centers[0])
            last = centers[-1] + (centers[-1] - mids[-1])
            return np.concatenate([[first], mids, [last]]), centers

    if det_col is not None:
        rows = table[np.asarray(table[det_col], dtype=int) == int(detector)]
    else:
        rows = table

    if len(rows) == 0:
        return None, None

    if lo_col is not None and hi_col is not None:
        lo = np.asarray(rows[lo_col], dtype=float)
        hi = np.asarray(rows[hi_col], dtype=float)
        good = np.isfinite(lo) & np.isfinite(hi) & (hi > lo)
        lo, hi = lo[good], hi[good]
        if len(lo) == 0:
            return None, None
        order = np.argsort(0.5 * (lo + hi))
        lo, hi = lo[order], hi[order]
        centers = 0.5 * (lo + hi)
        edges = np.concatenate([[lo[0]], hi])
        return edges, centers

    if center_col is not None:
        raw_centers = np.asarray(rows[center_col], dtype=float)
        good = np.isfinite(raw_centers)
        centers = raw_centers[good]

        if len(centers) < 2:
            return None, None

        if ch_col is not None:
            raw_channels = np.asarray(rows[ch_col], dtype=float)
            channels = raw_channels[good]
            good2 = np.isfinite(channels)
            centers = centers[good2]
            channels = channels[good2]
            order = np.argsort(channels)
            centers = centers[order]
        else:
            centers = np.sort(centers)

        if len(centers) < 2:
            return None, None

        mids = 0.5 * (centers[:-1] + centers[1:])
        first = centers[0] - (mids[0] - centers[0])
        last = centers[-1] + (centers[-1] - mids[-1])
        edges = np.concatenate([[first], mids, [last]])
        return edges, centers

    return None, None


def _prepare_sorted_spectrum(wl, flux, err):
    """Filter, sort, and coadd duplicate wavelength samples before binning."""
    wl = np.asarray(wl, dtype=float)
    flux = np.asarray(flux, dtype=float)
    err = np.asarray(err, dtype=float)

    good = np.isfinite(wl) & np.isfinite(flux) & np.isfinite(err) & (err > 0)
    wl, flux, err = wl[good], flux[good], err[good]

    if len(wl) == 0:
        return wl, flux, err

    order = np.argsort(wl)
    wl, flux, err = wl[order], flux[order], err[order]

    unique_wl, unique_flux, unique_err = [], [], []
    for val in np.unique(wl):
        m = wl == val
        if np.count_nonzero(m) == 1:
            unique_wl.append(float(val))
            unique_flux.append(float(flux[m][0]))
            unique_err.append(float(err[m][0]))
        else:
            w = 1.0 / err[m] ** 2
            unique_wl.append(float(val))
            unique_flux.append(float(np.sum(w * flux[m]) / np.sum(w)))
            unique_err.append(float(np.sqrt(1.0 / np.sum(w))))

    return np.asarray(unique_wl), np.asarray(unique_flux), np.asarray(unique_err)


def _piecewise_linear_bin_average(wl, values, lo, hi):
    """Integrate a piecewise-linear spectrum over one wavelength bin."""
    if len(wl) < 2:
        return np.nan

    lo = float(lo)
    hi = float(hi)
    if hi <= lo:
        return np.nan

    lo_eff = max(lo, float(wl[0]))
    hi_eff = min(hi, float(wl[-1]))
    if hi_eff <= lo_eff:
        return np.nan

    internal = wl[(wl > lo_eff) & (wl < hi_eff)]
    grid = np.concatenate([[lo_eff], internal, [hi_eff]])
    vals = np.interp(grid, wl, values)
    integral = np.trapezoid(vals, grid)

    return float(integral / (hi_eff - lo_eff))


def _flux_conserving_integrated_bin(wl, flux, err, lo, hi, center, det_value, cfg: PipelineConfig):
    """Bin a spectrum by integrating across wavelength intervals while conserving flux density."""
    wl, flux, err = _prepare_sorted_spectrum(wl, flux, err)
    if len(wl) < 2:
        return None

    lo = float(lo)
    hi = float(hi)
    if hi <= lo:
        return None

    in_bin = (wl >= lo) & (wl < hi)
    n_in_bin = int(np.count_nonzero(in_bin))

    if n_in_bin < int(cfg.spectral_channels_min_points_per_bin):
        if not (hi > wl[0] and lo < wl[-1]):
            return None

    f_avg = _piecewise_linear_bin_average(wl, flux, lo, hi)
    if not np.isfinite(f_avg):
        return None

    if n_in_bin > 0:
        err_in = err[in_bin]
        if str(cfg.spectral_channels_integrate_errors).lower() == "weighted":
            w = 1.0 / err_in ** 2
            e_avg = float(np.sqrt(1.0 / np.sum(w)))
        else:
            e_avg = float(np.sqrt(np.sum(err_in ** 2)) / max(1, n_in_bin))
    else:
        e_avg = _piecewise_linear_bin_average(wl, err, lo, hi)

    if not np.isfinite(e_avg) or e_avg <= 0:
        return None

    return (float(center), f_avg, e_avg, int(det_value))


def _weighted_average_bin(flux_values, err_values, center_value, det_value):
    """Bin samples with inverse-variance weights inside fixed wavelength edges."""
    valid = np.isfinite(flux_values) & np.isfinite(err_values) & (err_values > 0)
    if not np.any(valid):
        return None

    weights = 1.0 / err_values[valid] ** 2
    return (
        float(center_value),
        float(np.sum(weights * flux_values[valid]) / np.sum(weights)),
        float(np.sqrt(1.0 / np.sum(weights))),
        int(det_value),
    )


def reduce_oversampling_with_spectral_channels(wl, flux, err, det, channels_table, cfg: PipelineConfig):
    """
    Reduce oversampling using the spectral_channels calibration.

    Modes:
    - integrate: flux-conserving piecewise-linear channel integration.
    - edges: inverse-variance weighted mean inside channel edges.
    - nearest: assign samples to nearest channel center.
    - auto: same as integrate.
    """
    wl_binned, flux_binned, err_binned, det_binned = [], [], [], []
    fallback_wl, fallback_flux, fallback_err, fallback_det = [], [], [], []

    mode = str(cfg.spectral_channels_bin_by).lower()

    for det_num in np.unique(det):
        det_num_int = int(det_num)
        mask_det = det == det_num
        wl_d = np.asarray(wl[mask_det], dtype=float)
        flux_d = np.asarray(flux[mask_det], dtype=float)
        err_d = np.asarray(err[mask_det], dtype=float)

        edges, centers = spectral_channel_edges_for_detector(channels_table, det_num_int)

        if edges is None or centers is None or len(edges) < 2:
            fallback_wl.extend(wl_d)
            fallback_flux.extend(flux_d)
            fallback_err.extend(err_d)
            fallback_det.extend([det_num_int] * len(wl_d))
            continue

        centers = np.asarray(centers, dtype=float)

        """
        # --------------------------------------------------------------
        # DEBUG: inspect spectral-channel assignment around 1.6 micron
        # --------------------------------------------------------------
        debug_lo = 1.50
        debug_hi = 1.65

        debug_mask = (
            np.isfinite(wl_d)
            & np.isfinite(flux_d)
            & np.isfinite(err_d)
            & (wl_d >= debug_lo)
            & (wl_d <= debug_hi)
        )

        if np.any(debug_mask):
            print(f"\nDEBUG spectral-channel assignment for detector {det_num_int}")
            print(f"Mode: {mode}")
            print(" idx | wavelength | flux | err | assigned_channel | channel_center | edge_lo | edge_hi")

            if mode == "nearest":
                assigned = np.argmin(np.abs(wl_d[:, None] - centers[None, :]), axis=1)
            else:
                assigned = np.searchsorted(edges, wl_d, side="right") - 1
                assigned = np.clip(assigned, 0, len(centers) - 1)

            for local_idx in np.where(debug_mask)[0]:
                ch = int(assigned[local_idx])
                edge_lo = edges[ch] if ch < len(edges) else np.nan
                edge_hi = edges[ch + 1] if ch + 1 < len(edges) else np.nan
                cen = centers[ch] if ch < len(centers) else np.nan

                print(
                    f"{local_idx:4d} | "
                    f"{wl_d[local_idx]:10.6f} | "
                    f"{flux_d[local_idx]:12.5e} | "
                    f"{err_d[local_idx]:12.5e} | "
                    f"{ch:4d} | "
                    f"{cen:10.6f} | "
                    f"{edge_lo:10.6f} | "
                    f"{edge_hi:10.6f}"
                )
        """

        if mode == "nearest":
            good = np.isfinite(wl_d) & np.isfinite(flux_d) & np.isfinite(err_d) & (err_d > 0)
            if not np.any(good):
                continue
            wl_good = wl_d[good]
            flux_good = flux_d[good]
            err_good = err_d[good]

            nearest = np.argmin(np.abs(wl_good[:, None] - centers[None, :]), axis=1)
            for j, cen in enumerate(centers):
                m = nearest == j
                if not np.any(m):
                    continue
                result = _weighted_average_bin(flux_good[m], err_good[m], cen, det_num_int)
                if result is not None:
                    wb, fb, eb, db = result
                    wl_binned.append(wb)
                    flux_binned.append(fb)
                    err_binned.append(eb)
                    det_binned.append(db)
            continue

        if mode == "integrate":
            for j in range(len(edges) - 1):
                lo = edges[j]
                hi = edges[j + 1]
                cen = centers[j] if j < len(centers) else 0.5 * (lo + hi)

                result = _flux_conserving_integrated_bin(
                    wl_d, flux_d, err_d, lo, hi, cen, det_num_int, cfg
                )
                if result is not None:
                    wb, fb, eb, db = result
                    wl_binned.append(wb)
                    flux_binned.append(fb)
                    err_binned.append(eb)
                    det_binned.append(db)
            continue

        for j in range(len(edges) - 1):
            lo = edges[j]
            hi = edges[j + 1]
            cen = centers[j] if j < len(centers) else 0.5 * (lo + hi)

            m = (wl_d >= lo) & (wl_d < hi)
            if not np.any(m):
                continue

            result = _weighted_average_bin(flux_d[m], err_d[m], cen, det_num_int)
            if result is not None:
                wb, fb, eb, db = result
                wl_binned.append(wb)
                flux_binned.append(fb)
                err_binned.append(eb)
                det_binned.append(db)

    if len(fallback_wl) > 0:
        fwl, fflux, ferr, fdet = reduce_oversampling_per_detector(
            np.asarray(fallback_wl),
            np.asarray(fallback_flux),
            np.asarray(fallback_err),
            np.asarray(fallback_det),
        )
        wl_binned.extend(fwl)
        flux_binned.extend(fflux)
        err_binned.extend(ferr)
        det_binned.extend(fdet)

    return tuple(map(np.array, (wl_binned, flux_binned, err_binned, det_binned)))


def reduce_oversampling_per_detector(wl, flux, err, det):
    """
    Reduce spectral oversampling with hard-coded detector resolving powers.

    This is the fallback path used when spectral_channels calibration is disabled
    or unavailable. Bins are inverse-variance weighted within each detector.
    """
    bands = {
        1: (0.75, 1.11, 41),
        2: (1.11, 1.64, 41),
        3: (1.64, 2.42, 41),
        4: (2.42, 3.82, 35),
        5: (3.82, 4.42, 110),
        6: (4.42, 5.00, 130),
    }
    out = [[], [], [], []]

    for d in np.unique(det):
        if int(d) not in bands:
            continue

        md = det == d
        wd, fd, ed = wl[md], flux[md], err[md]
        lo, hi, resolving_power = bands[int(d)]

        # Keep the historical 17-bin fallback grid but format it more clearly.
        edges = lo * (1 + 1 / resolving_power) ** np.arange(18)
        edges *= hi / edges[-1]

        for i in range(len(edges) - 1):
            m = (wd >= edges[i]) & (wd < edges[i + 1])
            if not np.any(m):
                continue

            fb, eb = fd[m], ed[m]
            good = np.isfinite(fb) & np.isfinite(eb) & (eb > 0)
            if not np.any(good):
                continue

            weights = 1.0 / eb[good] ** 2
            out[0].append(np.sqrt(edges[i] * edges[i + 1]))
            out[1].append(np.sum(weights * fb[good]) / np.sum(weights))
            out[2].append(np.sqrt(1.0 / np.sum(weights)))
            out[3].append(d)

    return tuple(map(np.array, out))


def build_spectrum_table(measurements: list[dict], aperture_radius_pix: float | Mapping[int, float] | None, photometry_method: str = "aperture") -> Table:
    """Select valid measurements and return a wavelength-sorted raw spectrum table.

    For aperture spectra, ``aperture_radius_pix`` may be either a single radius
    applied to every detector or a mapping from detector number to selected
    radius.
    """
    method = str(photometry_method).lower()
    if method == "psf":
        rows = [r for r in measurements if r.get("photometry_method") == "psf" and r["status"] == "ok"]
    else:
        rows = [
            r for r in measurements
            if r.get("photometry_method", "aperture") == "aperture"
               and aperture_radius_matches_detector_selection(r, aperture_radius_pix)
               and r["status"] == "ok"
        ]
    if not rows:
        return Table(names=("WAVELENGTH", "FLUX", "ERR", "DETECTOR"))
    wl = np.array([r["wavelength"] for r in rows])
    flux = np.array([r["flux"] for r in rows])
    err = np.array([r["err"] for r in rows])
    det = np.array([r["detector"] for r in rows])
    order = np.argsort(wl)
    return Table([wl[order], flux[order], err[order], det[order]], names=("WAVELENGTH", "FLUX", "ERR", "DETECTOR"))


def process_spectrum_table(spec: Table, cfg: PipelineConfig, reduce_oversampling_override: bool | None = None) -> Table:
    """Apply final filtering, optional outlier rejection, and optional spectral binning.

    ``reduce_oversampling_override=False`` is used by the diagnostic plot to
    produce the true unbinned comparison layer after applying the same clipping,
    sanitation, and outlier rejection as the final spectrum, but before spectral
    binning.  This avoids plotting a hybrid product.
    """
    if len(spec) == 0:
        return spec
    wl, flux, err, det = [np.asarray(spec[name]) for name in ("WAVELENGTH", "FLUX", "ERR", "DETECTOR")]
    if cfg.clip_flux_at_wavelength is not None:
        keep = wl >= float(cfg.clip_flux_at_wavelength)
        wl, flux, err, det = wl[keep], flux[keep], err[keep], det[keep]
    if cfg.sanitize_flux:
        # Keep negative fluxes, but remove non-finite values, zero placeholders, and invalid uncertainties.
        good = np.isfinite(wl) & np.isfinite(flux) & np.isfinite(err) & (err > 0) & (flux != 0)
        wl, flux, err, det = wl[good], flux[good], err[good], det[good]
    if cfg.remove_outliers:
        wl, flux, err, det = remove_outliers_per_detector(wl, flux, err, det, cfg.outlier_detectors, cfg.outlier_nbr_of_bins, cfg.outlier_sigma)

    do_reduce_oversampling = cfg.reduce_oversampling if reduce_oversampling_override is None else bool(reduce_oversampling_override)
    if do_reduce_oversampling:
        if cfg.use_spectral_channels_for_binning:
            channels_table = load_spectral_channels_calibration(cfg)
            if channels_table is not None:
                wl2, flux2, err2, det2 = reduce_oversampling_with_spectral_channels(
                    wl, flux, err, det, channels_table, cfg
                )
                if len(wl2) > 0:
                    wl, flux, err, det = wl2, flux2, err2, det2
                else:
                    logging.warning("spectral_channels binning produced no points; falling back to hard-coded bins.")
                    wl, flux, err, det = reduce_oversampling_per_detector(wl, flux, err, det)
            else:
                logging.warning("No spectral_channels calibration loaded; falling back to hard-coded bins.")
                wl, flux, err, det = reduce_oversampling_per_detector(wl, flux, err, det)
        else:
            wl, flux, err, det = reduce_oversampling_per_detector(wl, flux, err, det)
    order = np.argsort(wl)
    return Table([wl[order], flux[order], err[order], det[order]], names=("WAVELENGTH", "FLUX", "ERR", "DETECTOR"))


def compute_epoch_adjusted_coordinate_stats(cutouts: list[dict]) -> dict:
    """Compute mean and scatter of the per-cutout epoch-adjusted coordinates.

    The pipeline stores the proper-motion-propagated sky position used for each
    exposure in ``input_ra_deg`` and ``input_dec_deg``.  A direct arithmetic
    mean of RA can fail near the 0/360-degree boundary, so the mean position is
    computed from unit vectors on the sphere.  The reported RA and Dec scatters
    are small-angle standard deviations in arcseconds around the mean position,
    and ``pos_std_arcsec`` is the standard deviation of the radial separation
    from the mean position.
    """
    ras = np.asarray([row.get("input_ra_deg", np.nan) for row in cutouts], dtype=float)
    decs = np.asarray([row.get("input_dec_deg", np.nan) for row in cutouts], dtype=float)
    valid = np.isfinite(ras) & np.isfinite(decs)

    n_valid = int(np.count_nonzero(valid))
    if n_valid == 0:
        return {
            "mean_ra_deg": np.nan,
            "mean_dec_deg": np.nan,
            "ra_std_arcsec": np.nan,
            "dec_std_arcsec": np.nan,
            "pos_std_arcsec": np.nan,
            "pos_max_sep_arcsec": np.nan,
            "n_positions": 0,
        }

    ra_rad = np.deg2rad(ras[valid])
    dec_rad = np.deg2rad(decs[valid])

    # Spherical mean, robust against RA wrap-around at 0/360 degrees.
    x = np.cos(dec_rad) * np.cos(ra_rad)
    y = np.cos(dec_rad) * np.sin(ra_rad)
    z = np.sin(dec_rad)
    mean_vec = np.array([np.nanmean(x), np.nanmean(y), np.nanmean(z)], dtype=float)
    norm = np.linalg.norm(mean_vec)

    if not np.isfinite(norm) or norm <= 0:
        return {
            "mean_ra_deg": np.nan,
            "mean_dec_deg": np.nan,
            "ra_std_arcsec": np.nan,
            "dec_std_arcsec": np.nan,
            "pos_std_arcsec": np.nan,
            "pos_max_sep_arcsec": np.nan,
            "n_positions": n_valid,
        }

    mean_vec /= norm
    mean_ra = float(np.rad2deg(np.arctan2(mean_vec[1], mean_vec[0])) % 360.0)
    mean_dec = float(np.rad2deg(np.arcsin(np.clip(mean_vec[2], -1.0, 1.0))))

    # Small-angle component scatter around the mean position.
    dra_deg = ((ras[valid] - mean_ra + 180.0) % 360.0) - 180.0
    dra_arcsec = dra_deg * np.cos(np.deg2rad(mean_dec)) * 3600.0
    ddec_arcsec = (decs[valid] - mean_dec) * 3600.0

    ddof = 1 if n_valid > 1 else 0
    ra_std = float(np.nanstd(dra_arcsec, ddof=ddof)) if n_valid > 0 else np.nan
    dec_std = float(np.nanstd(ddec_arcsec, ddof=ddof)) if n_valid > 0 else np.nan

    mean_coord = SkyCoord(mean_ra * u.deg, mean_dec * u.deg, frame="icrs")
    coords = SkyCoord(ras[valid] * u.deg, decs[valid] * u.deg, frame="icrs")
    sep_arcsec = coords.separation(mean_coord).arcsec
    pos_std = float(np.nanstd(sep_arcsec, ddof=ddof)) if n_valid > 0 else np.nan
    pos_max = float(np.nanmax(sep_arcsec)) if n_valid > 0 else np.nan

    return {
        "mean_ra_deg": mean_ra,
        "mean_dec_deg": mean_dec,
        "ra_std_arcsec": ra_std,
        "dec_std_arcsec": dec_std,
        "pos_std_arcsec": pos_std,
        "pos_max_sep_arcsec": pos_max,
        "n_positions": n_valid,
    }


def print_epoch_adjusted_coordinate_stats(stats: dict) -> None:
    """Print a compact summary of the epoch-adjusted coordinate statistics."""
    mean_ra = stats.get("mean_ra_deg", np.nan)
    mean_dec = stats.get("mean_dec_deg", np.nan)
    n_pos = int(stats.get("n_positions", 0) or 0)

    if not (np.isfinite(mean_ra) and np.isfinite(mean_dec) and n_pos > 0):
        print("Mean epoch-adjusted coordinates: unavailable")
        return

    print(
        "Mean epoch-adjusted coordinates "
        f"({n_pos} cutouts): RA={mean_ra:.9f} deg, Dec={mean_dec:.9f} deg"
    )
    print(
        "Epoch-adjusted coordinate scatter: "
        f"RA={stats.get('ra_std_arcsec', np.nan):.4f} arcsec, "
        f"Dec={stats.get('dec_std_arcsec', np.nan):.4f} arcsec, "
        f"radial std={stats.get('pos_std_arcsec', np.nan):.4f} arcsec, "
        f"max separation={stats.get('pos_max_sep_arcsec', np.nan):.4f} arcsec"
    )


def add_epoch_adjusted_coordinate_header(header, stats: dict) -> None:
    """Add mean epoch-adjusted position and scatter metadata to a FITS header."""
    n_pos = int(stats.get("n_positions", 0) or 0)
    header["EPNPOS"] = (n_pos, "Number of epoch-adjusted positions")

    mean_ra = stats.get("mean_ra_deg", np.nan)
    mean_dec = stats.get("mean_dec_deg", np.nan)
    if np.isfinite(mean_ra):
        header["EPMRA"] = (float(mean_ra), "Mean epoch-adjusted RA [deg]")
    if np.isfinite(mean_dec):
        header["EPMDEC"] = (float(mean_dec), "Mean epoch-adjusted Dec [deg]")

    ra_std = stats.get("ra_std_arcsec", np.nan)
    dec_std = stats.get("dec_std_arcsec", np.nan)
    pos_std = stats.get("pos_std_arcsec", np.nan)
    pos_max = stats.get("pos_max_sep_arcsec", np.nan)
    if np.isfinite(ra_std):
        header["EPRASTD"] = (float(ra_std), "RA scatter about mean [arcsec]")
    if np.isfinite(dec_std):
        header["EPDESTD"] = (float(dec_std), "Dec scatter about mean [arcsec]")
    if np.isfinite(pos_std):
        header["EPRDSTD"] = (float(pos_std), "Radial sep. scatter [arcsec]")
    if np.isfinite(pos_max):
        header["EPMAX"] = (float(pos_max), "Max sep. from mean pos [arcsec]")


def save_spectrum_fits(
    spec: Table,
    ra: float,
    dec: float,
    object_name: str,
    cfg: PipelineConfig,
    photometry_method: str | None = None,
    coord_stats: dict | None = None,
):
    """Write one processed spectrum to a FITS binary table.

    Parameters
    ----------
    spec
        Final processed spectrum table for one photometry method.
    ra, dec
        Reference target coordinates in degrees.
    object_name
        Name used in the output filename.
    cfg
        Pipeline configuration.
    photometry_method
        Method label for the file name and FITS header.  When omitted, the
        value from cfg.photometry_method is used.  Passing this explicitly is
        important when cfg.photometry_method == "both", because aperture and
        PSF spectra must be written as separate products.
    coord_stats
        Optional statistics of the per-cutout epoch-adjusted coordinates.
        When provided, these values are written to the primary FITS header.
    """
    ensure_output_directories(cfg.output_dir)
    method = str(photometry_method or cfg.photometry_method).lower().strip()

    hdu0 = fits.PrimaryHDU()
    hdu0.header["TELESCOP"] = "SPHEREx"
    data_release = get_runtime_data_release(cfg)
    if data_release != "unknown":
        hdu0.header["DATAREL"] = data_release
    hdu0.header["TARGET"] = f"{ra:.6f},{dec:.6f}"
    hdu0.header["REFRA"] = (float(ra), "Input reference RA [deg]")
    hdu0.header["REFDEC"] = (float(dec), "Input reference Dec [deg]")
    if cfg.reference_epoch_yr is not None:
        hdu0.header["REFEPOCH"] = (float(cfg.reference_epoch_yr), "Reference epoch [decimal year]")
    if cfg.pmra_masyr is not None:
        hdu0.header["PMRA"] = (float(cfg.pmra_masyr), "Proper motion RA*cosDec [mas/yr]")
    if cfg.pmdec_masyr is not None:
        hdu0.header["PMDEC"] = (float(cfg.pmdec_masyr), "Proper motion Dec [mas/yr]")
    hdu0.header["PHOTMET"] = (method, "Photometry method used for this spectrum")
    if coord_stats is not None:
        add_epoch_adjusted_coordinate_header(hdu0.header, coord_stats)

    hdul = fits.HDUList([hdu0, fits.BinTableHDU(spec, name="SPECTRUM")])
    out = Path(cfg.output_dir, "fits", f"{object_name}_{method}_spectrum.fits")
    hdul.writeto(out, overwrite=True)
    print(f"Saved {method} spectrum: {out}")


def save_measurements_fits(measurements: list[dict], object_name: str, cfg: PipelineConfig):
    """Write the optional per-cutout measurement table to FITS."""
    if not measurements:
        return
    ensure_output_directories(cfg.output_dir)
    table = Table(rows=measurements)
    out = Path(cfg.output_dir, "fits", f"{object_name}_measurements.fits")
    fits.HDUList([fits.PrimaryHDU(), fits.BinTableHDU(table, name="MEASUREMENTS")]).writeto(out, overwrite=True)
    print(f"Saved raw measurements: {out}")


def make_broad_shape_spline_points(x, y, n_bins: int = 35, min_points_per_bin: int = 2, sigma_clip: float | None = 3.0):
    """Return binned median anchor points for a broad-shape spectrum guide.

    This deliberately does not interpolate every oversampled measurement.  The
    spectrum is first compressed into wavelength bins, each bin is summarized by
    a robust median flux, and the diagnostic guide line is drawn through those
    anchors.  The result is a visual low-frequency spectral-shape guide while
    the original data points remain unchanged.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    good = np.isfinite(x) & np.isfinite(y)
    x = x[good]
    y = y[good]

    if x.size < 3:
        return np.array([], dtype=float), np.array([], dtype=float)

    order = np.argsort(x)
    x = x[order]
    y = y[order]

    n_bins = int(max(3, min(int(n_bins), x.size)))
    min_points_per_bin = int(max(1, min_points_per_bin))
    edges = np.linspace(float(np.nanmin(x)), float(np.nanmax(x)), n_bins + 1)

    xb = []
    yb = []
    for i in range(n_bins):
        if i == n_bins - 1:
            in_bin = (x >= edges[i]) & (x <= edges[i + 1])
        else:
            in_bin = (x >= edges[i]) & (x < edges[i + 1])

        yy = y[in_bin]
        xx = x[in_bin]
        valid = np.isfinite(xx) & np.isfinite(yy)
        xx = xx[valid]
        yy = yy[valid]

        if yy.size < min_points_per_bin:
            continue

        if sigma_clip is not None and np.isfinite(float(sigma_clip)) and yy.size >= 4:
            clip = SigmaClip(sigma=float(sigma_clip), maxiters=3)
            clipped = clip(yy)
            keep = ~np.asarray(clipped.mask, dtype=bool)
            xx = xx[keep]
            yy = yy[keep]
            if yy.size < min_points_per_bin:
                continue

        xb.append(float(np.nanmedian(xx)))
        yb.append(float(np.nanmedian(yy)))

    xb = np.asarray(xb, dtype=float)
    yb = np.asarray(yb, dtype=float)
    good = np.isfinite(xb) & np.isfinite(yb)
    xb = xb[good]
    yb = yb[good]

    # PCHIP requires strictly increasing x values.  Merge rare duplicate anchor
    # wavelengths by taking the median y value at each unique x.
    if xb.size:
        unique_x = []
        unique_y = []
        for ux in np.unique(xb):
            same = xb == ux
            unique_x.append(float(ux))
            unique_y.append(float(np.nanmedian(yb[same])))
        xb = np.asarray(unique_x, dtype=float)
        yb = np.asarray(unique_y, dtype=float)

    return xb, yb


def _spectrum_plot_arrays(spec: Table, cfg: PipelineConfig):
    """Return wavelength, plotted flux, and plotted error arrays for diagnostic plotting."""
    wl = np.asarray(spec["WAVELENGTH"], dtype=float) * u.um
    flux = np.asarray(spec["FLUX"], dtype=float) * u.Jy
    err = np.asarray(spec["ERR"], dtype=float) * u.Jy
    if cfg.plot_flux_lambda:
        fl = flux_to_flux_lambda(wl, flux)
        er = flux_to_flux_lambda(wl, err)
    else:
        fl = flux
        er = err

    x = np.asarray(wl.value, dtype=float)
    y = np.asarray(fl.value, dtype=float)
    e = np.asarray(er.value, dtype=float)
    good = np.isfinite(x) & np.isfinite(y) & np.isfinite(e) & (e > 0)
    x, y, e = x[good], y[good], e[good]
    if x.size:
        order = np.argsort(x)
        x, y, e = x[order], y[order], e[order]
    return x, y, e, fl.unit


def add_spectral_channel_overlay(ax, cfg, detectors=(1, 2, 3, 4, 5, 6),
                                 wl_min=None, wl_max=None):
    """
    Overlay SPHEREx spectral-channel bins on an existing spectrum plot.
    Uses the same spectral_channels calibration loader as the binning code.
    """

    if not cfg.use_spectral_channels_for_binning:
        return

    channels_table = load_spectral_channels_calibration(cfg)

    if channels_table is None:
        print("WARNING: no spectral_channels calibration table available for plot overlay.")
        return

    for det in detectors:
        edges, centers = spectral_channel_edges_for_detector(channels_table, det)

        if edges is None or centers is None or len(edges) < 2:
            print(f"WARNING: no spectral-channel edges available for D{det}")
            continue

        for j in range(len(edges) - 1):
            lo = float(edges[j])
            hi = float(edges[j + 1])

            if wl_min is not None and hi < wl_min:
                continue
            if wl_max is not None and lo > wl_max:
                continue

            ax.axvline(
                lo,
                color="tab:blue",
                alpha=0.25,
                linewidth=0.5,
                zorder=0,
            )

        ax.axvline(
            float(edges[-1]),
            color="tab:blue",
            alpha=0.25,
            linewidth=0.5,
            zorder=0,
        )

        """
        ax.axvline(
            float(edges[0]),
            color="tab:red",
            alpha=0.6,
            linewidth=1.0,
            linestyle="--",
            zorder=1,
        )
        """

        if det < 6:
            ax.axvline(
                float(edges[-1]),
                color="tab:red",
                alpha=0.6,
                linewidth=1.0,
                linestyle="--",
                zorder=1,
            )


def plot_spectrum(
    spec: Table,
    object_name: str,
    cfg: PipelineConfig,
    photometry_method: str | None = None,
    raw_spec: Table | None = None,
):
    """Create one diagnostic spectrum plot in F_lambda or F_nu units.

    By default, the plotted points and spline both come from ``spec``.  If
    ``cfg.plot_unbinned_points_with_binned_spline`` is True and ``raw_spec`` is
    supplied, the points come from the explicitly unbinned-but-filtered spectrum
    while the dense PCHIP spline is computed only from the final binned spectrum
    in ``spec``.  The optional binned-point overlay shows the exact spline
    anchors, making it obvious that the line is not computed from the unbinned
    cloud.
    """
    if len(spec) == 0:
        return
    ensure_output_directories(cfg.output_dir)
    method = str(photometry_method or cfg.photometry_method).lower().strip()

    use_raw_points = bool(getattr(cfg, "plot_unbinned_points_with_binned_spline", False)) and raw_spec is not None and len(raw_spec) > 0

    # The spline source remains the final/binned spectrum.  The point source can
    # optionally be the unbinned spectrum for visual diagnostics.
    x_line, y_line, e_line, flux_unit = _spectrum_plot_arrays(spec, cfg)
    if use_raw_points:
        x, y, e, _ = _spectrum_plot_arrays(raw_spec, cfg)
    else:
        x, y, e = x_line, y_line, e_line

    if len(x) == 0:
        return

    plt.figure(figsize=(12, 6))
    plt.rcParams.update(
        {
            "font.size": 14,
            "font.family": "Arial",
            "axes.formatter.limits": [-0, 0],
            "text.usetex": False,
            "mathtext.fontset": "custom",
            "mathtext.rm": "Arial",
        }
    )
    color = cfg.plot_color

    if len(x_line) >= 3 and cfg.plot_spline:
        if use_raw_points:
            # Requested diagnostic mode: draw the original dense PCHIP spline
            # through the final binned spectrum, over the unbinned points.
            xd = np.linspace(float(np.nanmin(x_line)), float(np.nanmax(x_line)), int(cfg.spline_density))
            plt.plot(xd, PchipInterpolator(x_line, y_line)(xd), lw=1, c=color, alpha=0.4, zorder=3, label="PCHIP through final binned spectrum")
        else:
            spline_mode = str(getattr(cfg, "spline_mode", "binned_median") or "binned_median").lower().strip()
            if spline_mode in ("interpolate", "pchip", "connect_points"):
                # Backward-compatible behavior: draw a PCHIP curve through every
                # sorted measurement point.  This can be too wiggly for oversampled
                # SPHEREx spectra, but remains available for diagnostics.
                xd = np.linspace(x_line.min(), x_line.max(), cfg.spline_density)
                plt.plot(xd, PchipInterpolator(x_line, y_line)(xd), lw=1, c=color, alpha=0.4, zorder=2, label="PCHIP spline")
            else:
                # Default behavior: draw a broad-shape guide through robust binned
                # medians, not through every oversampled point.
                xb, yb = make_broad_shape_spline_points(
                    x_line,
                    y_line,
                    n_bins=getattr(cfg, "spline_n_bins", 35),
                    min_points_per_bin=getattr(cfg, "spline_min_points_per_bin", 2),
                    sigma_clip=getattr(cfg, "spline_sigma_clip", 3.0),
                )
                if len(xb) >= 3:
                    xd = np.linspace(xb.min(), xb.max(), cfg.spline_density)
                    plt.plot(xd, PchipInterpolator(xb, yb)(xd), lw=1, c=color, alpha=0.4, zorder=2, label="binned-median broad-shape spline")

    plt.errorbar(
        x,
        y,
        yerr=e,
        fmt="o",
        ms=4,
        color=to_rgba(color, alpha=0.2),
        capsize=0,
        elinewidth=0.8,
        markeredgewidth=0,
        markerfacecolor=color,
        zorder=1,
        label="unbinned filtered measurements" if use_raw_points else "spectrum points",
    )
    if use_raw_points and bool(getattr(cfg, "plot_binned_points_with_unbinned_overlay", False)):
        plt.errorbar(
            x_line,
            y_line,
            yerr=e_line,
            fmt="o",
            ms=5,
            color=color,
            capsize=0,
            elinewidth=0.8,
            markeredgewidth=0.8,
            markerfacecolor="white",
            zorder=4,
            label="final binned spectrum points",
        )
    ax = plt.gca()
    if cfg.plot_spectral_channel_overlay:
        add_spectral_channel_overlay(
            ax,
            cfg,
            detectors=cfg.plot_spectral_channel_overlay_detectors,
            wl_min=cfg.plot_spectral_channel_overlay_wl_min,
            wl_max=cfg.plot_spectral_channel_overlay_wl_max,
        )
    if cfg.reduce_oversampling and (use_raw_points or bool(getattr(cfg, "plot_binned_points_with_unbinned_overlay", False))):
        handles, _ = ax.get_legend_handles_labels()
        if cfg.plot_spectral_channel_overlay:
            handles.append(
                Line2D(
                    [0],
                    [0],
                    color="tab:blue",
                    linestyle="-",
                    linewidth=1.0,
                    alpha=0.7,
                    label="Spectral-channel bins",
                )
            )
            handles.append(
                Line2D(
                    [0],
                    [0],
                    color="tab:red",
                    linestyle="--",
                    linewidth=1.0,
                    alpha=0.7,
                    label="Detector boundaries",
                )
            )
        ax.legend(
            frameon=True,
            handles=handles,
            facecolor="white",
            framealpha=0.85,
            fontsize=10,
            fancybox=False,
        )
    if cfg.plot_vertical_line:
        plt.axvline(cfg.vertical_line_position, color="tab:red", linewidth=1, linestyle="--")
    formatter = ScalarFormatter(useMathText=True)
    formatter.set_scientific(True)
    ax.yaxis.set_major_formatter(formatter)
    plt.xlabel("Wavelength ($\\mu$m)")
    plt.ylabel(f"Flux ({flux_unit.to_string('latex_inline')})")
    # suffix = " — unbinned points, binned spline" if use_raw_points else ""
    suffix = ""
    plt.title(f"SPHEREx {method if method == 'aperture' else method.upper()} spectrum of {object_name}{suffix}")
    plt.grid(color="silver", linestyle="-", linewidth=0.5, alpha=0.5)
    out = Path(cfg.output_dir, "plots", f"{object_name}_{method}_spectrum.{cfg.plot_format}")
    plt.savefig(out, dpi=300, bbox_inches="tight", format=cfg.plot_format)
    plt.close()
    print(f"Saved {method} plot: {out}")


def run_spherex_pipeline(ra: float, dec: float, object_name: str | None = None, cfg: PipelineConfig | None = None):
    """Run the full SPHEREx extraction workflow and return the processed spectrum table."""
    if cfg is None:
        cfg = PipelineConfig()
    validate_config(cfg)
    object_name = make_object_name(ra, dec, object_name)
    ensure_output_directories(cfg.output_dir)

    if cfg.query_irsa_for_cutouts:
        print("Querying SPHEREx cutouts...")
        cutout_table = query_spherex_cutouts(ra, dec, cfg)
        print(f"Found {len(cutout_table)} cutouts")

        print("Downloading/caching cutouts...")
        prepared_rows = download_cutout_files_parallel(cutout_table, object_name, cfg, ra=ra, dec=dec)
        n_cached = sum(1 for r in prepared_rows if r.get("download_status") == "cached")
        n_failed = sum(1 for r in prepared_rows if str(r.get("download_status", "")).startswith("download_failed"))
        print(f"Prepared {len(prepared_rows)} files ({n_cached} reused from cache, {n_failed} failed)")
        prepared_release = infer_unique_data_release(prepared_rows)
        if prepared_release not in ("unknown", "mixed"):
            set_runtime_data_release(cfg, prepared_release)
    else:
        print("Skipping IRSA query; using locally cached cutouts...")
        prepared_rows = prepare_cached_cutout_rows(object_name, cfg)
        print(f"Found {len(prepared_rows)} cached cutout files in {get_object_download_dir(cfg, object_name)}")
        prepared_release = infer_unique_data_release(prepared_rows)
        if prepared_release not in ("unknown", "mixed"):
            print(f"SPHEREx data release inferred from cached file paths: {prepared_release.upper()}")
            set_runtime_data_release(cfg, prepared_release)

    print("Opening cached cutouts...")
    cutouts = open_cutouts_parallel(prepared_rows, ra, dec, cfg)
    good_cutouts = [r for r in cutouts if "image_hdu" in r]
    opened_release = infer_unique_data_release(good_cutouts)
    if opened_release not in ("unknown", "mixed"):
        set_runtime_data_release(cfg, opened_release)
        print(f"SPHEREx data release used for calibration lookup: {opened_release.upper()}")
    elif opened_release == "mixed":
        print("WARNING: mixed SPHEREx data releases detected; calibration lookup will use per-cutout releases where possible.")
    else:
        print("WARNING: could not infer SPHEREx data release from opened cutouts.")
    print(f"Opened {len(good_cutouts)} usable cutouts")

    coord_stats = compute_epoch_adjusted_coordinate_stats(good_cutouts)
    print_epoch_adjusted_coordinate_stats(coord_stats)

    append_manifest_rows(
        build_cutout_manifest_rows(prepared_rows, cutouts, object_name, cfg),
        object_name,
        cfg,
        basename="cutout_manifest",
    )

    print("Performing photometry...")
    sapm_cache = {}
    measurements = []
    for row in good_cutouts:
        measurements.extend(measure_cutout_photometry(row, sapm_cache, cfg))

    if cfg.save_raw_measurements:
        save_measurements_fits(measurements, object_name, cfg)

    append_manifest_rows(measurements, object_name, cfg, basename="measurement_manifest")

    requested_method = str(cfg.photometry_method).lower().strip()
    methods_to_write = ("aperture", "psf") if requested_method == "both" else (requested_method,)

    final_specs: dict[str, Table] = {}
    for method in methods_to_write:
        print(f"Building {method} spectrum...")
        selected_aperture = (
            {det: get_selected_aperture_radius_pix(cfg, det) for det in range(1, 7)}
            if method == "aperture"
            else None
        )
        raw_spec = build_spectrum_table(
            measurements,
            selected_aperture,
            photometry_method=method,
        )
        # This is the true unbinned comparison layer: same clipping/sanitation/outlier
        # handling as the final spectrum, but explicitly before oversampling reduction.
        unbinned_plot_spec = process_spectrum_table(raw_spec, cfg, reduce_oversampling_override=False)
        final_spec = process_spectrum_table(raw_spec, cfg)
        final_specs[method] = final_spec
        save_spectrum_fits(
            final_spec,
            ra,
            dec,
            object_name,
            cfg,
            photometry_method=method,
            coord_stats=coord_stats,
        )
        if cfg.plot_spectrum:
            plot_spectrum(final_spec, object_name, cfg, photometry_method=method, raw_spec=unbinned_plot_spec)

    measurements_table = Table(rows=measurements) if measurements else Table()

    # Backward-compatible return value for single-method runs.  When both
    # methods are requested, return a dictionary keyed by method name so callers
    # can access both final spectra without rerunning the pipeline.
    if requested_method == "both":
        return final_specs, measurements_table
    return final_specs[requested_method], measurements_table
