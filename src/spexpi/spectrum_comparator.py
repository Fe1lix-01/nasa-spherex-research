"""
Spectral template comparison utilities.

Designed for continuous spectra such as SPHEREx, Euclid, SpeX, etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


@dataclass
class Spectrum:
    wavelength: np.ndarray
    flux: np.ndarray
    uncertainty: Optional[np.ndarray] = None
    label: str = ""
    metadata: Dict = field(default_factory=dict)
    model_params: Optional[Dict] = None

    def __post_init__(self) -> None:
        self.wavelength = np.asarray(self.wavelength, dtype=float)
        self.flux = np.asarray(self.flux, dtype=float)
        if self.uncertainty is None:
            self.uncertainty = np.full_like(self.flux, np.nan, dtype=float)
        else:
            self.uncertainty = np.asarray(self.uncertainty, dtype=float)

        if not (len(self.wavelength) == len(self.flux) == len(self.uncertainty)):
            raise ValueError("wavelength, flux and uncertainty must have the same length")

    def copy(self) -> "Spectrum":
        return Spectrum(
            wavelength=self.wavelength.copy(),
            flux=self.flux.copy(),
            uncertainty=self.uncertainty.copy(),
            label=self.label,
            metadata=dict(self.metadata),
            model_params=None if self.model_params is None else dict(self.model_params),
        )

    def sort_by_wavelength(self) -> "Spectrum":
        order = np.argsort(self.wavelength)
        self.wavelength = self.wavelength[order]
        self.flux = self.flux[order]
        self.uncertainty = self.uncertainty[order]
        return self

    def trim(self, min_wave: Optional[float] = None, max_wave: Optional[float] = None) -> "Spectrum":
        if len(self.wavelength) == 0:
            return self
        if min_wave is None:
            min_wave = np.nanmin(self.wavelength)
        if max_wave is None:
            max_wave = np.nanmax(self.wavelength)
        w, f = trim_arrays(self.wavelength, self.flux, min_wave, max_wave)
        _, e = trim_arrays(self.wavelength, self.uncertainty, min_wave, max_wave)
        self.wavelength, self.flux, self.uncertainty = w, f, e
        return self


@dataclass
class MatchResult:
    statistic: float
    metric: str
    observed: Spectrum
    template_original: Spectrum
    template_scaled: Spectrum
    scale_factor: float
    offset: float


@dataclass
class ComparisonResult:
    observed: Spectrum
    best_matches: List[MatchResult]
    metric: str
    scaling_mode: str
    all_results: List[MatchResult] = field(default_factory=list)

    @property
    def best_match(self) -> Optional[MatchResult]:
        return self.best_matches[0] if self.best_matches else None


def determine_overlapping_wavelength_range(
    wavelength_a: Sequence[float], wavelength_b: Sequence[float]
) -> Tuple[float, float]:
    min_wave = max(np.nanmin(wavelength_a), np.nanmin(wavelength_b))
    max_wave = min(np.nanmax(wavelength_a), np.nanmax(wavelength_b))
    if not np.isfinite(min_wave) or not np.isfinite(max_wave) or min_wave >= max_wave:
        raise ValueError("No overlapping wavelength range between reference and template")
    return float(min_wave), float(max_wave)


def trim_arrays(
    wavelength: Sequence[float],
    values: Sequence[float],
    min_wave: float,
    max_wave: float,
) -> Tuple[np.ndarray, np.ndarray]:
    wavelength = np.asarray(wavelength, dtype=float)
    values = np.asarray(values, dtype=float)
    mask = np.isfinite(wavelength) & (wavelength >= min_wave) & (wavelength <= max_wave)
    return wavelength[mask], values[mask]


def _filter_finite_triplets(
    wavelength: np.ndarray,
    flux: np.ndarray,
    uncertainty: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    mask = np.isfinite(wavelength) & np.isfinite(flux)
    if uncertainty is not None:
        mask &= np.isfinite(uncertainty)
    return wavelength[mask], flux[mask], uncertainty[mask]


def _sanitize_for_scoring(
    ref_flux: np.ndarray,
    ref_uncertainty: np.ndarray,
    tpl_flux: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    mask = np.isfinite(ref_flux) & np.isfinite(tpl_flux)
    if ref_uncertainty is not None:
        mask &= np.isfinite(ref_uncertainty)
    ref_flux = ref_flux[mask]
    tpl_flux = tpl_flux[mask]
    if ref_uncertainty is None:
        ref_uncertainty = np.full_like(ref_flux, np.nan, dtype=float)
    else:
        ref_uncertainty = ref_uncertainty[mask]
    return ref_flux, ref_uncertainty, tpl_flux


class SpectrumTemplateComparator:
    """
    Compare an observed spectrum to template spectra.

    The template is interpolated onto the observed wavelength grid over the
    overlapping wavelength range, then scaled to the observed spectrum before
    evaluating a fit statistic.
    """

    def compare(
        self,
        reference: Spectrum,
        templates: List[Spectrum],
        number_of_matches: int = 1,
        metric: str = "reduced-chi2",
        trim_wave: bool = False,
        verbose: bool = False,
        normalize: bool = True,
        scaling_mode: str = "least-squares",
    ) -> ComparisonResult:
        if len(reference.flux) == 0:
            raise ValueError("Reference flux array is empty")

        reference_prepared = reference.copy().sort_by_wavelength()
        results: List[MatchResult] = []

        for template_in in templates:
            reference_work = reference_prepared.copy()
            template_original = template_in.copy().sort_by_wavelength()
            template_work = template_original.copy()

            if trim_wave:
                min_wave, max_wave = determine_overlapping_wavelength_range(
                    reference_work.wavelength, template_work.wavelength
                )
                reference_work.trim(min_wave, max_wave)
                template_work.trim(min_wave, max_wave)

            ref_wl, ref_flux, ref_unc = _filter_finite_triplets(
                reference_work.wavelength,
                reference_work.flux,
                reference_work.uncertainty,
            )
            tpl_wl, tpl_flux, tpl_unc = _filter_finite_triplets(
                template_work.wavelength,
                template_work.flux,
                template_work.uncertainty,
            )

            if len(ref_wl) < 2 or len(tpl_wl) < 2:
                continue

            try:
                min_wave, max_wave = determine_overlapping_wavelength_range(ref_wl, tpl_wl)
            except ValueError:
                continue

            ref_wl, ref_flux = trim_arrays(ref_wl, ref_flux, min_wave, max_wave)
            _, ref_unc = trim_arrays(ref_wl, ref_unc, min_wave, max_wave)
            tpl_wl, tpl_flux = trim_arrays(tpl_wl, tpl_flux, min_wave, max_wave)
            _, tpl_unc = trim_arrays(tpl_wl, tpl_unc, min_wave, max_wave)

            if len(ref_wl) < 2 or len(tpl_wl) < 2:
                continue

            tpl_flux_interp = np.interp(ref_wl, tpl_wl, tpl_flux)
            tpl_unc_interp = np.interp(ref_wl, tpl_wl, tpl_unc) if np.isfinite(tpl_unc).any() else np.full_like(ref_wl, np.nan)

            if normalize:
                tpl_flux_scaled, tpl_unc_scaled, scale_factor, offset = self._scale_template(
                    ref_flux=ref_flux,
                    ref_uncertainty=ref_unc,
                    tpl_flux=tpl_flux_interp,
                    tpl_uncertainty=tpl_unc_interp,
                    scaling_mode=scaling_mode,
                )
            else:
                tpl_flux_scaled = tpl_flux_interp.copy()
                tpl_unc_scaled = tpl_unc_interp.copy()
                scale_factor = 1.0
                offset = 0.0

            score_ref_flux, score_ref_unc, score_tpl_flux = _sanitize_for_scoring(
                ref_flux, ref_unc, tpl_flux_scaled
            )
            if len(score_ref_flux) < 2:
                continue

            statistic = self.compare_fluxes(
                score_ref_flux,
                score_ref_unc,
                score_tpl_flux,
                metric,
            )

            observed_out = Spectrum(
                wavelength=ref_wl,
                flux=ref_flux,
                uncertainty=ref_unc,
                label=reference.label,
                metadata=dict(reference.metadata),
                model_params=None if reference.model_params is None else dict(reference.model_params),
            )
            template_scaled = Spectrum(
                wavelength=ref_wl,
                flux=tpl_flux_scaled,
                uncertainty=tpl_unc_scaled,
                label=template_original.label,
                metadata=dict(template_original.metadata),
                model_params=None if template_original.model_params is None else dict(template_original.model_params),
            )

            results.append(
                MatchResult(
                    statistic=float(statistic),
                    metric=metric,
                    observed=observed_out,
                    template_original=template_original,
                    template_scaled=template_scaled,
                    scale_factor=float(scale_factor),
                    offset=float(offset),
                )
            )

            if verbose:
                print(f"Compared {reference.label!r} with {template_original.label!r}: {metric} = {statistic:.6g}")

        reverse = metric == "cosine-similarity"
        results.sort(key=lambda x: x.statistic, reverse=reverse)
        results = [r for r in results if np.isfinite(r.statistic)]

        observed_result = results[0].observed if results else reference_prepared
        return ComparisonResult(
            observed=observed_result,
            best_matches=results[:number_of_matches],
            metric=metric,
            scaling_mode=scaling_mode,
            all_results=results,
        )

    def _scale_template(
        self,
        ref_flux: np.ndarray,
        ref_uncertainty: np.ndarray,
        tpl_flux: np.ndarray,
        tpl_uncertainty: np.ndarray,
        scaling_mode: str = "least-squares",
    ) -> Tuple[np.ndarray, np.ndarray, float, float]:
        if scaling_mode == "least-squares":
            return self._weighted_linear_scale(ref_flux, ref_uncertainty, tpl_flux, tpl_uncertainty)
        if scaling_mode == "scale-shift":
            return self._original_scale_shift(ref_flux, tpl_flux, tpl_uncertainty)
        raise ValueError(f"Unsupported scaling_mode: {scaling_mode}")

    def _original_scale_shift(
        self,
        ref_flux: np.ndarray,
        tpl_flux: np.ndarray,
        tpl_uncertainty: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, float, float]:
        tpl_mean = np.nanmean(tpl_flux)
        ref_mean = np.nanmean(ref_flux)

        if not np.isfinite(tpl_mean) or tpl_mean == 0:
            scale = 1.0
        else:
            scale = ref_mean / tpl_mean

        scaled_flux = tpl_flux * scale
        scaled_unc = tpl_uncertainty * abs(scale)

        offset = ref_mean - np.nanmean(scaled_flux)
        if not np.isfinite(offset):
            offset = 0.0

        scaled_flux = scaled_flux + offset
        return scaled_flux, scaled_unc, float(scale), float(offset)

    def _weighted_linear_scale(
        self,
        ref_flux: np.ndarray,
        ref_uncertainty: np.ndarray,
        tpl_flux: np.ndarray,
        tpl_uncertainty: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, float, float]:
        valid = np.isfinite(ref_flux) & np.isfinite(tpl_flux)
        if np.isfinite(ref_uncertainty).any():
            valid &= np.isfinite(ref_uncertainty)

        y = ref_flux[valid]
        x = tpl_flux[valid]

        if len(x) < 2:
            return tpl_flux.copy(), tpl_uncertainty.copy(), 1.0, 0.0

        if np.isfinite(ref_uncertainty).any():
            sigma = ref_uncertainty[valid].copy()
            positive = sigma > 0
            if not np.any(positive):
                sigma = np.full_like(y, np.nanstd(y) if np.nanstd(y) > 0 else 1.0)
            else:
                fallback = np.nanmedian(sigma[positive])
                sigma[~positive] = fallback
            w = 1.0 / sigma ** 2
        else:
            w = np.ones_like(y)

        X = np.column_stack([x, np.ones_like(x)])
        sqrt_w = np.sqrt(w)
        Xw = X * sqrt_w[:, None]
        yw = y * sqrt_w
        try:
            coeffs, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
            a, b = coeffs
        except np.linalg.LinAlgError:
            a, b = 1.0, 0.0

        scaled_flux = a * tpl_flux + b
        scaled_unc = np.abs(a) * tpl_uncertainty
        return scaled_flux, scaled_unc, float(a), float(b)

    def compare_fluxes(
        self,
        ref_flux: np.ndarray,
        ref_uncertainty: np.ndarray,
        tpl_flux: np.ndarray,
        metric: str,
    ) -> float:
        if metric == "reduced-chi2":
            if len(ref_flux) < 2:
                return np.nan
            uncertainty = ref_uncertainty.copy()
            if len(uncertainty) != len(ref_flux):
                uncertainty = np.full_like(ref_flux, np.nan)
            if not np.isfinite(uncertainty).any():
                fallback = np.nanmedian(np.abs(ref_flux)) * 0.2
                if not np.isfinite(fallback) or fallback <= 0:
                    fallback = 1.0
                uncertainty[:] = fallback
            positive = uncertainty > 0
            if not np.any(positive):
                uncertainty[:] = np.nanmedian(np.abs(uncertainty[np.isfinite(uncertainty)])) if np.isfinite(uncertainty).any() else 1.0
            else:
                fallback = np.nanmedian(uncertainty[positive])
                uncertainty[~positive] = fallback
            dof = max(np.count_nonzero(np.isfinite(ref_flux)) - 1, 1)
            return float(np.sum((ref_flux - tpl_flux) ** 2 / uncertainty ** 2) / dof)

        if metric == "mean-squared-error":
            return float(np.nanmean((ref_flux - tpl_flux) ** 2))

        raise ValueError(f"Unsupported metric: {metric}")
