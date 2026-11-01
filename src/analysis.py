"""Consumer-insight analysis on the Great American Coffee Taste Test survey.

Business question: a specialty coffee brand wants to know whether the coffee that
won the taste test (Coffee D, a fruity, high-acidity cup) should lead a
mainstream launch, and who will pay a premium.

Run after src/pipeline.py:  python -I src/analysis.py   (from project root)
Writes outputs/results.json and reports/figures/*.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import chi2_contingency
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from survey_tools import code_open_ends, kish_ess, rake, two_prop_ci, weighted_shares  # noqa: E402

DB = ROOT / "outputs" / "coffee_survey.duckdb"
FIG = ROOT / "reports" / "figures"
OUT = ROOT / "outputs" / "results.json"

COFFEES = ["Coffee A", "Coffee B", "Coffee C", "Coffee D"]
# Reference categorical palette, slots 1-4 (validated adjacent-pair CVD-safe).
COLORS = dict(zip(COFFEES, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]))
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
BANDS = ["Novice (1-3)", "Intermediate (4-6)", "Enthusiast (7-10)"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": "#c3c2b7",
    "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK,
    "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
})


def cramers_v(table: pd.DataFrame) -> float:
    chi2 = chi2_contingency(table)[0]
    n = table.values.sum()
    return float(np.sqrt(chi2 / (n * (min(table.shape) - 1))))


def stacked_share_chart(shares: pd.DataFrame, title: str, path: Path, n: pd.Series) -> None:
    fig, ax = plt.subplots(figsize=(8, 3.4))
    left = np.zeros(len(shares))
    for coffee in COFFEES:
        vals = shares[coffee].values
        ax.barh(range(len(shares)), vals, left=left, color=COLORS[coffee],
                edgecolor=SURFACE, linewidth=2, height=0.62, label=coffee)
        for i, (l, v) in enumerate(zip(left, vals)):
            if v >= 0.08:
                ax.text(l + v / 2, i, f"{v:.0%}", ha="center", va="center",
                        color=INK if coffee == "Coffee D" else "white", fontsize=9)
        left += vals
    ax.set_yticks(range(len(shares)))
    ax.set_yticklabels([f"{idx}\n(n={n[idx]:,})" for idx in shares.index], color=INK2)
    ax.set_xlim(0, 1)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.invert_yaxis()
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    ax.legend(ncol=4, loc="upper left", bbox_to_anchor=(0, -0.12), frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> dict:
    con = duckdb.connect(str(DB), read_only=True)
    df = con.sql("SELECT * FROM mart_respondents").df()
    res: dict = {}
    res["exclusions"] = con.sql("SELECT stage, respondents FROM mart_exclusions ORDER BY step").df().to_dict("records")
    res["completion"] = con.sql("SELECT section, completion_rate FROM mart_completion ORDER BY section_order").df().to_dict("records")
    res["ratings"] = con.sql("SELECT * FROM mart_coffee_ratings").df().round(2).to_dict("records")
    res["dq_flags"] = con.sql("""SELECT SUM(dq_straightlined::INT) AS straightlined,
        SUM(dq_inconsistent_choice::INT) AS inconsistent_choice, SUM(dq_under_18::INT) AS under_18,
        SUM(dq_duplicate_id::INT) AS duplicate_ids FROM stg_survey""").df().iloc[0].astype(int).to_dict()
    n = len(df)
    res["n_base"] = n

    # 1. Topline -------------------------------------------------------------
    top = weighted_shares(df.prefer_overall).reindex(COFFEES)
    res["topline"] = top.round(4).to_dict()
    sample = {
        "male_share_of_stated_gender": float((df.gender_group == "Male").sum() / df.gender_group.isin(["Male", "Female"]).sum()),
        "enthusiast_share": float((df.expertise_band == "Enthusiast (7-10)").mean()),
        "age_25_44_share": float(df.age.isin(["25-34 years old", "35-44 years old"]).mean()),
    }
    res["sample_profile"] = {k: round(v, 4) for k, v in sample.items()}

    # 2. Preference by expertise ---------------------------------------------
    sub = df[df.expertise_band.notna()]
    ct = pd.crosstab(sub.expertise_band, sub.prefer_overall).reindex(index=BANDS, columns=COFFEES)
    chi2, p, dof, _ = chi2_contingency(ct)
    shares_exp = ct.div(ct.sum(axis=1), axis=0)
    res["pref_by_expertise"] = {"shares": shares_exp.round(4).to_dict("index"), "n": ct.sum(axis=1).to_dict(),
                                "chi2": round(chi2, 1), "dof": int(dof), "p": float(p), "cramers_v": round(cramers_v(ct), 3)}
    stacked_share_chart(shares_exp, "Favourite coffee by self-rated expertise: Coffee D's lead comes from enthusiasts",
                        FIG / "01_favourite_by_expertise.png", ct.sum(axis=1))

    # Novice vs enthusiast gap on Coffee D
    nov, ent = sub[sub.expertise_band == BANDS[0]], sub[sub.expertise_band == BANDS[2]]
    d, lo, hi = two_prop_ci((ent.prefer_overall == "Coffee D").sum(), len(ent), (nov.prefer_overall == "Coffee D").sum(), len(nov))
    res["d_gap_enthusiast_vs_novice"] = {"diff_pp": round(d * 100, 1), "ci_pp": [round(lo * 100, 1), round(hi * 100, 1)]}

    # 3. Preference by gender ------------------------------------------------
    g = df[df.gender_group.isin(["Male", "Female"])]
    ctg = pd.crosstab(g.gender_group, g.prefer_overall).reindex(columns=COFFEES)
    chi2g, pg, _, _ = chi2_contingency(ctg)
    res["pref_by_gender"] = {"shares": ctg.div(ctg.sum(axis=1), axis=0).round(4).to_dict("index"),
                             "n": ctg.sum(axis=1).to_dict(), "chi2": round(chi2g, 1), "p": float(pg),
                             "cramers_v": round(cramers_v(ctg), 3)}

    # 4. Logistic regression: who picks Coffee D? ----------------------------
    m = df.dropna(subset=["expertise", "age_order"]).copy()
    m["pick_d"] = (m.prefer_overall == "Coffee D").astype(int)
    m["female"] = (m.gender_group == "Female").astype(int)
    m["black"] = m.drinks_black.astype(int)
    fit = smf.logit("pick_d ~ expertise + female + age_order + black", data=m).fit(disp=0)
    ors = np.exp(fit.params)
    ci = np.exp(fit.conf_int())
    res["logit_pick_d"] = {
        "n": int(fit.nobs),
        "odds_ratios": {k: {"or": round(ors[k], 3), "ci": [round(ci.loc[k, 0], 3), round(ci.loc[k, 1], 3)],
                            "p": float(fit.pvalues[k])} for k in ["expertise", "female", "age_order", "black"]},
        "pseudo_r2": round(fit.prsquared, 3),
    }

    # 5. Weighting sensitivity: rebalance gender to parity --------------------
    # Assumption (stated in memo): mainstream coffee drinkers are ~50/50 male/female.
    # Respondents outside Male/Female keep their observed share.
    w = rake(df, {"gender_group": {"Male": 0.5, "Female": 0.5}})
    res["weighting"] = {
        "target": "Male 50% / Female 50% of respondents stating male or female",
        "weighted_topline": weighted_shares(df.prefer_overall, w).reindex(COFFEES).round(4).to_dict(),
        "kish_ess": round(kish_ess(w)), "weight_min": round(w.min(), 2), "weight_max": round(w.max(), 2),
    }
    # "Mainstream proxy": non-enthusiasts who do not drink coffee black
    mainstream = df[(df.expertise_band.isin(BANDS[:2])) & (~df.drinks_black)]
    res["mainstream_proxy"] = {"n": len(mainstream),
                               "topline": weighted_shares(mainstream.prefer_overall).reindex(COFFEES).round(4).to_dict()}

    fig, ax = plt.subplots(figsize=(8, 3.2))
    rows = {"All respondents\n(unweighted)": res["topline"],
            "Gender rebalanced 50/50\n(Kish effective n)": res["weighting"]["weighted_topline"],
            "Mainstream proxy\n(non-enthusiast, not black)": res["mainstream_proxy"]["topline"]}
    shares_w = pd.DataFrame(rows).T[COFFEES]
    nn = pd.Series({list(rows)[0]: n, list(rows)[1]: res["weighting"]["kish_ess"], list(rows)[2]: len(mainstream)})
    plt.close(fig)
    stacked_share_chart(shares_w, "Coffee D's topline lead shrinks or reverses outside the enthusiast core",
                        FIG / "02_topline_sensitivity.png", nn)

    # 6. Willingness to pay ---------------------------------------------------
    wtp = df.dropna(subset=["willing_order"])
    res["wtp_15_plus"] = {
        "by_expertise": wtp.groupby("expertise_band").willing_15_plus.mean().reindex(BANDS).round(4).to_dict(),
        "by_favourite": wtp.groupby("prefer_overall").willing_15_plus.mean().reindex(COFFEES).round(4).to_dict(),
        "overall": round(float(wtp.willing_15_plus.mean()), 4), "n": len(wtp),
    }

    # 7. Taste-profile segmentation (k-means on the four 1-5 preference scores)
    X = df[["a_pref", "b_pref", "c_pref", "d_pref"]].to_numpy(dtype=float)
    sil = {}
    for k in range(2, 7):
        lab = KMeans(n_clusters=k, n_init=20, random_state=42).fit_predict(X)
        sil[k] = round(float(silhouette_score(X, lab, sample_size=3000, random_state=42)), 3)
    k_best = 4  # chosen for interpretability; silhouette scores reported alongside
    km = KMeans(n_clusters=k_best, n_init=20, random_state=42).fit(X)
    df["segment"] = km.labels_
    prof = df.groupby("segment").agg(
        size=("segment", "size"), a=("a_pref", "mean"), b=("b_pref", "mean"), c=("c_pref", "mean"), d=("d_pref", "mean"),
        enthusiast=("expertise_band", lambda s: (s == BANDS[2]).mean()),
        female=("gender_group", lambda s: (s == "Female").sum() / s.isin(["Male", "Female"]).sum()),
        black=("drinks_black", "mean"), wtp15=("willing_15_plus", "mean"),
    )
    prof["share"] = prof["size"] / n

    def name(r):
        top_two = r[["a", "b", "c", "d"]].sort_values(ascending=False).index[:2]
        return "Prefers " + " + ".join(sorted(t.upper() for t in top_two))
    prof["name"] = prof.apply(name, axis=1)
    prof = prof.sort_values("share", ascending=False)
    res["segmentation"] = {"silhouette": sil, "k": k_best,
                           "profiles": prof.round(3).reset_index(drop=True).to_dict("records")}

    fig, ax = plt.subplots(figsize=(8, 3.6))
    x = np.arange(len(prof))
    width = 0.19
    for i, (col, coffee) in enumerate(zip(["a", "b", "c", "d"], COFFEES)):
        ax.bar(x + (i - 1.5) * width, prof[col], width=width - 0.02, color=COLORS[coffee], label=coffee)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r['name']}\n{r['share']:.0%} of base" for _, r in prof.iterrows()], fontsize=8.5, color=INK2)
    ax.set_ylim(1, 5)
    ax.set_ylabel("Mean preference (1-5)")
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title("Four taste segments: two of them (41% of the base) rate Coffee D near the bottom",
                 loc="left", fontsize=11)
    ax.legend(ncol=4, loc="upper left", bbox_to_anchor=(0, -0.2), frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "03_taste_segments.png", dpi=160)
    plt.close(fig)

    # 8. Open-ended notes: why do people dislike Coffee D? ---------------------
    likers = df[df.d_pref >= 4]
    dislikers = df[df.d_pref <= 2]
    lc, dc = code_open_ends(likers.coffee_d_notes), code_open_ends(dislikers.coffee_d_notes)
    has_l, has_d = likers.coffee_d_notes.notna(), dislikers.coffee_d_notes.notna()
    codes = pd.DataFrame({"likers": lc[has_l].mean(), "dislikers": dc[has_d].mean()}).round(4)
    res["open_ends_coffee_d"] = {"n_likers_with_notes": int(has_l.sum()), "n_dislikers_with_notes": int(has_d.sum()),
                                 "code_rates": codes.to_dict("index")}

    fig, ax = plt.subplots(figsize=(8, 3.4))
    codes = codes.sort_values("dislikers")
    y = np.arange(len(codes))
    ax.barh(y + 0.2, codes["likers"], height=0.36, color="#2a78d6", label=f"Rated D 4-5 (n={has_l.sum():,})")
    ax.barh(y - 0.2, codes["dislikers"], height=0.36, color="#eb6834", label=f"Rated D 1-2 (n={has_d.sum():,})")
    ax.set_yticks(y)
    ax.set_yticklabels(codes.index, color=INK2)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title("Same cup, different words: dislikers are twice as likely to call Coffee D 'sour'",
                 loc="left", fontsize=11)
    ax.set_xlabel("Share of tasting notes mentioning theme")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG / "04_coffee_d_open_ends.png", dpi=160)
    plt.close(fig)

    OUT.write_text(json.dumps(res, indent=2, default=float))
    con.close()
    return res


if __name__ == "__main__":
    r = main()
    print(json.dumps(r, indent=1, default=float))
