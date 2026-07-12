-- Sample SQL queries for pharmacovigilance data
-- ================================================

-- 1. Total adverse events by drug
SELECT drug_name, COUNT(*) AS total_cases,
       SUM(is_serious) AS serious_cases,
       ROUND(SUM(is_serious) * 100.0 / COUNT(*), 1) AS serious_pct
FROM adverse_events
GROUP BY drug_name
ORDER BY total_cases DESC;

-- 2. Severity distribution
SELECT severity, COUNT(*) AS count,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM adverse_events), 1) AS pct
FROM adverse_events
GROUP BY severity
ORDER BY count DESC;

-- 3. Monthly trend of serious adverse events
SELECT STRFTIME('%Y-%m', report_date) AS month,
       COUNT(*) AS total_events,
       SUM(is_serious) AS serious_events
FROM adverse_events
WHERE report_date >= '2022-01-01'
GROUP BY month
ORDER BY month;

-- 4. Top adverse events by drug
SELECT drug_name, adverse_event, COUNT(*) AS cases
FROM adverse_events
GROUP BY drug_name, adverse_event
ORDER BY drug_name, cases DESC;

-- 5. Country-wise distribution
SELECT country, COUNT(*) AS total_cases,
       ROUND(AVG(time_to_onset_days), 1) AS avg_onset_days
FROM adverse_events
GROUP BY country
ORDER BY total_cases DESC;

-- 6. Age group analysis
SELECT patient_age_group, severity, COUNT(*) AS cases
FROM adverse_events
GROUP BY patient_age_group, severity
ORDER BY patient_age_group;

-- 7. Reporter type breakdown
SELECT reporter_type, COUNT(*) AS count,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM adverse_events), 1) AS pct
FROM adverse_events
GROUP BY reporter_type
ORDER BY count DESC;

-- 8. Outcome analysis
SELECT drug_name, outcome, COUNT(*) AS cases
FROM adverse_events
WHERE outcome IN ('Fatal', 'Life-threatening', 'Not Recovered')
GROUP BY drug_name, outcome
ORDER BY cases DESC;
