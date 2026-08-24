-- =============================================================================
-- yearly_count.sql
-- -----------------------------------------------------------------------------
-- Purpose: approximate row counts per year, used to characterize how much
-- data exists over time and to plan historical / stress experiments
-- (scripts/test_gdelt_history.py).
--
-- Filters on _PARTITIONTIME so BigQuery only scans the partitions inside the
-- requested range instead of the whole table (see docs/gdelt.md for why this
-- matters -- GKG is a very large, continuously growing table).
--
-- Scalar parameters:
--   @start_date  DATE  -- inclusive lower bound
--   @end_date    DATE  -- exclusive upper bound
-- Identifiers {project}/{dataset}/{table} are substituted in Python.
-- =============================================================================

SELECT
  EXTRACT(YEAR FROM _PARTITIONTIME) AS year,
  COUNT(*) AS approx_row_count
FROM
  `{project}.{dataset}.{table}`
WHERE
  _PARTITIONTIME >= @start_date
  AND _PARTITIONTIME < @end_date
GROUP BY
  year
ORDER BY
  year;
