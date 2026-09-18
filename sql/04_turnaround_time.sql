-- Turnaround Time
--
-- Turnaround time measures the elapsed time from study start to completion.
-- julianday converts each timestamp to a number of days. Subtracting the
-- start from the completion gives elapsed days, and multiplying by 24 * 60
-- converts that difference to minutes, including studies that cross midnight.
-- AVG adds the elapsed minutes and divides by the number of valid durations.
-- Missing or unrecognized timestamps produce NULL, which AVG ignores.
-- ROUND(..., 1) rounds the final average to one decimal place.

-- Overall average turnaround time across all studies.
SELECT
    ROUND(
        AVG((julianday(study_complete_time) - julianday(study_start_time)) * 24 * 60),
        1
    ) AS avg_turnaround_minutes
FROM imaging_studies;

-- GROUP BY site puts studies from the same site together so AVG calculates
-- a separate average for each site. ORDER BY lists sites alphabetically.
SELECT
    site,
    ROUND(
        AVG((julianday(study_complete_time) - julianday(study_start_time)) * 24 * 60),
        1
    ) AS avg_turnaround_minutes
FROM imaging_studies
GROUP BY site
ORDER BY site;

-- Grouping by modality calculates a separate average for each imaging type.
SELECT
    modality,
    ROUND(
        AVG((julianday(study_complete_time) - julianday(study_start_time)) * 24 * 60),
        1
    ) AS avg_turnaround_minutes
FROM imaging_studies
GROUP BY modality
ORDER BY modality;

-- SQLite stores ai_processed as 1 (true) or 0 (false) in this dataset.
-- GROUP BY ai_processed separates those two groups, and AVG calculates the
-- average within each group. CASE gives each group a readable label.
-- This compares all studies, including ineligible studies in the non-AI group.
-- A difference in this mock dataset does not establish that AI caused it.
SELECT
    CASE ai_processed
        WHEN 1 THEN 'AI-processed'
        WHEN 0 THEN 'Not processed by AI'
        ELSE 'Unknown'
    END AS ai_processing_status,
    ROUND(
        AVG((julianday(study_complete_time) - julianday(study_start_time)) * 24 * 60),
        1
    ) AS avg_turnaround_minutes
FROM imaging_studies
GROUP BY ai_processed
ORDER BY ai_processed DESC;
