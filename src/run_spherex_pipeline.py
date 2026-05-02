from astropy.time import Time

from spexpi.spherex_pipeline import PipelineConfig, run_spherex_pipeline

# ------------------------------------------------------
# Spectral standards
# ------------------------------------------------------

ra, dec = 265.349, 25.882
object_name = "T9 WISEP J174124.25+255319.5"
fits_dir = "standards/data_alt"

ra, dec = 63.849, -9.582
object_name = "T8 2MASSI J0415195-093506"
fits_dir = "spherex_qr2_downloads"

ra, dec = 111.835, 17.161
object_name = "T7 2MASSI J0727182+171001"
fits_dir = "spherex_qr2_downloads"

ra, dec = 226.6945, 70.4635
object_name = "T6 2MASS J15065257+7027247"
fits_dir = "standards/data_alt"

ra, dec = 225.833, 25.425
object_name = "T5 2MASS J15031961+2525196"
fits_dir = "standards/data"

ra, dec = 343.580, 31.398
object_name = "T4 2MASSI J2254188+312349"
fits_dir = "standards/data"

ra, dec = 104.043, 42.092
object_name = "T3 2MASS J06560926+4205301"
fits_dir = "standards/data_alt"

ra, dec = 193.722, -1.380
object_name = "T2 SDSSp J125453.90-012247.4"
fits_dir = "standards/data"

ra, dec = 191.624, -31.663
object_name = "T1 2MASS J12462965-3139280"
fits_dir = "standards/data_alt"

ra, dec = 181.944, 2.740
object_name = "T0 SDSS J120747.17+024424.8"
fits_dir = "spherex_qr2_downloads"

ra, dec = 43.777, -47.019
object_name = "L9 DENIS-P J0255-4700"
fits_dir = "standards/data"

object_name = "L8 2MASSW J1632291+190441"
ra, dec = 248.123048, 19.0776561
pmra, pmdec = 233.784, -58.5  # NSC DR2
ref_epoch = Time("2017-08-07 06:15:33").decimalyear

object_name = "L7 2MASSW J2148162+400359"
ra, dec = 327.0723955, 40.0685178
pmra, pmdec = 772.176, 458.243
ref_epoch = 2016.0

object_name = "L6 2MASSI J1010148-040649"
ra, dec = 152.561696, -4.11387
pmra, pmdec = -324.2, -17.8  # 2020AJ....159..257B
ref_epoch = 2000.0

object_name = "L5 SDSS J083506.16+195304.4"
ra, dec = 128.775097, 19.884142
pmra, pmdec = -141.852, -142.771  # NSC DR2
ref_epoch = Time("2016-10-24 03:31:24").decimalyear

object_name = "L4 2MASS J21580457-1550098"
ra, dec = 329.519261, -15.836336
pmra, pmdec = 45.951, -63.481
ref_epoch = 2016.0

"""
object_name = "L3 2MASSW J1506544+132106"
ra, dec = 226.721482, 13.3516252
pmra, pmdec = -1071.073, -11.8
ref_epoch = 2016.0

object_name = "L2 Kelu-1"
ra, dec = 196.415845, -25.6850415
pmra, pmdec = -305.371, -27.326
ref_epoch = 2016.0

object_name = "L1 2MASSW J1439284+192915"
ra, dec = 219.8614407, 19.4894642
pmra, pmdec = -1241.001, 385.125
ref_epoch = 2016.0

object_name = "L0 2MASP J0345432+254023"
ra, dec = 56.4293698, 25.6729385
pmra, pmdec = -95.363, -41.319
ref_epoch = 2016.0

object_name = "M9 LHS 2924"
ra, dec = 217.1782723, 33.1744121
pmra, pmdec = -346.961, -710.986
ref_epoch = 2016.0

object_name = "M8 VB 10"
ra, dec = 289.2373737, 5.1443733
pmra, pmdec = -598.761, -1366.063
ref_epoch = 2016.0

object_name = "M7 VB 8"
ra, dec = 253.8932463, -8.398523
pmra, pmdec = -813.038, -870.609
ref_epoch = 2016.0
"""

# pmra, pmdec = 0, 0
# ref_epoch = Time("2017-10-11 07:58:57").decimalyear

photometry_method = "both"  # "aperture" or "psf"
outlier_nbr_of_bins = 8

cfg = PipelineConfig(

    # ============================================================
    # 1. PHOTOMETRY MODE & CORE SETTINGS
    # ============================================================
    photometry_method=photometry_method,  # "aperture", "psf", or "both"

    # --- Aperture photometry ---
    selected_aperture_radius_pix=2.0,  # main radius used for final spectrum
    aperture_radii_pix=(1.0, 2.0, 3.0),  # radii tested (useful for diagnostics / robustness)

    # --- PSF photometry ---
    psf_kernel_radius_native=5,  # PSF kernel half-size (native pixels)
    psf_shift_sign=1.0,  # sign convention for subpixel shift
    psf_fit_background_gradient=False,  # fit background gradient (usually not needed)

    # ============================================================
    # 2. PSF LOCAL GRID SEARCH (centroid refinement)
    # ============================================================
    enable_psf_local_grid_search=True,

    # Search window around initial WCS position
    psf_local_grid_half_range_pix=1.0,  # typical: 1.0–2.0 (larger = more robust but slower)

    # Sampling step
    psf_local_grid_step_pix=0.25,  # fine grid; use 0.5 if half_range >= 3.0

    # Optimization metric
    psf_local_grid_metric="snr",  # "snr" (robust) or "chi2" (more sensitive)

    # Apply to all detectors
    psf_grid_search_enabled_detectors=(1, 2, 3, 4, 5, 6),

    # ============================================================
    # 3. OUTLIER REJECTION & SPECTRAL CLEANING
    # ============================================================
    remove_outliers=True,  # sigma-clipping per detector
    outlier_detectors=(1, 2, 3, 4, 5, 6),  # detectors to clean
    outlier_nbr_of_bins=outlier_nbr_of_bins,  # spectral bins for local statistics

    keep_negative_flux=True,  # set True if you want to keep faint/noisy flux points

    # ============================================================
    # 4. SPECTRAL BINNING / OVERSAMPLING CONTROL
    # ============================================================
    reduce_oversampling=True,  # enforce detector resolution (recommended)

    use_spectral_channels_for_binning=True,  # use QR2 calibration (preferred over hard-coded bands)
    spectral_channels_min_points_per_bin=1,
    spectral_channels_bin_by="integrate",  # best choice for flux-conserving spectra
    # alternatives: "edges", "nearest", "auto"

    spectral_channels_cache_dir="../resources/spherex_calibration_files/spherex_spectral_channels_cache",
    redownload_spectral_channels=False,
    spectral_channels_collection="cal-sch-v1-2026-106",

    # ============================================================
    # 5. DATA INPUT / DOWNLOAD / CACHING
    # ============================================================
    cutout_size_arcsec=120,  # cutout size
    max_workers=8,  # parallel download threads (adjust based on your system and network)

    download_dir="../resources/standards/data",  # local cache directory
    redownload_existing_files=False,  # reuse cached FITS

    # If False → skip IRSA query and use existing local FITS
    query_irsa_for_cutouts=True,
    cached_cutout_glob="*.fits",

    show_download_progress=True,

    # ============================================================
    # 6. SAPM (CALIBRATION) HANDLING
    # ============================================================
    sapm_cache_dir="../resources/spherex_calibration_files/spherex_sapm_cache",
    redownload_sapm_files=False,
    sapm_collection="cal-sapm-v2-2025-164",

    # ============================================================
    # 7. OUTPUT & VISUALIZATION
    # ============================================================
    output_dir="../resources/standards",
    plot_spectrum=True,

    # ============================================================
    # 8. OPTIONAL: PROPER MOTION / EPOCH PROPAGATION
    # ============================================================
    # Enable for high proper-motion objects
    reference_epoch_yr=ref_epoch,
    pmra_masyr=pmra,
    pmdec_masyr=pmdec,
)

run_spherex_pipeline(ra, dec, object_name=object_name, cfg=cfg)
