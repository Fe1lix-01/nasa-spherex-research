
import numpy as np

# P_D: PSF efectiva del resultado ZOGY
grad_y, grad_x = np.gradient(P_D)

templates = {
    "brightness": P_D.ravel(),
    "motion_x": (-grad_x).ravel(),
    "motion_y": (-grad_y).ravel(),
}

models = {
    "H0": [],
    "H1": ["brightness"],
    "H2": ["motion_x", "motion_y"],
    "H3": ["brightness", "motion_x", "motion_y"],
}

def evaluate_model(name, columns, difference):
    y = difference.ravel()

    if columns:
        X = np.column_stack(
            [templates[c] for c in columns]
        )
        coefficients = np.linalg.lstsq(
            X, y, rcond=None
        )[0]
        residual = y - X @ coefficients
    else:
        coefficients = []
        residual = y

    chi2 = np.sum(residual**2)
    bic = chi2 + len(columns) * np.log(len(y))

    return {
        "hypothesis": name,
        "bic": float(bic),
        "coefficients": np.asarray(
            coefficients
        ).tolist()
    }

results = [
    evaluate_model(name, cols, D)
    for name, cols in models.items()
]

best = min(results, key=lambda r: r["bic"])
print("Mejor hipótesis:", best["hypothesis"])
