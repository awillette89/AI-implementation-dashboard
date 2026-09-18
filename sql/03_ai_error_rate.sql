-- AI Error Rate
--
-- Error rate answers: when AI processing was attempted, how often did it fail?
-- The denominator is AI-processed studies only. It would be misleading to
-- include studies that never entered the AI workflow.

-- WHERE keeps only studies where AI processing was attempted. SUM with CASE
-- WHEN adds one for each processed study whose ai_error value is 1. NULLIF
-- safely prevents a division-by-zero error, and ROUND keeps one decimal place.
SELECT
    COUNT(*) AS ai_processed_studies,
    SUM(CASE WHEN ai_error = 1 THEN 1 ELSE 0 END) AS ai_error_studies,
    ROUND(
        100.0 * SUM(CASE WHEN ai_error = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        1
    ) AS ai_error_rate_percent
FROM imaging_studies
WHERE ai_processed = 1;

-- Calculate error rate separately for each site.
SELECT
    site,
    COUNT(*) AS ai_processed_studies,
    SUM(CASE WHEN ai_error = 1 THEN 1 ELSE 0 END) AS ai_error_studies,
    ROUND(
        100.0 * SUM(CASE WHEN ai_error = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        1
    ) AS ai_error_rate_percent
FROM imaging_studies
WHERE ai_processed = 1
GROUP BY site
ORDER BY site;

-- Calculate error rate separately for each modality.
SELECT
    modality,
    COUNT(*) AS ai_processed_studies,
    SUM(CASE WHEN ai_error = 1 THEN 1 ELSE 0 END) AS ai_error_studies,
    ROUND(
        100.0 * SUM(CASE WHEN ai_error = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        1
    ) AS ai_error_rate_percent
FROM imaging_studies
WHERE ai_processed = 1
GROUP BY modality
ORDER BY modality;
