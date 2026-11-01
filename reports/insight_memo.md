# Insight memo: Should the taste-test winner lead a mainstream launch?

**To:** Marketing lead, specialty coffee brand (hypothetical brief)
**Data:** Great American Coffee Taste Test (Oct 2023), 4,042 online submissions; analysis base 3,716 adults who rated all four blind coffees
**Method:** DuckDB SQL staging with data-quality flags, cross-tabs with chi-square tests, logistic regression, raking weights, k-means segmentation, coded open-ended notes

---

## Bottom line

Coffee D (fruity, high acidity) won the taste test with **37%** of first choices. That win comes from a self-selected enthusiast audience. Among less experienced drinkers who don't take their coffee black, **D comes last (21%)**, behind the classic, lower-acidity Coffees B and C (30% each).

**Recommendation:** position D as a premium, enthusiast-led product (direct-to-consumer, subscription). Lead the mainstream range with a B/C-style balanced coffee. Before committing launch spend, validate with a nationally representative sample.

## Key findings

1. **D's lead depends on expertise.** D is the favourite of 46% of self-rated enthusiasts (7–10) but only 22% of novices (1–3). The gap is 23.7 pp (95% CI 19.4–28.0). Novices most often pick Coffee B (33%). Expertise and favourite coffee are associated (χ² = 174, p < 0.001, Cramér's V = 0.15).
2. **Other factors also predict choosing D.** In a logistic regression, each extra expertise point raises the odds of picking D by **15%** (OR 1.15). Drinking coffee black roughly **doubles** them (OR 2.20). Women (OR 0.77) and older respondents (OR 0.87 per age band) are less likely to pick D. All p < 0.01; pseudo-R² is 0.06, so these are associations, not causes.
3. **The sample is not the market.** 75% of respondents who gave a gender are male, 74% are aged 25–44, and 40% rate themselves 7+/10 on expertise. Rebalancing gender to 50/50 alone cuts D's share from 37% to 33% (Kish effective n = 2,867). The data can't correct for expertise, which is the larger bias.
4. **The taste segments are distinct.** The four k-means taste segments include two (41% of the base) that rate D at or below 2.1/5. The "Prefers A + D" segment (37%) is 53% enthusiasts and 81% black-coffee drinkers.
5. **Enthusiasts pay more.** 37% of enthusiasts would pay $15+ for a cup, against 12% of novices. Among people whose favourite is D, the figure is 34%, against 18% for B or C fans. That supports a premium price for D.
6. **Open-ended notes show why people dislike D.** People who rated D 1–2 were twice as likely to call it "sour/acidic" (26% vs 14%) and less likely to call it "fruity" (54% vs 78%). Mainstream packaging copy should set expectations ("bright, berry-like") rather than lead with "fermented/funky".

## Caveats

- This is a self-selected YouTube audience, not a probability sample. Treat these figures as directional.
- The gender target (50/50) is an assumption for a sensitivity test, not a census benchmark.
- The k-means silhouette score is modest (0.25 at k = 4). The segments are overlapping taste tendencies, not hard types.
- The tasting order was fixed (A → D), so order effects can't be ruled out (see `questionnaire_review.md`).

## Proposed next step (for agency brief / RFP)

Commission a nationally representative online survey of about 1,500 US coffee drinkers, with quotas on age, gender and region and a screener for brew habits. Include a sequential monadic, randomised-order blind tasting of D against a balanced B/C-style coffee, plus a price-sensitivity module (Van Westendorp). Success metric: share preferring D among non-enthusiasts, with a pre-registered decision threshold.
