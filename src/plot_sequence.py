import os
import warnings

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from astropy.table import Table
from matplotlib.patches import Rectangle
from scipy.interpolate import PchipInterpolator


def extract_spectrum_from_fits(fits_file_path):
    try:
        with fits.open(fits_file_path) as hdul:
            data = hdul[1].data
            wavelength = data["WAVELENGTH"]
            flux = data["FLUX"]
            error = data["ERR"]
            return wavelength, flux, error
    except Exception as e:
        print(f"Error reading {fits_file_path}: {e}")
        return None, None, None


def flux_to_flux_lambda(wavelength, flux, density_unit=u.AA):
    return flux.to(u.erg / u.s / u.cm ** 2 / density_unit, equivalencies=u.spectral_density(wavelength))


def get_standards(data_dir):
    fits_files = sorted(f for f in os.listdir(data_dir) if f.endswith(".fits"))

    spectra = []

    for i, filename in enumerate(fits_files):
        full_path = os.path.join(data_dir, filename)
        wavelength, flux, error = extract_spectrum_from_fits(full_path)
        spectra.append(
            {
                "SpT": filename.split()[0].replace("_", ""),
                "Wavelength": np.array(wavelength, dtype=float),
                "Flux": np.array(flux, dtype=float),
                "Error": np.array(error, dtype=float),
            }
        )

    return Table(rows=spectra)


def plot_group(ax, standards, color=None, plot_spt=True):
    row_i = 0

    cmap = plt.get_cmap("tab10")
    n_curves = len(standards)
    colors = cmap(np.linspace(0, 1, n_curves))

    for standard in standards:
        wavelength = np.asarray(standard["Wavelength"], dtype=float)
        flux = np.asarray(standard["Flux"], dtype=float)
        error = np.asarray(standard["Error"], dtype=float)

        if flux_type == "F_lambda":
            wavelength *= u.um
            flux *= u.Jy
            error *= u.Jy

            flux = flux_to_flux_lambda(wavelength, flux)
            error = flux_to_flux_lambda(wavelength, error)

            wavelength = wavelength.value
            flux = flux.value
            error = error.value

        """
        # Robust normalization near the J-band peak.
        # This avoids using a single noisy maximum value to scale the spectrum.
        norm_region = (wavelength > 1.20) & (wavelength < 1.35)
        finite_region = norm_region & np.isfinite(flux) & (flux > 0)

        if np.count_nonzero(finite_region) >= 2:
            norm = np.nanmedian(flux[finite_region])
        else:
            finite_flux = np.isfinite(flux) & (flux > 0)
            norm = np.nanpercentile(flux[finite_flux], 95) if np.any(finite_flux) else np.nan

        if not np.isfinite(norm) or norm <= 0:
            continue
        """

        norm = np.nanmax(flux)

        flux = flux / norm
        flux = flux + row_i * offset_step
        error = error / norm

        if row_i == 0:
            min_y = np.min(flux)

        if row_i == len(standards) - 1:
            max_y = np.max(flux)

        plot_curves(ax, wavelength, flux, np.abs(error), colors[row_i] if color is None else color)

        if plot_spt:
            ax.text(
                5.05,
                flux[-1],
                standard["SpT"],
                fontsize=18,
                va="center",
            )

        row_i += 1

    return min_y, max_y


def plot_curves(ax, wl, flux, err, color):
    wl_dense = np.linspace(wl.min(), wl.max(), 1000)
    interp = PchipInterpolator(wl, flux)
    flux_dense = interp(wl_dense)

    ax.plot(wl_dense, flux_dense, lw=1.0, c=color, alpha=0.4, zorder=1)
    ax.errorbar(
        wl,
        flux,
        yerr=err,
        fmt="o",
        ms=5,
        color=color,
        capsize=0,
        elinewidth=0.8,
        markeredgewidth=0.8,
        markerfacecolor="white",
        zorder=2,
        label="Flux"
    )


def add_standard_reference_box(ax, text, title=None):
    """Add a compact reference textbox below an axes.

    The position uses axes coordinates so the box stays attached to the
    corresponding panel even if the figure size or data limits change.
    """
    box_text = f"{title}\n{text}" if title else text
    ax.text(
        0.5,
        -0.05,
        box_text,
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=16,
        linespacing=2.0,
        multialignment="left",
        bbox={
            "boxstyle": "square,pad=0.45",
            "facecolor": "white",
            "edgecolor": "0.35",
            "linewidth": 0.8,
            "alpha": 0.95,
        },
        clip_on=False,
    )


def shade_absorption_features(
    ax,
    dwarf_type="T",
    alpha=0.16,
    zorder=0,
    label_top=0.985,
    label_step=0.035,
):
    dtype = dwarf_type.strip().lower()

    l_features = [
        (1.10, 1.20, r"H$_2$O", 0),
        (1.30, 1.50, r"H$_2$O", 0.5),
        (1.75, 2.00, r"H$_2$O", 0),
        (1.80, 2.30, r"H$_2$-H$_2$", 0.5),
        (2.30, 2.50, r"H$_2$O", 0),
        (2.51, 3.20, r"H$_2$O", 0.5),
        (3.00, 3.80, r"CH$_4$", 0),
        # (4.00, 4.45, r"CO$_2$", 0),
        (4.45, 5.00, r"CO", 0),
    ]

    t_features = [
        (1.10, 1.23, r"H$_2$O+CH$_4$", 0),
        (1.30, 1.51, r"H$_2$O", 0.5),
        (1.60, 1.80, r"CH$_4$", 0),
        (1.75, 2.05, r"H$_2$O", 0.5),
        (2.15, 2.50, r"H$_2$O+CH$_4$", 0),
        (2.51, 3.20, r"H$_2$O", 0.5),
        (3.00, 3.80, r"CH$_4$", 0),
        (4.20, 4.40, r"CO$_2$", 0),
        (4.45, 5.00, r"CO", 0),
    ]

    if dtype == "l":
        features = l_features
    elif dtype == "t":
        features = t_features
    else:
        raise ValueError("dwarf_type must be either 'L' or 'T'.")

    feature_colors = {
        r"H$_2$O": "tab:blue",
        r"CH$_4$": "tab:orange",
        r"H$_2$O+CH$_4$": "tab:cyan",
        r"H$_2$-H$_2$": "tab:brown",
        r"CO$_2$": "tab:red",
        r"CO": "tab:green",
    }

    seen_labels = set()

    for x0, x1, label, offset in features:
        color = feature_colors[label]
        legend_label = label if label not in seen_labels else None
        seen_labels.add(label)

        ax.axvspan(
            x0,
            x1,
            color=color,
            alpha=alpha,
            zorder=zorder,
            label=legend_label,
        )

        ax.text(
            0.5 * (x0 + x1),
            label_top - offset * label_step,
            label,
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=14,
            color=color,
            zorder=zorder + 1,
            bbox={
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.75,
                "pad": 1.0,
            },
        )

    return ax


warnings.simplefilter("ignore")

flux_type = "F_nu"  # "F_lambda" or "F_nu"
color_aperture = "k"
color_psf = "tab:red"
plot_features = False
offset_step = 0.9  # vertical spacing between spectra

L_STANDARD_REFERENCES = """L0 : 2MASP J0345432+254023  –  J. D. Kirkpatrick et al. (1999)
L1 : 2MASSW J1439284+192915 – J. D. Kirkpatrick et al. (1999)
L2 : Kelu-1 – J. D. Kirkpatrick et al. (1999)
L3 : 2MASSW J1506544+132106 – J. E. Gizis et al. (2000)
L4 : 2MASS J21580457-1550098 – J. D. Kirkpatrick et al. (2008)
L5 : SDSS J083506.16+195304.4 – K. Chiu et al. (2006)
L6 : 2MASSI J1010148-040649 – K. L. Cruz et al. (2003)
L7 : 2MASSW J2148162+400359 – A. C. Schneider et al. (2014)
L8 : 2MASSW J1632291+190441 – J. D. Kirkpatrick et al. (1999)
L9 : DENIS-P J0255-4700 – J. D. Kirkpatrick et al. (2008)"""

T_STANDARD_REFERENCES = """T0 : SDSS J120747.17+024424.8 – S. L. Hawley et al. (2002)
T1 : 2MASS J12462965-3139280 – G. N. Mace et al. (2013)
T2 : SDSSp J125453.90-012247.4 – A. J. Burgasser et al. (2006)
T3 : 2MASS J06560926+4205301 – R. L. Griffith et al. (2012)
T4 : 2MASSI J2254188+312349 – A. J. Burgasser et al. (2006)
T5 : 2MASS J15031961+2525196 – A. J. Burgasser et al. (2006)
T6 : 2MASS J15065257+7027247 – R. L. Griffith et al. (2012)
T7 : 2MASSI J0727182+171001 – A. J. Burgasser et al. (2006)
T8 : 2MASSI J0415195-093506 – A. J. Burgasser et al. (2006)
T9 : WISEP J174124.25+255319.5 – R. L. Griffith et al. (2012)"""

standards_aperture = get_standards("../resources/standards/sequence/aperture")
L_standards_aperture = [s for s in standards_aperture if s["SpT"].startswith("L")]
T_standards_aperture = [s for s in standards_aperture if s["SpT"].startswith("T")]

standards_psf = get_standards("../resources/standards/sequence/psf")
L_standards_psf = [s for s in standards_psf if s["SpT"].startswith("L")]
T_standards_psf = [s for s in standards_psf if s["SpT"].startswith("T")]

# -----------------------------
# Plot configuration
# -----------------------------
plt.rcParams.update({
    "font.size": 20,
    "font.family": "Arial",
    "axes.formatter.limits": [-0, 0],  # Always use scientific notation
    "text.usetex": False,
    "mathtext.fontset": "custom",
    "mathtext.rm": "Arial"
})

fig, axes = plt.subplots(1, 2, figsize=(20, 25), sharey=True)
ax_L, ax_T = axes

plot_group(ax_L, L_standards_aperture, color_aperture)
plot_group(ax_T, T_standards_aperture, color_aperture)

plot_group(ax_L, L_standards_psf, color_psf, plot_spt=False)
min_y, max_y = plot_group(ax_T, T_standards_psf, color_psf, plot_spt=False)

fig.suptitle("SPHEREx Aperture (black) vs. PSF (red) photometry", fontsize=26)

ax_L.set_title("L dwarfs")
ax_T.set_title("T dwarfs")

# -----------------------------
# Final plot styling
# -----------------------------
for ax in axes:
    ax.set_xlim(0.75, 5.0)
    ax.tick_params(axis='x', labelsize=18)
    ax.set_yticks([])
    ax.grid(alpha=0.2)
    ax.set_xlabel(r"Wavelength ($\mathrm{\mu}$m)", fontsize=20)

mean_y = (min_y + max_y / 2)
margin = mean_y * 0.05

y_label = r"F$_{\mathrm{\lambda}}$ + offset" if flux_type == "F_lambda" else "Flux + offset"

ax_L.set_ylim(min_y - margin, max_y + margin)
ax_L.set_ylabel(y_label, fontsize=20)

if plot_features:
    shade_absorption_features(ax_L, dwarf_type="L")
    shade_absorption_features(ax_T, dwarf_type="T")

# Reference boxes below each sequence plot.
add_standard_reference_box(ax_L, L_STANDARD_REFERENCES)
add_standard_reference_box(ax_T, T_STANDARD_REFERENCES)

file_name = f"standards_{flux_type}.pdf"

# Add invisible rectangle below figure to force bottom padding
fig.add_artist(Rectangle(
    (0, -0.01),  # (x, y) in figure coordinates → y < 0 pushes bottom margin
    1, 0.1,  # width, height
    transform=fig.transFigure,
    facecolor="none",
    edgecolor="none"
))

plt.tight_layout()
plt.savefig("../resources/standards/sequence/" + file_name, dpi=300, bbox_inches="tight")
plt.close()
