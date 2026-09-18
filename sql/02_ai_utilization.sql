-- AI Utilization
--
-- Utilization answers: of the studies that were eligible for AI, how many
-- were actually processed by AI?

-- WHERE limits this report to eligible studies only. SUM with CASE WHEN adds
-- one for each eligible study that was AI processed. ROUND formats the final
-- percentage to one decimal place. NULLIF prevents division by zero by turning
-- a zero denominator into NULL.
SELECT
    COUNT(*) AS ai_eligible_studies,
    SUM(CASE WHEN ai_processed = 1 THEN 1 ELSE 0 END) AS eligible_studies_ai_processed,
    ROUND(
        100.0 * SUM(CASE WHEN ai_processed = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        1
    ) AS ai_utilization_percent
FROM imaging_studies
WHERE ai_eligible = 1;

-- GROUP BY calculates the same utilization metric independently for each site.
SELECT
    site,
    COUNT(*) AS ai_eligible_studies,
    SUM(CASE WHEN ai_processed = 1 THEN 1 ELSE 0 END) AS eligible_studies_ai_processed,
    ROUND(
        100.0 * SUM(CASE WHEN ai_processed = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        1
    ) AS ai_utilization_percent
FROM imaging_studies
WHERE ai_eligible = 1
GROUP BY site
ORDER BY site;

-- This final breakdown shows utilization for each imaging modality.
SELECT
    modality,
    COUNT(*) AS ai_eligible_studies,
    SUM(CASE WHEN ai_processed = 1 THEN 1 ELSE 0 END) AS eligible_studies_ai_processed,
    ROUND(
        100.0 * SUM(CASE WHEN ai_processed = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        1
    ) AS ai_utilization_percent
FROM imaging_studies
WHERE ai_eligible = 1
GROUP BY modality
ORDER BY modality;
