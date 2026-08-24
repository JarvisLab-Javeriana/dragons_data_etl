SELECT
  column_name,
  data_type,
  is_nullable,
  ordinal_position
FROM
  `{project}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
WHERE
  table_name = @table_name
ORDER BY
  ordinal_position;
