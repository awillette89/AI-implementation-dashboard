-- Turnaround time by algorithm. Product names are real, ALL statistics are mock.
-- Each study has at most one assigned algorithm, keeping the table simple.
-- WHERE includes only studies where AI processing was attempted.
-- GROUP BY calculates separate statistics for each vendor/algorithm pair.
-- Successful results supply AI processing TAT. Errors have no result time,
-- so AVG ignores those NULL durations instead of counting them as zero.
-- Study TAT includes all attempted studies, including errors.
-- julianday subtracts timestamps in days. Multiply by 1440 for minutes.
-- ROUND(..., 1) keeps one decimal place. Counts show each average's sample size.
SELECT
    algorithm_vendor,
    algorithm_name,
    COUNT(*) AS ai_processed_studies,
    SUM(CASE WHEN ai_result_available = 1 THEN 1 ELSE 0 END) AS successful_results,
    SUM(CASE WHEN ai_error = 1 THEN 1 ELSE 0 END) AS ai_errors,
    ROUND(AVG(CASE WHEN ai_result_available = 1 THEN
        (julianday(ai_result_time) - julianday(ai_start_time)) * 1440
        END), 1) AS avg_ai_processing_minutes,
    ROUND(AVG(
        (julianday(study_complete_time) - julianday(study_start_time)) * 1440
        ), 1) AS avg_study_turnaround_minutes
FROM imaging_studies
WHERE ai_processed = 1 AND algorithm_name IS NOT NULL
GROUP BY algorithm_vendor, algorithm_name
ORDER BY algorithm_vendor, algorithm_name;
