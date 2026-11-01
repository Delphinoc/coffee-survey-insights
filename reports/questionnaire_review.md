# Questionnaire review: Great American Coffee Taste Test

A critique of the survey instrument, written the way an in-house researcher would review an agency draft before fieldwork. Each issue lists its evidence (from this dataset where possible) and a suggested fix.

| # | Issue | Evidence | Why it matters | Suggested fix |
|---|---|---|---|---|
| 1 | **Self-selected sample** (YouTube viewers who bought a tasting kit) | 75% of those stating gender are male; 74% aged 25–44; 40% rate expertise 7+/10 | Toplines can't be projected to "Americans". The winner may simply reflect the channel's audience | Use an online panel with quotas on age, gender and region; weight to census benchmarks; report the effective sample size |
| 2 | **Fixed tasting order** (A → B → C → D) | Order isn't randomised in the instrument | Order and palate-fatigue effects get confounded with the coffees themselves. D, tasted last, may benefit from a recency effect | Randomise the order per respondent (sequential monadic or Latin square) and record the order served |
| 3 | **Unanchored 1–10 expertise scale** | "How would you rate your own coffee expertise?" with no labels | Respondents interpret the numbers differently, so the scale is hard to compare across people | Add labelled anchors (1 = "I just drink it", 10 = "I could judge a competition") or use behavioural proxies (brew method, equipment spend) |
| 4 | **Overlapping concepts** | Separate "strength", "roast level" and "caffeine" questions; "strength" is ambiguous (brew ratio? roast? caffeine?) | Respondents conflate the three, which weakens each measure | Define each term in the question text, or drop "strength" |
| 5 | **Two-step forced choice** (prefer A/B/C, then A vs D, then overall) | 10 respondents chose a coffee in A-vs-D that they had rated 2+ points lower | It adds length and can produce inconsistent answers | Ask one overall ranking of all four, or a single "favourite" after all ratings |
| 6 | **Breakoff in the second half** | Completion falls from 99% (age) to 93% (tasting) to 87% (willingness to pay) to 85% (demographics) | Post-tasting and demographic answers come from a narrower group, which biases subgroup reads | Move the key demographics into the screener; shorten the post-tasting block; show a progress bar |
| 7 | **Banded price questions with uneven widths** | "$8–$10" sits next to "$10–$15" and "More than $20" | Uneven bands distort averages, and an open top band loses information | Use an open numeric entry with validation, or a Van Westendorp price-sensitivity module |
| 8 | **Same wording for two questions** (data dictionary) | `value_cafe` and `value_equipment` share one question label in the published dictionary | Analysts could misread the second item | Keep a versioned codebook that maps each variable to its exact question text and answer options |
| 9 | **Straight-lining check** | 7 respondents gave an identical score on all 12 tasting ratings | Low here, but there is no built-in attention check | Add one instructed-response item; flag straight-liners and speeders in QA |

**Overall:** the instrument works as a fun community tasting, but issues 1 and 2 mean it can't support a market-level product decision without a representative, randomised follow-up.
