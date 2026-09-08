# Banderas disponibles — `news_extractor.py`

El scraper soporta actualmente las siguientes banderas:

| Bandera | Valor por defecto | Descripción |
|---|---:|---|
| `--whitelist` | `white_list` | Carpeta raíz donde están los CSV de la whitelist. |
| `--database` | `MONGODB_DATABASE` o `dragons_app` | Base de datos de MongoDB donde se guardan las noticias y auditorías. |
| `--collection` | `MONGODB_COLLECTION` o `news` | Colección de MongoDB donde se guardan las noticias. |
| `--audit-collection` | `MONGODB_AUDIT_COLLECTION` o `audit_runs` | Colección donde se guardan las auditorías de cada ejecución. |
| `--audit-progress-every` | `100` | Actualiza el progreso de la auditoría cada N registros. Usa `0` para desactivar los checkpoints periódicos. |
| `--delay` | `2.5` | Tiempo mínimo, en segundos, entre solicitudes al mismo dominio. |
| `--timeout` | `20` | Timeout, en segundos, para la descarga del artículo y el fallback con navegador. |
| `--robots-timeout` | `5` | Timeout, en segundos, para consultar `robots.txt`. |
| `--resume` | desactivado | Salta documentos que ya existen en MongoDB según `eid + language + keywords`. |
| `--skip-empty-content` | desactivado | No guarda en MongoDB noticias cuyo campo `contenido` no pudo ser extraído. |

## Ejemplos

### Ejecución normal

```bash
python news_extractor.py
```

### Continuar sin volver a scrapear documentos existentes

```bash
python news_extractor.py --resume
```

### No guardar noticias sin contenido

```bash
python news_extractor.py --skip-empty-content
```

### Actualizar la auditoría cada 10 registros

```bash
python news_extractor.py --audit-progress-every 10
```

### Cambiar timeouts

```bash
python news_extractor.py --timeout 10 --robots-timeout 3
```

### Cambiar el delay por dominio

```bash
python news_extractor.py --delay 1.5
```

### Usar otra whitelist

```bash
python news_extractor.py --whitelist otra_white_list
```

### Usar otra colección

```bash
python news_extractor.py --collection news_test
```

### Combinar banderas

```bash
python news_extractor.py \
  --resume \
  --skip-empty-content \
  --audit-progress-every 10 \
  --timeout 10
```

## Con Docker

Solo se agregan las banderas después del comando del script:

```bash
docker compose run --rm scraper \
  python news_extractor.py --resume
```

Ejemplo completo:

```bash
docker compose run --rm scraper \
  python news_extractor.py \
  --resume \
  --skip-empty-content \
  --audit-progress-every 10
```

## Ver ayuda desde terminal

Puedes consultar todas las opciones disponibles con:

```bash
python news_extractor.py --help
```

o usando Docker:

```bash
docker compose run --rm scraper python news_extractor.py --help
```
