from astropy.time import Time

from spexpi.spherex_pipeline import PipelineConfig, run_spherex_pipeline

# ------------------------------------------------------
# Spectral standards
# ------------------------------------------------------

object_name = "T9 WISEP J174124.25+255319.5"
ra, dec = 265.352586, 25.892878  # 2MASS
pmra, pmdec = -495, -1472  # 2013ApJ...762..119M
ref_epoch = Time("2000-04-11").decimalyear  # 2MASS

object_name = "T8 2MASSI J0415195-093506"
# Bad results
# ra, dec = 63.831432, -9.585187  # 2MASS
# pmra, pmdec = 2193, 527  # 2009AJ....137....1F
# ref_epoch = Time("1998-11-15").decimalyear  # 2MASS
ra, dec = 63.849, -9.582  # determined from stacked SPHEREx images
ref_epoch = None

object_name = "T7 2MASSI J0727182+171001"
ra, dec = 111.826025, 17.167002  # 2MASS
pmra, pmdec = 1046, -767  # 2009AJ....137....1F
ref_epoch = Time("1997-10-29").decimalyear  # 2MASS
# selected_aperture_radius_pix=1.0
# psf_local_grid_half_range_pix=0.5
# keep_negative_flux = False

object_name = "T6 2MASS J15065257+7027247"
ra, dec = 226.7026361, 70.4616191
pmra, pmdec = -1194.179, 1042.194
ref_epoch = 2016.0

object_name = "T5 2MASS J15031961+2525196"
ra, dec = 225.8321423, 25.4246445
pmra, pmdec = 87.414, 557.78
ref_epoch = 2016.0

object_name = "T4 2MASSI J2254188+312349"
ra, dec = 343.578834, 31.397175  # 2MASS
pmra, pmdec = 67, 187  # 2013A&A...560A..52M
ref_epoch = Time("1998-06-22").decimalyear  # 2MASS

object_name = "T3 2MASS J06560926+4205301"
ra, dec = 104.038623, 42.091709  # 2MASS
pmra, pmdec = 321.0, 155.5  # 2020AJ....159..257B
ref_epoch = Time("1998-11-05").decimalyear  # 2MASS
# selected_aperture_radius_pix=1.0
# psf_local_grid_half_range_pix=0.5

object_name = "T2 SDSSp J125453.90-012247.4"
ra, dec = 193.7223713, -1.3793373  # NSC DR2
pmra, pmdec = -514.451, 140.791  # NSC DR2
ref_epoch = Time("2016-05-08 04:33:26").decimalyear  # NSC DR2
# remove_outliers=False

object_name = "T1 2MASS J12462965-3139280"
ra, dec = 191.623491, -31.6604026
pmra, pmdec = -14.163, -562.188
ref_epoch = 2016.0

object_name = "T0 SDSS J120747.17+024424.8"
ra, dec = 181.9444058, 2.7407938  # NSC DR2
pmra, pmdec = -529.769, 108.917  # NSC DR2
ref_epoch = Time("2015-08-01 12:23:52").decimalyear  # NSC DR2
# selected_aperture_radius_pix=1.0
# keep_negative_flux=False

object_name = "L9 DENIS-P J0255-4700"
ra, dec = 43.7719859, -47.0167284
pmra, pmdec = 1012.445, -554.031
ref_epoch = 2016.0

object_name = "L8 2MASSW J1632291+190441"
ra, dec = 248.123048, 19.0776561  # NSC DR2
pmra, pmdec = 233.784, -58.5  # NSC DR2
ref_epoch = Time("2017-08-07 06:15:33").decimalyear  # NSC DR2
# selected_aperture_radius_pix=1.0

object_name = "L7 2MASSW J2148162+400359"
ra, dec = 327.0723955, 40.0685178
pmra, pmdec = 772.176, 458.243
ref_epoch = 2016.0

object_name = "L6 2MASSI J1010148-040649"
ra, dec = 152.561696, -4.11387  # 2MASS
pmra, pmdec = -324.2, -17.8  # 2020AJ....159..257B
ref_epoch = Time("1998-12-27").decimalyear  # 2MASS
# selected_aperture_radius_pix=1.0
# outlier_nbr_of_bins = 4

object_name = "L5 SDSS J083506.16+195304.4"
ra, dec = 128.775097, 19.884142  # NSC DR2
pmra, pmdec = -141.852, -142.771  # NSC DR2
ref_epoch = Time("2016-10-24 03:31:24").decimalyear  # NSC DR2
# selected_aperture_radius_pix=1.0
# outlier_nbr_of_bins = 4

object_name = "L4 2MASS J21580457-1550098"
ra, dec = 329.519261, -15.836336
pmra, pmdec = 45.951, -63.481
ref_epoch = 2016.0

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

# ------------------------------------------------------
# Test cases
# ------------------------------------------------------

object_name = "T2 SIMP J013656.5+093347.3"
ra, dec = 24.2412498, 9.5630705
pmra, pmdec = 1238.244, -16.156
ref_epoch = 2016.0

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
    remove_outliers=True,  # apply detector-wise wavelength-bin outlier rejection before final binning
    outlier_detectors=(1, 2, 3, 4, 5, 6),  # detectors to clean
    outlier_nbr_of_bins=outlier_nbr_of_bins,  # number of wavelength bins per detector

    keep_negative_flux=True,  # set True if you want to keep faint/noisy flux points

    # ============================================================
    # 4. SPECTRAL BINNING / OVERSAMPLING CONTROL
    # ============================================================
    reduce_oversampling=True,  # bin repeated SPHEREx measurements to reduce spectral oversampling

    remove_outliers_before_spectral_binning=True,  # remove outliers inside spectral-channel bins before combining them
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

    download_dir="../resources/objects/data",  # local cache directory
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
    output_dir="../resources/objects/spectra",
    plot_spectrum=True,

    # ============================================================
    # 8. OPTIONAL: PROPER MOTION / EPOCH PROPAGATION
    # ============================================================
    # Enable for high proper-motion objects
    reference_epoch_yr=ref_epoch,
    pmra_masyr=pmra,
    pmdec_masyr=pmdec,

    # ============================================================
    # 9. PLOTTING OPTIONS
    # ============================================================
    plot_spline=True,
    spline_density=1000,
    plot_color="k",
    plot_format="pdf",
    plot_flux_lambda=False,

)

run_spherex_pipeline(ra, dec, object_name=object_name, cfg=cfg)
