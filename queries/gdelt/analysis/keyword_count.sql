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
