SELECT
  GKGRECORDID,
  DATE,
  SourceCollectionIdentifier,
  SourceCommonName,
  DocumentIdentifier,
  V2Themes,
  V2Locations,
  V2Persons,
  V2Organizations,
  V2Tone
FROM
  `{project}.{dataset}.{table}`
WHERE
  _PARTITIONTIME >= TIMESTAMP(@start_date)
  AND _PARTITIONTIME < TIMESTAMP(@end_date)
  AND EXISTS (
    SELECT 1
    FROM UNNEST(@keywords) AS kw
    WHERE
      LOWER(IFNULL(V2Themes, '')) LIKE CONCAT('%', LOWER(kw), '%')
      OR LOWER(IFNULL(V2Persons, '')) LIKE CONCAT('%', LOWER(kw), '%')
      OR LOWER(IFNULL(V2Organizations, '')) LIKE CONCAT('%', LOWER(kw), '%')
  )
ORDER BY
  DATE
LIMIT
  @row_limit;
