-- Studies Processed
--
-- Each SELECT statement below answers one version of the volume question.

-- SELECT chooses the value to display. COUNT(*) counts every study row.
SELECT COUNT(*) AS total_studies_processed
FROM imaging_studies;

-- GROUP BY puts studies with the same date into one group. COUNT(*) then
-- counts the studies in each group. ORDER BY shows the dates chronologically.
SELECT
    study_date,
    COUNT(*) AS studies_processed
FROM imaging_studies
GROUP BY study_date
ORDER BY study_date;

-- This GROUP BY uses two columns, producing one count for every combination
-- of site and modality. ORDER BY makes the report easier to scan.
SELECT
    site,
    modality,
    COUNT(*) AS studies_processed
FROM imaging_studies
GROUP BY site, modality
ORDER BY site, modality;
