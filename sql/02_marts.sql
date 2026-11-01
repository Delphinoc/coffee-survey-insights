-- 02_marts.sql
-- Analysis-ready tables built from stg_survey.

-- Analysis base: adults who completed the tasting block, not straight-lined,
-- with a stated overall favourite.
CREATE OR REPLACE TABLE mart_respondents AS
SELECT *
FROM stg_survey
WHERE NOT COALESCE(dq_under_18, false)
  AND NOT dq_incomplete_tasting
  AND NOT dq_missing_outcome
  AND NOT COALESCE(dq_straightlined, false)
  AND NOT dq_duplicate_id;

-- Exclusion waterfall (for the README / memo).
CREATE OR REPLACE TABLE mart_exclusions AS
SELECT 1 AS step, 'All submissions' AS stage, COUNT(*) AS respondents FROM stg_survey
UNION ALL
SELECT 2, 'Adults (18+ or age not stated)', COUNT(*) FROM stg_survey WHERE NOT COALESCE(dq_under_18, false)
UNION ALL
SELECT 3, '... completed all 4 tasting ratings', COUNT(*) FROM stg_survey
 WHERE NOT COALESCE(dq_under_18, false) AND NOT dq_incomplete_tasting
UNION ALL
SELECT 4, '... named an overall favourite', COUNT(*) FROM stg_survey
 WHERE NOT COALESCE(dq_under_18, false) AND NOT dq_incomplete_tasting AND NOT dq_missing_outcome
UNION ALL
SELECT 5, '... not straight-lined (analysis base)', COUNT(*) FROM mart_respondents
ORDER BY step;

-- Section-level completion: how far respondents got through the questionnaire.
CREATE OR REPLACE TABLE mart_completion AS
SELECT 1 AS section_order, 'Screener: age' AS section,
       AVG(CASE WHEN age IS NOT NULL THEN 1 ELSE 0 END) AS completion_rate FROM stg_survey
UNION ALL SELECT 2, 'Habits: roast preference',
       AVG(CASE WHEN roast_level IS NOT NULL THEN 1 ELSE 0 END) FROM stg_survey
UNION ALL SELECT 3, 'Tasting: all 4 coffees rated',
       AVG(CASE WHEN NOT dq_incomplete_tasting THEN 1 ELSE 0 END) FROM stg_survey
UNION ALL SELECT 4, 'Post-tasting: willingness to pay',
       AVG(CASE WHEN most_willing IS NOT NULL THEN 1 ELSE 0 END) FROM stg_survey
UNION ALL SELECT 5, 'Demographics: education',
       AVG(CASE WHEN education_level IS NOT NULL THEN 1 ELSE 0 END) FROM stg_survey
ORDER BY section_order;

-- Mean sensory ratings per coffee (long format).
CREATE OR REPLACE TABLE mart_coffee_ratings AS
SELECT 'Coffee A' AS coffee, AVG(a_bitterness) AS bitterness, AVG(a_acidity) AS acidity, AVG(a_pref) AS preference FROM mart_respondents
UNION ALL SELECT 'Coffee B', AVG(b_bitterness), AVG(b_acidity), AVG(b_pref) FROM mart_respondents
UNION ALL SELECT 'Coffee C', AVG(c_bitterness), AVG(c_acidity), AVG(c_pref) FROM mart_respondents
UNION ALL SELECT 'Coffee D', AVG(d_bitterness), AVG(d_acidity), AVG(d_pref) FROM mart_respondents
ORDER BY coffee;

-- Favourite-coffee share by expertise band.
CREATE OR REPLACE TABLE mart_pref_by_expertise AS
SELECT expertise_band, prefer_overall, COUNT(*) AS n,
       COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY expertise_band) AS share
FROM mart_respondents
WHERE expertise_band IS NOT NULL
GROUP BY 1, 2;

-- Favourite-coffee share by gender group.
CREATE OR REPLACE TABLE mart_pref_by_gender AS
SELECT gender_group, prefer_overall, COUNT(*) AS n,
       COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY gender_group) AS share
FROM mart_respondents
GROUP BY 1, 2;
