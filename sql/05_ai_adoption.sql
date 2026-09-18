-- AI Adoption
--
-- Adoption asks: when an AI result was available, did the radiologist use it?
-- The denominator is studies with an available AI result, because a
-- radiologist needs an available result before they can use it.
-- WHERE keeps only rows where ai_result_available = 1 (true).
-- COUNT(*) counts those rows. CASE WHEN contributes 1 when the radiologist
-- used AI and 0 otherwise, and SUM adds those values to count adoption.
-- COALESCE turns an empty SUM into 0 if no results were available.
-- Multiplying by 100.0 gives a percentage and keeps decimal division.
-- NULLIF changes a zero denominator to NULL, avoiding division by zero.
-- An adoption rate of NULL means there were no available results to assess.
-- ROUND(..., 1) rounds the percentage to one decimal place.

-- Overall adoption among studies with an AI result available.
SELECT
    COUNT(*) AS ai_result_available_studies,
    COALESCE(SUM(CASE WHEN radiologist_used_ai = 1 THEN 1 ELSE 0 END), 0)
        AS radiologist_used_ai_studies,
    ROUND(
        100.0 * COALESCE(SUM(CASE WHEN radiologist_used_ai = 1 THEN 1 ELSE 0 END), 0)
        / NULLIF(COUNT(*), 0),
        1
    ) AS ai_adoption_rate_percent
FROM imaging_studies
WHERE ai_result_available = 1;

-- GROUP BY site collects each site's remaining rows into a separate group.
-- The counts and percentage are calculated within each group.
-- ORDER BY lists sites alphabetically. Sites with no available results are
-- absent because WHERE removes their rows before grouping.
SELECT
    site,
    COUNT(*) AS ai_result_available_studies,
    COALESCE(SUM(CASE WHEN radiologist_used_ai = 1 THEN 1 ELSE 0 END), 0)
        AS radiologist_used_ai_studies,
    ROUND(
        100.0 * COALESCE(SUM(CASE WHEN radiologist_used_ai = 1 THEN 1 ELSE 0 END), 0)
        / NULLIF(COUNT(*), 0),
        1
    ) AS ai_adoption_rate_percent
FROM imaging_studies
WHERE ai_result_available = 1
GROUP BY site
ORDER BY site;

-- GROUP BY modality calculates adoption separately for each imaging type
-- with at least one available AI result.
SELECT
    modality,
    COUNT(*) AS ai_result_available_studies,
    COALESCE(SUM(CASE WHEN radiologist_used_ai = 1 THEN 1 ELSE 0 END), 0)
        AS radiologist_used_ai_studies,
    ROUND(
        100.0 * COALESCE(SUM(CASE WHEN radiologist_used_ai = 1 THEN 1 ELSE 0 END), 0)
        / NULLIF(COUNT(*), 0),
        1
    ) AS ai_adoption_rate_percent
FROM imaging_studies
WHERE ai_result_available = 1
GROUP BY modality
ORDER BY modality;
