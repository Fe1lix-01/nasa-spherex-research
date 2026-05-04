import os
from collections import defaultdict

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.nddata import Cutout2D
from reproject import reproject_interp
from reproject.mosaicking import find_optimal_celestial_wcs

from .shared import create_object_name


def _crop_center(data, shape):
    y, x = data.shape
    cy, cx = shape
    sy = (y - cy) // 2
    sx = (x - cx) // 2
    return data[sy: sy + cy, sx: sx + cx]


def stack_images(ra, dec, data_dir, output_dir, object_name=None, image_size_arcsec=100, save_fits=False):
    # ----------------------------------------------------------
    # 1. Config
    # ----------------------------------------------------------
    aper_radius = 2.0  # aperture radius in pixels
    bg_in_radius = 4.0  # inner radius of background annulus
    bg_out_radius = 6.0  # outer radius of background annulus

    phot_radii = {
        "1": (aper_radius, bg_in_radius, bg_out_radius),
        "2": (aper_radius, bg_in_radius, bg_out_radius),
        "3": (aper_radius, bg_in_radius, bg_out_radius),
        "4": (aper_radius, bg_in_radius, bg_out_radius),
        "5": (aper_radius, bg_in_radius, bg_out_radius),
        "6": (aper_radius, bg_in_radius, bg_out_radius)
    }

    # ----------------------------------------------------------
    # 2. Group images by detector
    # ----------------------------------------------------------
    target = SkyCoord(ra, dec, unit="deg")
    detector_images = defaultdict(list)

    for file in os.listdir(data_dir):
        fits_path = os.path.join(data_dir, file)
        with fits.open(fits_path) as hdul:
            hdu = hdul["IMAGE"]
            detector = hdu.header["DETECTOR"]
            date_obs = hdu.header["DATE-OBS"]

            wcs, shape = find_optimal_celestial_wcs([hdu])
            image, _ = reproject_interp(hdu, wcs, shape_out=shape)
            image_cutout = Cutout2D(image, target, image_size_arcsec * u.arcsec, wcs=wcs, mode="partial")

            flags, _ = reproject_interp(hdul["FLAGS"], wcs, shape_out=shape)
            # FLAGS is an integer bitmask plane; in partial mode, padding must be an integer.
            # Using 0 means "no flags set" outside the footprint, which is appropriate for most bitmasks.
            flags_int = np.asarray(flags)
            if flags_int.dtype.kind not in ("i", "u", "b"):
                flags_int = flags_int.astype(np.uint32, copy=False)
            flags_cutout = Cutout2D(
                flags_int,
                target,
                image_size_arcsec * u.arcsec,
                wcs=wcs,
                mode="partial",
                fill_value=0,
            )

            zodi, _ = reproject_interp(hdul["ZODI"], wcs, shape_out=shape)
            zodi_cutout = Cutout2D(zodi, target, image_size_arcsec * u.arcsec, wcs=wcs, mode="partial")

            detector_images[detector].append(
                (date_obs, image_cutout.data - zodi_cutout.data, image_cutout.wcs.to_header(), flags_cutout.data)
            )

    # ----------------------------------------------------------
    # 3. Stack images and save per detector
    # ----------------------------------------------------------
    if not object_name:
        object_name = create_object_name(ra, dec, precision=2, shortform=False, prefix="J", decimal=False)

    cutouts = []

    for det, images in sorted(detector_images.items()):
        images = sorted(images, key=lambda x: x[0])  # sort by date_obs
        _, ref_data, ref_header, _ = images[0]  # reference cutout

        stacked = np.zeros_like(ref_data, dtype=float)
        count = np.zeros_like(ref_data, dtype=float)

        fatal_bits_ap = [0, 1, 2, 4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 17, 19, 22, 24, 26, 27, 28, 29]
        fatal_mask_ap = np.uint32(sum(1 << b for b in fatal_bits_ap))

        for _, data, _, flags in images[1:]:
            data = _crop_center(data, ref_data.shape)
            flags = _crop_center(flags, ref_data.shape)

            flags_u = np.asarray(flags)
            if flags_u.dtype.kind not in ("i", "u", "b"):
                flags_u = flags_u.astype(np.uint32, copy=False)

            good_flags = (flags_u & fatal_mask_ap) == 0
            good_data = np.isfinite(data)
            valid_mask = good_flags & good_data

            stacked[valid_mask] += data[valid_mask]
            count[valid_mask] += 1

        mean_image = stacked / np.maximum(count, 1)

        # Create FITS
        hdu = fits.PrimaryHDU(mean_image, header=ref_header)

        if save_fits:
            hdu.writeto(
                os.path.join(output_dir, object_name + f"_D{det}_{image_size_arcsec}_arcsec_cutout.fits"),
                overwrite=True
            )
            print(f"Saved stacked cutout for detector {det}")

        cutouts.append({"hdu": hdu, "band": f"D{det}", "phot_radii": phot_radii[f"{det}"]})

    return cutouts
