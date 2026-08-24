SELECT
  table_name,
  table_type,
  creation_time
FROM
  `{project}.{dataset}.INFORMATION_SCHEMA.TABLES`
ORDER BY
  table_name;