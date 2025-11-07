-- Get only the necessary columns from the OECD table with the hours worked per year

CREATE TABLE OECD_hours AS
SELECT ref_area AS country_code, `reference area` AS country, time_period AS year, obs_value AS hours_worked
FROM oecd_hours_worked;


-- Allign country name

UPDATE oecd_hours 
SET country = 'Slovakia' WHERE country = 'Slovak Republic';


-- Fix the values in the column hours_worked so they are integer and in the same format

UPDATE oecd_hours 
SET hours_worked = REPLACE(REPLACE(hours_worked, '.', ''), ',', '.');

ALTER TABLE oecd_hours 
ADD COLUMN hours INT;

SELECT
  hours_worked AS original,
  LENGTH(hours_worked) AS len,
  ROUND(CAST(hours_worked AS DECIMAL(20,6)) / POW(10, GREATEST(LENGTH(hours_worked) - 4, 0))) AS four_digit_rounded
FROM oecd_hours
ORDER BY len ASC, original
LIMIT 100;

UPDATE oecd_hours
SET hours = LEAST(
  9999,
  CAST(
    ROUND(
      CAST(hours_worked AS DECIMAL(20,6)) / POW(10, GREATEST(LENGTH(hours_worked) - 4, 0))
    ) AS UNSIGNED
  )
)
WHERE hours_worked REGEXP '^[0-9]+$' AND hours_worked IS NOT NULL AND hours_worked <> '';


-- Get only the necessary columns from the OECD table with the average annual wage

CREATE TABLE oecd_wages AS
SELECT ref_area AS country_code, `reference area` AS country, unit_measure, `price base`, obs_value AS avg_wage, time_period AS YEAR
FROM oecd_annual_average_wages;


UPDATE oecd_wages 
SET country = 'Slovakia' WHERE country = 'Slovak Republic';


-- Keep only the rows with constant prices

delete FROM oecd_wages
WHERE `price base` = 'current prices';


-- Allign country name


-- Keep only the European countries
DELETE FROM oecd_wages  
WHERE country IN (
	SELECT country 
	FROM (
		SELECT country 
		FROM oecd_wages
		WHERE country NOT IN (
			SELECT country 
			FROM the_countries
			WHERE continent = 'Europe'
		) 
		AND country NOT IN ('turkey', 'oecd')
	) AS sub
);


-- Keep only the rows where the wages are calculated in us dollars, adjusted for inflation (where available)

DELETE FROM oecd_wages 
WHERE unit_measure != 'usd_ppp'
AND country NOT IN ('Bulgaria', 'Romania', 'Croatia');


-- Fix the values in the avg_wage column so they all have the same format

ALTER TABLE oecd_wages ADD COLUMN avg_wage_int INT UNSIGNED;

UPDATE oecd_wages
SET avg_wage_int = CASE
  WHEN country_code = 'BGR'
       AND unit_measure = 'BGN'
       AND `price base` = 'Constant prices'
       AND `YEAR` IN (2000, 2001, 2002, 2003, 2004)
  THEN
    -- 4-digit rounded
    LEAST(
      9999,
      CAST(
        ROUND(
          CAST(REPLACE(TRIM(avg_wage), '.', '') AS DECIMAL(20,0))
          / POW(10, GREATEST(LENGTH(REPLACE(TRIM(avg_wage), '.', '')) - 4, 0))
        ) AS UNSIGNED
      )
    )
  ELSE
    -- 5-digit rounded
    LEAST(
      99999,
      CAST(
        ROUND(
          CAST(REPLACE(TRIM(avg_wage), '.', '') AS DECIMAL(20,0))
          / POW(10, GREATEST(LENGTH(REPLACE(TRIM(avg_wage), '.', '')) - 5, 0))
        ) AS UNSIGNED
      )
    )
END
WHERE avg_wage REGEXP '^[0-9.]+$' AND avg_wage IS NOT NULL AND avg_wage <> '';



-- Create table with average wage per hour worked column

CREATE TABLE oecd_hourly_wage AS
SELECT w.country, w.year, w.avg_wage_int AS avg_wage, h.hours, round((w.avg_wage_int / h.hours), 1) AS hourly_wage
FROM oecd_wages w 
inner JOIN oecd_hours h
ON w.country = h.country
AND w.YEAR = h.YEAR;

-- Create table with change in real wage per hour worked column

CREATE TABLE oecd_hw_change as
SELECT
  country,
  MAX(CASE WHEN year = 2000 THEN hourly_wage END) AS hw_2000,
  MAX(CASE WHEN year = 2007 THEN hourly_wage END) AS hw_2007,
  MAX(CASE WHEN year = 2008 THEN hourly_wage END) AS hw_2008,
  MAX(CASE WHEN year = 2010 THEN hourly_wage END) AS hw_2010,
  MAX(CASE WHEN year = 2014 THEN hourly_wage END) AS hw_2014,
  MAX(CASE WHEN year = 2024 THEN hourly_wage END) AS hw_2024,
  CASE
    WHEN MAX(CASE WHEN year = 2000 THEN hourly_wage END) IS NULL
         OR MAX(CASE WHEN year = 2000 THEN hourly_wage END) = 0
         OR MAX(CASE WHEN year = 2024 THEN hourly_wage END) IS NULL
    THEN NULL
    ELSE ROUND(
      (MAX(CASE WHEN year = 2024 THEN hourly_wage END)
       - MAX(CASE WHEN year = 2000 THEN hourly_wage END))
      / MAX(CASE WHEN year = 2000 THEN hourly_wage END) * 100, 2)
  END AS pct_change_2000_2024,
    CASE
    WHEN MAX(CASE WHEN year = 2007 THEN hourly_wage END) IS NULL
         OR MAX(CASE WHEN year = 2007 THEN hourly_wage END) = 0
         OR MAX(CASE WHEN year = 2024 THEN hourly_wage END) IS NULL
    THEN NULL
    ELSE ROUND(
      (MAX(CASE WHEN year = 2024 THEN hourly_wage END)
       - MAX(CASE WHEN year = 2007 THEN hourly_wage END))
      / MAX(CASE WHEN year = 2007 THEN hourly_wage END) * 100, 2)
  END AS pct_change_2007_2024,
   CASE
    WHEN MAX(CASE WHEN year = 2008 THEN hourly_wage END) IS NULL
         OR MAX(CASE WHEN year = 2008 THEN hourly_wage END) = 0
         OR MAX(CASE WHEN year = 2024 THEN hourly_wage END) IS NULL
    THEN NULL
    ELSE ROUND(
      (MAX(CASE WHEN year = 2024 THEN hourly_wage END)
       - MAX(CASE WHEN year = 2008 THEN hourly_wage END))
      / MAX(CASE WHEN year = 2008 THEN hourly_wage END) * 100, 2)
  END AS pct_change_2008_2024,
  CASE
    WHEN MAX(CASE WHEN year = 2010 THEN hourly_wage END) IS NULL
         OR MAX(CASE WHEN year = 2010 THEN hourly_wage END) = 0
         OR MAX(CASE WHEN year = 2024 THEN hourly_wage END) IS NULL
    THEN NULL
    ELSE ROUND(
      (MAX(CASE WHEN year = 2024 THEN hourly_wage END)
       - MAX(CASE WHEN year = 2010 THEN hourly_wage END))
      / MAX(CASE WHEN year = 2010 THEN hourly_wage END) * 100, 2)
  END AS pct_change_2010_2024,
  CASE
    WHEN MAX(CASE WHEN year = 2014 THEN hourly_wage END) IS NULL
         OR MAX(CASE WHEN year = 2014 THEN hourly_wage END) = 0
         OR MAX(CASE WHEN year = 2024 THEN hourly_wage END) IS NULL
    THEN NULL
    ELSE ROUND(
      (MAX(CASE WHEN year = 2024 THEN hourly_wage END)
       - MAX(CASE WHEN year = 2014 THEN hourly_wage END))
      / MAX(CASE WHEN year = 2014 THEN hourly_wage END) * 100, 2)
  END AS pct_change_2014_2024
FROM oecd_hourly_wage
GROUP BY country
ORDER BY country;

-- Create aditional table with the rankings of real hourly wages of countries in certain years
-- and the difference in rankings in certain periods 

CREATE TABLE oecd_hw_change_with_pr AS
SELECT
    *,
    ROUND(PERCENT_RANK() OVER (ORDER BY hw_2000), 3) AS pr_2000,
    ROUND(PERCENT_RANK() OVER (ORDER BY hw_2007), 3) AS pr_2007,
    ROUND(PERCENT_RANK() OVER (ORDER BY hw_2024), 3) AS pr_2024,
    ROUND((PERCENT_RANK() OVER (ORDER BY hw_2024) -
           PERCENT_RANK() OVER (ORDER BY hw_2000)) * 100, 2) AS pr_change_2000_2024,
    ROUND((PERCENT_RANK() OVER (ORDER BY hw_2024) -
           PERCENT_RANK() OVER (ORDER BY hw_2007)) * 100, 2) AS pr_change_2007_2024
FROM oecd_hw_change
WHERE hw_2000 IS NOT NULL AND hw_2007 IS NOT NULL AND hw_2024 IS NOT NULL;



