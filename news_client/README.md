# Cliente de consultas (GDELT / BigQuery)

CLI para buscar noticias con palabras clave, etiquetas, idiomas (`en`, `es`, `hu`), medios, fechas y `--limit`.

Consulta **BigQuery** (`gdelt-bq.gdeltv2.gkg_partitioned`). **No usa la API pública** de GDELT, así no aparece el error HTTP 429.

## Credenciales (JSON)

Hace falta una cuenta de servicio de Google Cloud con BigQuery habilitado. El archivo `.json` **no se sube al git**. Páselo a su compañero por un canal privado (Drive interno, correo, etc.).

**Opción A — argumento**

```text
.venv\Scripts\python.exe news_client/client.py --credentials "C:\Users\vivgo\Downloads\dragons-data-etl-e4c3aa1016a0.json" --keywords "biodiversity" --start-date 2024-01-01 --end-date 2024-01-31 --limit 10
```

**Opción B — variable de entorno (PowerShell)**

```text
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\Users\vivgo\Downloads\dragons-data-etl-e4c3aa1016a0.json"
.venv\Scripts\python.exe news_client/client.py --keywords "biodiversity,conservation" --tags "environment" --languages "en,es,hu" --media "reuters,bbc" --start-date "2024-01-01" --end-date "2024-01-31" --limit 100
```

Use el Python del `.venv` del repo (incluye `google-cloud-bigquery`). En PowerShell el comando va en **una sola línea**.

Los resultados quedan en `results.json`. `--languages` se aplica en SQL (inglés = sin traducción o `srclc:eng`; español `srclc:spa`; húngaro `srclc:hun`).
