import os
import tempfile
import warnings

import PIL.ImageOps
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from astropy.utils.exceptions import AstropyWarning
from astropy.visualization import make_lupton_rgb
from astropy.wcs import WCS
from matplotlib.patches import BoxStyle, Rectangle, Circle

from .shared import create_object_name, open_file


def plot_images(
    ra, dec, images, image_size, image_contrast=10, object_name=None,
    output_dir=tempfile.gettempdir(), save_plot=False, open_plot=True, plot_format="png"
):
    """
    Generate and save a grid of astronomical images, including individual band images and a combined RGB image.

    Parameters:
        ra (float): Right ascension of the object in degrees.
        dec (float): Declination of the object in degrees.
        images (list): List of dictionaries containing image data. Each dictionary should have:
            - 'hdu': FITS HDU object containing image data and header.
            - 'band': String representing the band name (e.g., 'r', 'g', 'b').
            - 'rgb': String indicating the RGB channel ('r', 'g', or 'b').
        image_size (float): Size of the image in arcseconds.
        aper_radius (float, optional): Radius of the circular aperture in pixels. Default is 2.0.
        image_contrast (int, optional): Contrast adjustment for the images. Default is 10.
        output_dir (str, optional): Directory to save the output image. Default is the system's temporary directory.
        open_plot (bool, optional): Whether to open the saved plot after creation. Default is True.
        plot_format (str, optional): Format of the saved plot (e.g., 'png', 'jpg'). Default is 'png'.

    Returns:
        None
    """

    def create_image(hdu, img_idx, band, phot_radii):
        """
        Create and plot a single-band image.

        Parameters:
            hdu: FITS HDU object containing image data and header.
            img_idx (int): Index of the subplot in the grid.
            band (str): Name of the band (e.g., 'r', 'g', 'b').

        Returns:
            tuple: Processed image data, x-coordinate of the center, y-coordinate of the center.
        """
        wcs = WCS(hdu.header)
        data = hdu.data

        ax = fig.add_subplot(rows, cols, img_idx, projection=wcs)

        x, y = data.shape
        x /= 2
        y /= 2

        plt.scatter(x, y, s=0.2, c='red')

        # Draw aperture and background circles in a loop to reduce repetition
        aper_radius, bg_in_radius, bg_out_radius = phot_radii
        for radius, color in [
            (aper_radius, "red"),
            (bg_in_radius, "blue"),
            (bg_out_radius, "blue"),
        ]:
            circle = Circle((x, y), radius=radius, edgecolor=color, facecolor="none", lw=0.5)
            ax.add_patch(circle)

        ax.text(
            0.03,
            0.93,
            band,
            color="black",
            fontsize=3.0,
            transform=ax.transAxes,
            bbox={"facecolor": "white", "alpha": 0.5, "linewidth": 0.1, "boxstyle": BoxStyle("Square", pad=0.3)},
        )
        ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, lw=0.2, ec="black", transform=ax.transAxes))

        vmin, vmax = get_min_max(data)
        ax.imshow(data, vmin=vmin, vmax=vmax, cmap="gray_r")
        ax.axis("off")

        return data, x, y

    def create_color_image(r, g, b, img_idx, band, invert=False):
        """
        Create and plot an RGB color image.

        Parameters:
            r, g, b: 2D numpy arrays representing the red, green, and blue channels.
            img_idx (int): Index of the subplot in the grid.
            band (str): Combined band name (e.g., 'r-g-b').
            x, y (float): Coordinates of the center.
            invert (bool, optional): Whether to invert the colors. Default is False.

        Returns:
            None
        """
        dims = [channel.shape for channel in [r, g, b]]
        ymin, xmin = map(min, zip(*dims))

        r = Image.fromarray(get_rgb(crop_center(r, (xmin, ymin)))).convert("L")
        g = Image.fromarray(get_rgb(crop_center(g, (xmin, ymin)))).convert("L")
        b = Image.fromarray(get_rgb(crop_center(b, (xmin, ymin)))).convert("L")

        if invert:
            r = PIL.ImageOps.invert(r)
            g = PIL.ImageOps.invert(g)
            b = PIL.ImageOps.invert(b)

        rgb = Image.merge("RGB", (r, g, b))

        ax = fig.add_subplot(rows, cols, img_idx)

        ax.text(
            0.03,
            0.93,
            band,
            color="black",
            fontsize=3.0,
            transform=ax.transAxes,
            bbox={"facecolor": "white", "alpha": 0.7, "linewidth": 0.1, "boxstyle": BoxStyle("Square", pad=0.3)},
        )
        ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, lw=0.2, ec="black", transform=ax.transAxes))

        ax.imshow(rgb, origin="lower")
        ax.axis("off")

    def crop_center(data, shape):
        """
        Crop the center of the image to the specified shape.

        Parameters:
            data (numpy.ndarray): Input image data.
            shape (tuple): Desired shape (height, width).

        Returns:
            numpy.ndarray: Cropped image data.
        """
        y, x = data.shape
        cy, cx = shape
        sy = (y - cy) // 2
        sx = (x - cx) // 2
        return data[sy: sy + cy, sx: sx + cx]

    def get_rgb(data):
        """
        Generate an RGB representation of the image data.

        Parameters:
            data (numpy.ndarray): Input image data.

        Returns:
            numpy.ndarray: RGB image data.
        """
        vmin, vmax = get_min_max(data)
        return make_lupton_rgb(data, data, data, minimum=vmin, stretch=vmax - vmin, Q=0)

    def get_min_max(data):
        """
        Calculate the minimum and maximum values for image scaling.

        Parameters:
            data (numpy.ndarray): Input image data.

        Returns:
            tuple: Minimum and maximum values for scaling.
        """
        lo = image_contrast
        hi = 100 - image_contrast
        med = np.nanmedian(data)
        mad = np.nanmedian(abs(data - med))
        dev = np.nanpercentile(data, hi) - np.nanpercentile(data, lo)
        vmin = med - 2.0 * mad
        vmax = med + 2.0 * dev
        return vmin, vmax

    warnings.simplefilter("ignore", category=AstropyWarning)

    img_idx = 1
    fontsize = 4.5
    rows, cols = 5, 6

    fig = plt.figure()
    fig.set_figheight(5)
    fig.set_figwidth(5)
    plt.subplots_adjust(wspace=0, hspace=0.1, right=1.0)
    plt.rcParams.update({"font.family": "Arial"})

    image_data = {}

    for image in images:
        hdu = image["hdu"]
        band = image["band"]
        phot_radii = image["phot_radii"]

        print(f"Creating {band}-band image")
        data, _, _ = create_image(hdu, img_idx, band, phot_radii)

        image_data[band] = data
        img_idx += 1

    # Define band pairs and their combined names
    band_pairs = [("D1", "D2", "D12"), ("D3", "D4", "D34"), ("D5", "D6", "D56")]
    combined_data = {}

    for b1, b2, cname in band_pairs:
        combined_data[cname] = (image_data[b1] + image_data[b2]) / 2

    b_data = combined_data["D12"]
    b_band = "D12"

    g_data = combined_data["D34"]
    g_band = "D34"

    r_data = combined_data["D56"]
    r_band = "D56"

    print("Creating color image")
    create_color_image(r_data, g_data, b_data, img_idx, f"{r_band}-{g_band}-{b_band}")
    img_idx += 1

    target_name = create_object_name(ra, dec, precision=2, shortform=False, prefix="J", decimal=False)
    source_name = object_name if object_name else target_name
    filename = os.path.join(output_dir, object_name + "_images." + plot_format)

    ax = fig.add_subplot(rows, cols, img_idx)
    ax.text(0.1, 0.80, source_name, fontsize=fontsize, transform=ax.transAxes)
    ax.text(0.1, 0.65, r"$\alpha$ = " + str(round(ra, 7)), fontsize=fontsize, transform=ax.transAxes)
    ax.text(0.1, 0.50, r"$\delta$ = " + str(round(dec, 7)), fontsize=fontsize, transform=ax.transAxes)
    ax.text(0.1, 0.35, "Size = " + str(int(image_size)) + " arcsec", fontsize=fontsize, transform=ax.transAxes)
    ax.text(0.1, 0.20, "North up, East left", fontsize=fontsize, transform=ax.transAxes)
    ax.axis("off")
    img_idx += 1

    if save_plot:
        plt.savefig(filename, dpi=600, bbox_inches="tight", format=plot_format)

    plt.close()

    if open_plot:
        open_file(filename)
