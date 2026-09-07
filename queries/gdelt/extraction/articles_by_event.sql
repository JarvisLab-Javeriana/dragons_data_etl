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
  V2Tone,
  TranslationInfo
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
      OR LOWER(IFNULL(DocumentIdentifier, '')) LIKE CONCAT('%', LOWER(kw), '%')
  )
  AND (
    @apply_locations IS FALSE
    OR EXISTS (
      SELECT 1
      FROM UNNEST(@locations) AS loc
      WHERE LOWER(IFNULL(V2Locations, '')) LIKE CONCAT('%', LOWER(loc), '%')
    )
  )
ORDER BY
  DATE
LIMIT
  @row_limit;
