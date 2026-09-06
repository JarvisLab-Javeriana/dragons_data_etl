# Cliente de consultas (GDELT / BigQuery)

CLI para buscar noticias con palabras clave, etiquetas, idiomas (`en`, `es`, `hu`), medios, fechas y `--limit`.

Consulta **BigQuery**. **No usa la API pública** de GDELT (evita HTTP 429).

## Credenciales (JSON)

Hace falta el archivo `.json` de la cuenta de servicio. **No se sube al git.** Páselo por un canal privado.

`C:\ruta\...` en mensajes anteriores era un **ejemplo**. Debe ser la ruta real del archivo, por ejemplo:

`C:\Users\vivgo\Downloads\dragons-data-etl-e4c3aa1016a0.json`

## Cómo ejecutarlo

1. Abra **PowerShell** (el prompt debe empezar por `PS C:\...>`). Si ve `C:\Users\...>` sin `PS`, es cmd: no use `$env:`.
2. Entre a la carpeta del repo clonado (`cd` hasta `dragons_data_etl`).
3. Cree el entorno e instale dependencias **una vez**:

```text
python -m venv .venv
.venv\Scripts\python.exe -m pip install google-cloud-bigquery python-dotenv PyYAML pymongo certifi
```

**Forma más simple (sin variable de entorno):** pase el JSON con `--credentials`.

PowerShell, **una sola línea**:

```text
.venv\Scripts\python.exe news_client\client.py --credentials "C:\Users\vivgo\Downloads\dragons-data-etl-e4c3aa1016a0.json" --keywords "biodiversity" --start-date 2024-01-01 --end-date 2024-01-31 --limit 10
```

Si prefiere la variable, **solo en PowerShell**:

```text
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\Users\vivgo\Downloads\dragons-data-etl-e4c3aa1016a0.json"
```

En **cmd.exe** (sin `PS`):

```text
set GOOGLE_APPLICATION_CREDENTIALS=C:\Users\vivgo\Downloads\dragons-data-etl-e4c3aa1016a0.json
.venv\Scripts\python.exe news_client\client.py --keywords biodiversity --start-date 2024-01-01 --end-date 2024-01-31 --limit 10
```

Los resultados quedan en `results.json`.
