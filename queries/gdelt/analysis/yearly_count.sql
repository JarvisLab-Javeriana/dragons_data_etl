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
