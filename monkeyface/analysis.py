"""Component 4b: rank which factors drive defect_rate, with honest confidence.

Pure function. Leads with interpretable methods: standardized ridge regression
(handles correlated weather variables) for effect ranking, plus per-factor
correlation confidence intervals for honesty. Includes the spike explainer.
"""
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


@dataclass
class FactorResult:
    name: str
    std_effect: float      # standardized ridge coefficient (comparable across factors)
    direction: str         # "increases" | "decreases" | "none"
    corr: float            # Pearson r vs defect_rate
    ci_low: float          # 95% CI on r
    ci_high: float
    confidence: str        # "strong" | "suggestive" | "weak"


@dataclass
class AnalysisResult:
    factors: list[FactorResult]
    n: int
    spike: dict | None = None
    notes: list[str] = field(default_factory=list)


def _corr_ci(r: float, n: int) -> tuple[float, float]:
    """Fisher z 95% CI for a Pearson correlation."""
    if n < 4 or abs(r) >= 1.0:
        return (r, r)
    z = np.arctanh(r)
    se = 1.0 / np.sqrt(n - 3)
    lo, hi = z - 1.96 * se, z + 1.96 * se
    return (float(np.tanh(lo)), float(np.tanh(hi)))


def _confidence(r: float, ci: tuple[float, float], n: int) -> str:
    lo, hi = ci
    sig = lo > 0 or hi < 0          # CI excludes zero
    if sig and abs(r) >= 0.3:
        return "strong"
    if sig and abs(r) >= 0.15:
        return "suggestive"
    return "weak"


def _table_to_frame(rows: list[dict]) -> pd.DataFrame:
    recs = []
    for r in rows:
        rec = dict(r["features"])
        rec["defect_rate"] = r["defect_rate"]
        rec["harvest_date"] = r.get("harvest_date")
        rec["grower"] = r.get("grower")
        recs.append(rec)
    return pd.DataFrame(recs)


def analyze(rows: list[dict]) -> AnalysisResult:
    df = _table_to_frame(rows)
    feature_cols = [c for c in df.columns
                    if c not in ("defect_rate", "harvest_date", "grower")]

    X = df[feature_cols].astype(float).values
    y = df["defect_rate"].astype(float).values
    n = len(df)

    Xs = StandardScaler().fit_transform(X)
    ridge = Ridge(alpha=1.0).fit(Xs, y)

    factors = []
    for col, coef in zip(feature_cols, ridge.coef_):
        r = float(np.corrcoef(df[col].astype(float), y)[0, 1]) if df[col].nunique() > 1 else 0.0
        ci = _corr_ci(r, n)
        conf = _confidence(r, ci, n)
        direction = "increases" if coef > 1e-6 else "decreases" if coef < -1e-6 else "none"
        factors.append(FactorResult(
            name=col, std_effect=float(coef), direction=direction,
            corr=r, ci_low=ci[0], ci_high=ci[1], confidence=conf,
        ))

    factors.sort(key=lambda f: abs(f.std_effect), reverse=True)

    spike = _spike_explainer(df, feature_cols)
    notes = []
    if n < 100:
        notes.append(f"Only {n} lots; treat all findings as suggestive, not conclusive.")
    return AnalysisResult(factors=factors, n=n, spike=spike, notes=notes)


def _spike_explainer(df: pd.DataFrame, feature_cols: list[str]) -> dict | None:
    """Identify the highest-defect year and which factors were anomalous then.

    Returns None when there is no cross-year comparison to make (no dates, or
    only a single year), so the UI shows the honest "only one year" message
    instead of a fabricated comparison where every z-score is structurally 0.
    """
    if df["harvest_date"].isna().all():
        return None
    years = pd.to_datetime(df["harvest_date"]).dt.year
    if years.nunique() < 2:
        return None
    by_year_defect = df.groupby(years)["defect_rate"].mean()
    if by_year_defect.empty:
        return None
    spike_year = int(by_year_defect.idxmax())

    anomalous = []
    for col in feature_cols:
        overall = df[col].astype(float).mean()
        overall_sd = df[col].astype(float).std() or 1.0
        spike_mean = df[years == spike_year][col].astype(float).mean()
        z = (spike_mean - overall) / overall_sd
        if abs(z) >= 1.0:
            anomalous.append({"factor": col, "z": round(float(z), 2),
                              "spike_mean": round(float(spike_mean), 2),
                              "overall_mean": round(float(overall), 2)})
    anomalous.sort(key=lambda a: abs(a["z"]), reverse=True)
    return {"year": spike_year,
            "defect_rate": round(float(by_year_defect.max()), 4),
            "anomalous_factors": anomalous}
