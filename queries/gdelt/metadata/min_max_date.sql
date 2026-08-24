SELECT
  MIN(DATE) AS min_date,
  MAX(DATE) AS max_date,
  COUNT(*)  AS total_rows_scanned_for_bounds
FROM
  `{project}.{dataset}.{table}`;