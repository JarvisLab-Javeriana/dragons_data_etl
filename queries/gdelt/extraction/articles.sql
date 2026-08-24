SELECT
  GKGRECORDID,
  DATE,
  SourceCollectionIdentifier,
  DocumentIdentifier,
  V1Counts,
  V2Counts,
  V1Themes,
  V2Themes,
  V1Locations,
  V2Locations,
  V1Persons,
  V2Persons,
  V1Organizations,
  V2Organizations,
  V1Tone,
  V2Tone,
  GCAM,
  AllNames,
  Amounts,
  TranslationInfo,
  Extras
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
  )
ORDER BY
  DATE
LIMIT
  @row_limit;
