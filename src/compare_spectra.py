import os
import warnings

import astropy.units as u
from astropy.io import fits

from spexpi.spectrum_comparator import Spectrum, SpectrumTemplateComparator
from spexpi.spectrum_plotter import create_comparison_plot


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


warnings.simplefilter('ignore', category=Warning)

# Spectral units
wl_unit = u.um
flux_unit = u.Jy

# Load template spectra
data_dir = "../resources/standards/sequence/psf"
fits_files = sorted(f for f in os.listdir(data_dir) if f.endswith(".fits"))

templates = []
for i, filename in enumerate(fits_files):
    full_path = os.path.join(data_dir, filename)
    wavelength, flux, flux_error = extract_spectrum_from_fits(full_path)

    wavelength *= wl_unit
    flux *= flux_unit
    flux_error *= flux_unit

    spt = filename.split()[0].replace("_", "")

    template = Spectrum(
        wavelength=wavelength,
        flux=flux,
        uncertainty=flux_error,
        label=spt,
        model_params={"spt": spt}
    )

    templates.append(template)

# Load observed spectrum
object_name = "T2 SIMP J013656.5+093347.3"
fits_path = "../resources/objects/fits/T2 SIMP J013656.5+093347.3_psf_spectrum.fits"

plot_observed_error = True
plot_template_error = False
plot_format = "pdf"
output_dir = "../resources/objects/plots"

wavelength, flux, flux_error = extract_spectrum_from_fits(fits_path)

wavelength *= wl_unit
flux *= flux_unit
flux_error *= flux_unit

observed = Spectrum(
    label=object_name,
    wavelength=wavelength,
    flux=flux,
    uncertainty=flux_error
)

comparator = SpectrumTemplateComparator()
result = comparator.compare(
    observed,
    templates,
    trim_wave=True,
    number_of_matches=3,
    metric="reduced-chi2",
    normalize=True,
    scaling_mode="least-squares",
)

create_comparison_plot(
    result,
    plot_observed_error=plot_observed_error,
    plot_template_error=plot_template_error,
    object_name=object_name,
    output_dir=output_dir,
    plot_format=plot_format,
)
