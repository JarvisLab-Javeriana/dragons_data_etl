# Cliente de consultas (GDELT)

CLI para buscar noticias con palabras clave, etiquetas, idiomas (`en`, `es`, `hu`), medios, fechas y `--limit`. Usa la API pública de GDELT: Python 3.10+ e internet, sin instalar paquetes ni configurar claves.

## Cómo ejecutarlo

En PowerShell, una sola línea (no uses `\` para partir el comando).

Desde esta carpeta:

```text
python client.py --help
```

```text
python client.py --keywords "biodiversity,conservation" --tags "environment" --languages "en,es,hu" --media "reuters,bbc" --start-date "2026-08-01" --end-date "2026-08-31" --limit 10
```

Desde la raíz del repositorio:

```text
python news_client/client.py --keywords "biodiversity" --start-date "2026-08-01" --end-date "2026-08-31" --limit 10
```

Los resultados se guardan en `results.json` (cámbielo con `--output`). `--limit` por defecto es 100 (máximo 250).

Prueba rápida: `--limit 10`. Solo español: `--languages es`.
