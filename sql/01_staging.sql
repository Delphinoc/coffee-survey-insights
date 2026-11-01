-- 01_staging.sql
-- Raw survey CSV -> typed staging table with data-quality flags.
-- One row per submission. No rows are dropped here; exclusions happen in the marts.

CREATE OR REPLACE TABLE raw_survey AS
SELECT * FROM read_csv_auto(getvariable('raw_path'), nullstr = 'NA', all_varchar = true);

CREATE OR REPLACE TABLE stg_survey AS
WITH typed AS (
    SELECT
        submission_id,
        age,
        CASE age
            WHEN '<18 years old'   THEN 0
            WHEN '18-24 years old' THEN 1
            WHEN '25-34 years old' THEN 2
            WHEN '35-44 years old' THEN 3
            WHEN '45-54 years old' THEN 4
            WHEN '55-64 years old' THEN 5
            WHEN '>65 years old'   THEN 6
        END                                                  AS age_order,
        cups,
        favorite,
        additions,
        roast_level,
        style,
        TRY_CAST(expertise AS INTEGER)                       AS expertise,
        TRY_CAST(coffee_a_bitterness AS INTEGER)             AS a_bitterness,
        TRY_CAST(coffee_a_acidity AS INTEGER)                AS a_acidity,
        TRY_CAST(coffee_a_personal_preference AS INTEGER)    AS a_pref,
        TRY_CAST(coffee_b_bitterness AS INTEGER)             AS b_bitterness,
        TRY_CAST(coffee_b_acidity AS INTEGER)                AS b_acidity,
        TRY_CAST(coffee_b_personal_preference AS INTEGER)    AS b_pref,
        TRY_CAST(coffee_c_bitterness AS INTEGER)             AS c_bitterness,
        TRY_CAST(coffee_c_acidity AS INTEGER)                AS c_acidity,
        TRY_CAST(coffee_c_personal_preference AS INTEGER)    AS c_pref,
        TRY_CAST(coffee_d_bitterness AS INTEGER)             AS d_bitterness,
        TRY_CAST(coffee_d_acidity AS INTEGER)                AS d_acidity,
        TRY_CAST(coffee_d_personal_preference AS INTEGER)    AS d_pref,
        coffee_a_notes, coffee_b_notes, coffee_c_notes, coffee_d_notes,
        prefer_abc,
        prefer_ad,
        prefer_overall,
        wfh,
        total_spend,
        most_willing,
        CASE most_willing
            WHEN 'Less than $2'  THEN 1
            WHEN '$2-$4'         THEN 2
            WHEN '$4-$6'         THEN 3
            WHEN '$6-$8'         THEN 4
            WHEN '$8-$10'        THEN 5
            WHEN '$10-$15'       THEN 6
            WHEN '$15-$20'       THEN 7
            WHEN 'More than $20' THEN 8
        END                                                  AS willing_order,
        value_cafe,
        taste,
        gender,
        education_level,
        employment_status
    FROM raw_survey
)
SELECT
    *,
    CASE
        WHEN expertise BETWEEN 1 AND 3  THEN 'Novice (1-3)'
        WHEN expertise BETWEEN 4 AND 6  THEN 'Intermediate (4-6)'
        WHEN expertise BETWEEN 7 AND 10 THEN 'Enthusiast (7-10)'
    END                                                      AS expertise_band,
    CASE
        WHEN gender IN ('Male', 'Female') THEN gender
        WHEN gender IS NULL               THEN 'Not stated'
        ELSE 'Other / prefer not to say'
    END                                                      AS gender_group,
    COALESCE(additions ILIKE '%just black%', false)          AS drinks_black,
    willing_order >= 7                                       AS willing_15_plus,

    -- Data-quality flags -------------------------------------------------
    age_order = 0                                            AS dq_under_18,
    (a_pref IS NULL OR b_pref IS NULL OR c_pref IS NULL OR d_pref IS NULL)
                                                             AS dq_incomplete_tasting,
    prefer_overall IS NULL                                   AS dq_missing_outcome,
    -- every one of the 12 tasting ratings identical = straight-lining
    (a_bitterness = a_acidity AND a_acidity = a_pref
      AND a_pref = b_bitterness AND b_bitterness = b_acidity AND b_acidity = b_pref
      AND b_pref = c_bitterness AND c_bitterness = c_acidity AND c_acidity = c_pref
      AND c_pref = d_bitterness AND d_bitterness = d_acidity AND d_acidity = d_pref)
                                                             AS dq_straightlined,
    -- forced-choice answer contradicts the respondent's own 1-5 ratings by 2+ points
    (prefer_ad = 'Coffee A' AND d_pref - a_pref >= 2)
      OR (prefer_ad = 'Coffee D' AND a_pref - d_pref >= 2)   AS dq_inconsistent_choice,
    COUNT(*) OVER (PARTITION BY submission_id) > 1           AS dq_duplicate_id
FROM typed;
