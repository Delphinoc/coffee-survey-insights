"""Reusable survey-analysis helpers: raking weights, weighted shares, Kish ESS,
and simple keyword coding of open-ended answers."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd


def rake(df: pd.DataFrame, targets: dict[str, dict[str, float]],
         max_iter: int = 100, tol: float = 1e-8,
         trim: tuple[float, float] = (0.2, 5.0)) -> pd.Series:
    """Iterative proportional fitting (raking).

    targets maps column -> {category: target share}. Categories in a column that
    are absent from its targets keep their observed share (they are left out of
    the adjustment), so the targets for listed categories are rescaled to the
    share those categories hold in the sample.
    Weights are normalised to mean 1 and trimmed to `trim` (then re-normalised).
    """
    w = pd.Series(1.0, index=df.index)
    # share of the sample covered by each column's targets, fixed at the observed value
    scope = {col: df[col].isin(tgt.keys()).mean() for col, tgt in targets.items()}
    for _ in range(max_iter):
        max_change = 0.0
        for col, tgt in targets.items():
            scope_share = scope[col]
            tgt_total = sum(tgt.values())
            for cat, share in tgt.items():
                mask = df[col] == cat
                current = w[mask].sum() / w.sum()
                if current == 0:
                    continue
                desired = share / tgt_total * scope_share
                factor = desired / current
                max_change = max(max_change, abs(factor - 1))
                w[mask] *= factor
        if max_change < tol:
            break
    w = w / w.mean()
    w = w.clip(*trim)
    return w / w.mean()


def kish_ess(weights: pd.Series) -> float:
    """Kish effective sample size: (sum w)^2 / sum w^2."""
    return float(weights.sum() ** 2 / (weights ** 2).sum())


def weighted_shares(values: pd.Series, weights: pd.Series | None = None) -> pd.Series:
    """Share of each category, optionally weighted."""
    if weights is None:
        weights = pd.Series(1.0, index=values.index)
    out = weights.groupby(values).sum()
    return out / out.sum()


CODEFRAME = {
    "fruity / berry": r"fruit|berr|blueberr|strawberr|cherr|citrus|lemon|tropical|jam",
    "fermented / funky": r"ferment|funk|boozy|wine|winey|alcohol",
    "sour / acidic": r"sour|acid|tart|tangy",
    "bitter / burnt": r"bitter|burnt|burned|ashy|smoky|charcoal",
    "chocolate / nutty": r"chocolat|cocoa|nut|caramel|toffee",
    "balanced / smooth": r"balanc|smooth|mellow|clean|round",
}


def code_open_ends(notes: pd.Series, codeframe: dict[str, str] = CODEFRAME) -> pd.DataFrame:
    """Multi-label keyword coding of free-text tasting notes.

    Returns one boolean column per code (a note can carry several codes).
    """
    text = notes.fillna("").str.lower()
    return pd.DataFrame(
        {code: text.str.contains(pattern, regex=True) for code, pattern in codeframe.items()},
        index=notes.index,
    )


def two_prop_ci(x1: int, n1: int, x2: int, n2: int, z: float = 1.96) -> tuple[float, float, float]:
    """Difference in proportions (p1 - p2) with a Wald 95% CI."""
    p1, p2 = x1 / n1, x2 / n2
    diff = p1 - p2
    se = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    return diff, diff - z * se, diff + z * se


def clean_label(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()
