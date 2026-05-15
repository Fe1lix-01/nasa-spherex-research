"""
Plotting utilities for spectral comparison results.

Primary entry point:
    create_spectrum_figure(comparison_result, object_name, output_dir, ...)

Expected input:
    comparison_result from SpectrumTemplateComparator.compare(...)
"""

import os
from pathlib import Path

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import PchipInterpolator


def open_file(filename):
    import os
    import subprocess
    import sys

    try:
        if sys.platform.startswith("win"):
            os.startfile(filename)
        elif sys.platform == "darwin":
            subprocess.call(["open", filename])
        else:
            subprocess.call(["xdg-open", filename])
    except Exception:
        pass


def to_latex(unit):
    return unit.to_string("latex_inline")


def jy_to_flambda(wavelength_um, flux_jy):
    wavelength = np.asarray(wavelength_um, dtype=float) * u.um
    flux = np.asarray(flux_jy, dtype=float) * u.Jy
    return flux.to(u.erg / u.s / u.cm ** 2 / u.um, equivalencies=u.spectral_density(wavelength)).value


def plot_curves(ax, wl, flux, err, color, plot_error=True, zorder=0, marker_size=5, line_width=1.0):
    wl = np.asarray(wl, dtype=float)
    flux = np.asarray(flux, dtype=float)
    err = np.asarray(err, dtype=float)

    valid = np.isfinite(wl) & np.isfinite(flux)
    if valid.sum() < 2:
        return

    wl = wl[valid]
    flux = flux[valid]
    err = err[valid] if len(err) == len(valid) else np.full_like(flux, np.nan)

    order = np.argsort(wl)
    wl = wl[order]
    flux = flux[order]
    err = err[order]

    if len(wl) >= 3 and np.all(np.diff(wl) > 0):
        wl_dense = np.linspace(wl.min(), wl.max(), 1000)
        interp = PchipInterpolator(wl, flux)
        flux_dense = interp(wl_dense)
        ax.plot(wl_dense, flux_dense, lw=line_width, c=color, alpha=0.4, zorder=zorder)
    else:
        ax.plot(wl, flux, lw=line_width, c=color, alpha=0.4, zorder=zorder)

    if plot_error and np.isfinite(err).any():
        ax.errorbar(
            wl,
            flux,
            yerr=err,
            fmt="o",
            ms=marker_size,
            color=color,
            capsize=0,
            elinewidth=0.8,
            markeredgewidth=0.8,
            markerfacecolor="white",
            zorder=zorder
        )
    else:
        ax.scatter(wl, flux, s=marker_size * 2, edgecolor=color, zorder=zorder, linewidth=0.8,
                   facecolor="white", )


def format_stat_label(metric, statistic):
    if metric == "reduced-chi2":
        return rf"$\chi_\nu^2$ = {statistic:.3f}"
    return f"{metric} = {statistic:.3f}"


def create_comparison_plot(
    comparison_result,
    object_name,
    output_dir,
    plot_format="pdf",
    plot_observed_error=True,
    plot_template_error=False,
    offset_step=1.0,
    template_color="tab:red",
    observed_color="black",
    open_plot=True,
    title_prefix="Comparison",
    max_matches=3,
    label_x=4.3,
    label_y_offset=-0.15,
    figure_size=(10, 8),
    dpi=300,
    xlabel=f"Wavelength ({to_latex(u.um)})",
    ylabel=r"F$_{\lambda}$ + offset",
    show_grid=True,
):
    """
    Create an offset comparison plot from a comparison_result.

    Parameters
    ----------
    comparison_result
        Result object returned by SpectrumTemplateComparator.compare(...).
    object_name : str
        Name used in title and output filename.
    output_dir : str
        Output directory for the plot file.
    plot_format : str, default="pdf"
        Output format, e.g. "pdf" or "png".
    plot_observed_error : bool, default=True
        Whether to plot observed error bars.
    plot_template_error : bool, default=False
        Whether to plot template error bars.
    offset_step : float, default=1.0
        Vertical offset between successive matches.
    template_color : str, default="tab:red"
        Template curve color.
    observed_color : str, default="black"
        Observed spectrum color.
    open_plot : bool, default=True
        Whether to try opening the plot after saving.
    title_prefix : str, default="SPHEREx Comparison"
        Title prefix before object name.
    max_matches : int, default=3
        Number of top matches to plot.
    label_x : float, default=4.3
        X position for right-side match labels.
    label_y_offset : float, default=-0.15
        Vertical offset applied to label anchor.
    figure_size : tuple, default=(10, 8)
        Matplotlib figure size.
    dpi : int, default=300
        Save DPI.
    ylabel : str, default=r"F$_{\\lambda}$ + offset"
        Y-axis label.
    show_grid : bool, default=True
        Whether to show a background grid.

    Returns
    -------
    str
        Saved filename.
    """
    plt.figure(figsize=figure_size)
    plt.rcParams.update({
        "font.size": 14,
        "font.family": "Arial",
        "axes.formatter.limits": [-0, 0],
        "text.usetex": False,
        "mathtext.fontset": "custom",
        "mathtext.rm": "Arial"
    })
    ax = plt.gca()

    spectrum = comparison_result.observed
    matches = comparison_result.best_matches[:max_matches]

    if not matches:
        raise ValueError("comparison_result.best_matches is empty")

    obs_wl = spectrum.wavelength
    obs_flux = jy_to_flambda(obs_wl, spectrum.flux)
    obs_err = jy_to_flambda(obs_wl, spectrum.uncertainty)
    norm = np.nanmax(obs_flux)
    if not np.isfinite(norm) or norm == 0:
        norm = 1.0

    for i, match in enumerate(matches):
        flux = obs_flux / norm
        flux = flux + i * offset_step
        error = obs_err / norm
        plot_curves(
            ax,
            obs_wl,
            flux,
            error,
            observed_color,
            plot_observed_error,
            zorder=1
        )

        template = match.template_scaled
        tpl_flux = jy_to_flambda(template.wavelength, template.flux)
        tpl_err = jy_to_flambda(template.wavelength, template.uncertainty) / norm
        tpl_flux = tpl_flux / norm + i * offset_step

        plot_curves(
            ax,
            template.wavelength,
            tpl_flux,
            tpl_err,
            template_color,
            plot_template_error,
            zorder=2
        )

        stat_label = format_stat_label(match.metric, match.statistic)
        ax.text(
            label_x,
            tpl_flux[-1] + label_y_offset,
            f"{template.label}  {stat_label}",
            color=template_color,
            fontsize=12,
            va="center"
        )

    filename = os.path.join(output_dir, object_name + "_comparison." + plot_format)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(f"{title_prefix} {object_name} vs. Standards", size=14)

    if show_grid:
        ax.grid(color='silver', linestyle='-', linewidth=0.5, alpha=0.5)

    plt.savefig(filename, dpi=dpi, bbox_inches="tight", format=plot_format)
    plt.close()

    if open_plot:
        open_file(filename)

    return filename
