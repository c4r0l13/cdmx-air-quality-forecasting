-- Analytical questions answered in SQL. Each block starts with "-- name: <id>" and "-- q: <question>".
-- The runner (python -m airq.sql_report) executes them in order and writes reports/sql_answers.md.

-- name: overview
-- q: How much data is there, and what are the average levels?
SELECT COUNT(*)                     AS days,
       MIN(fecha)                   AS first_day,
       MAX(fecha)                   AS last_day,
       ROUND(AVG(pm25), 1)          AS avg_pm25,
       ROUND(AVG(pm10), 1)          AS avg_pm10,
       ROUND(AVG(o3), 1)            AS avg_o3_ppb,
       ROUND(AVG(no2), 1)           AS avg_no2_ppb
FROM daily;

-- name: who_exceedance_by_year
-- q: How many days per year exceeded the WHO 2021 PM2.5 24-hour guideline (15 µg/m³) and interim target 4 (25 µg/m³)?
SELECT year,
       COUNT(*)                                        AS days,
       SUM(pm25 > 15)                                  AS days_over_15,
       SUM(pm25 > 25)                                  AS days_over_25,
       ROUND(100.0 * SUM(pm25 > 25) / COUNT(*), 1)     AS pct_over_25
FROM daily
GROUP BY year
ORDER BY year;

-- name: seasonality
-- q: Which months are worst for particles and for ozone?
SELECT month,
       ROUND(AVG(pm25), 1) AS pm25,
       ROUND(AVG(pm10), 1) AS pm10,
       ROUND(AVG(o3), 1)   AS o3,
       ROUND(AVG(tmp), 1)  AS temp_c,
       ROUND(AVG(rh), 1)   AS humidity
FROM daily
GROUP BY month
ORDER BY month;

-- name: weekday
-- q: Is there a weekday effect from traffic (NO2, CO) and does ozone behave differently?
SELECT CASE weekday WHEN 0 THEN '0 Sun' WHEN 1 THEN '1 Mon' WHEN 2 THEN '2 Tue' WHEN 3 THEN '3 Wed'
                    WHEN 4 THEN '4 Thu' WHEN 5 THEN '5 Fri' ELSE '6 Sat' END AS day,
       ROUND(AVG(no2), 1) AS no2,
       ROUND(AVG(co), 3)  AS co,
       ROUND(AVG(o3), 1)  AS o3,
       ROUND(AVG(pm25), 1) AS pm25
FROM daily
GROUP BY weekday
ORDER BY weekday;

-- name: worst_days
-- q: What were the 10 worst PM2.5 days, and when did they happen?
SELECT fecha, ROUND(pm25, 1) AS pm25, ROUND(pm10, 1) AS pm10, ROUND(wsp, 2) AS wind_ms
FROM daily
ORDER BY pm25 DESC
LIMIT 10;

-- name: covid_lockdown
-- q: How much did traffic pollutants drop in April-May 2020 (lockdown) versus the same months in 2015-2019?
WITH base AS (
    SELECT AVG(no2) AS no2, AVG(co) AS co, AVG(pm25) AS pm25, AVG(o3) AS o3
    FROM daily WHERE month IN (4, 5) AND year BETWEEN 2015 AND 2019
), lock AS (
    SELECT AVG(no2) AS no2, AVG(co) AS co, AVG(pm25) AS pm25, AVG(o3) AS o3
    FROM daily WHERE month IN (4, 5) AND year = 2020
)
SELECT ROUND(100.0 * (lock.no2 - base.no2) / base.no2, 1)   AS no2_change_pct,
       ROUND(100.0 * (lock.co - base.co) / base.co, 1)      AS co_change_pct,
       ROUND(100.0 * (lock.pm25 - base.pm25) / base.pm25, 1) AS pm25_change_pct,
       ROUND(100.0 * (lock.o3 - base.o3) / base.o3, 1)      AS o3_change_pct
FROM base, lock;

-- name: wind
-- q: Does wind clean the air? Average PM2.5 by wind-speed quartile.
WITH q AS (
    SELECT pm25, wsp, NTILE(4) OVER (ORDER BY wsp) AS wind_quartile FROM daily
)
SELECT wind_quartile,
       ROUND(MIN(wsp), 2)  AS wind_from_ms,
       ROUND(MAX(wsp), 2)  AS wind_to_ms,
       ROUND(AVG(pm25), 1) AS pm25
FROM q
GROUP BY wind_quartile
ORDER BY wind_quartile;
