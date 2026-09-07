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
  )
  AND (
    @apply_tags IS FALSE
    OR EXISTS (
      SELECT 1
      FROM UNNEST(@tags) AS tag
      WHERE LOWER(IFNULL(V2Themes, '')) LIKE CONCAT('%', LOWER(tag), '%')
    )
  )
  AND (
    @apply_media IS FALSE
    OR EXISTS (
      SELECT 1
      FROM UNNEST(@media) AS outlet
      WHERE
        LOWER(IFNULL(SourceCommonName, '')) LIKE CONCAT('%', LOWER(outlet), '%')
        OR LOWER(IFNULL(DocumentIdentifier, '')) LIKE CONCAT('%', LOWER(outlet), '%')
    )
  )
  AND (
    @apply_languages IS FALSE
    OR EXISTS (
      SELECT 1
      FROM UNNEST(@languages) AS lang
      WHERE
        (
          lang = 'en'
          AND (
            TranslationInfo IS NULL
            OR TRIM(CAST(TranslationInfo AS STRING)) = ''
            OR LOWER(CAST(TranslationInfo AS STRING)) LIKE '%srclc:eng%'
          )
        )
        OR (
          lang = 'es'
          AND LOWER(IFNULL(CAST(TranslationInfo AS STRING), '')) LIKE '%srclc:spa%'
        )
        OR (
          lang = 'hu'
          AND LOWER(IFNULL(CAST(TranslationInfo AS STRING), '')) LIKE '%srclc:hun%'
        )
    )
  )
ORDER BY
  DATE
LIMIT
  @row_limit;
