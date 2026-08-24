-- =============================================================================
-- keyword_count.sql
-- -----------------------------------------------------------------------------
-- Purpose: cheaply experiment with keywords by counting matching GKG rows
-- WITHOUT downloading the full documents. Useful to estimate result-set size
-- before running extraction/articles.sql with the same filters.
--
-- Matches against V2Themes, V2Persons, V2Organizations and the raw
-- V2Tone-adjacent text fields is deliberately avoided here (kept in
-- extraction where full row detail is needed); this query focuses on
-- V2Themes + V2Persons + V2Organizations, which is where most topical
-- keyword matching happens in GKG.
--
-- Scalar parameters:
--   @start_date  DATE          -- inclusive lower bound
--   @end_date    DATE          -- exclusive upper bound
--   @keywords    ARRAY<STRING> -- case-insensitive substrings to match
-- Identifiers {project}/{dataset}/{table} are substituted in Python.
-- =============================================================================

SELECT
  COUNT(*) AS matching_row_count
FROM
  `{project}.{dataset}.{table}`
WHERE
  _PARTITIONTIME >= @start_date
  AND _PARTITIONTIME < @end_date
  AND EXISTS (
    SELECT 1
    FROM UNNEST(@keywords) AS kw
    WHERE
      LOWER(IFNULL(V2Themes, '')) LIKE CONCAT('%', LOWER(kw), '%')
      OR LOWER(IFNULL(V2Persons, '')) LIKE CONCAT('%', LOWER(kw), '%')
      OR LOWER(IFNULL(V2Organizations, '')) LIKE CONCAT('%', LOWER(kw), '%')
  );
