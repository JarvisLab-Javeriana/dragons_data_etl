# Available Flags — `news_extractor.py`

The scraper currently supports the following flags:

| Flag                     |                              Default value | Description                                                                                            |
| ------------------------ | -----------------------------------------: | ------------------------------------------------------------------------------------------------------ |
| `--whitelist`            |                               `white_list` | Root directory containing the whitelist CSV files.                                                     |
| `--database`             |        `MONGODB_DATABASE` or `dragons_app` | MongoDB database where news articles and audit records are stored.                                     |
| `--collection`           |             `MONGODB_COLLECTION` or `news` | MongoDB collection where news articles are stored.                                                     |
| `--audit-collection`     | `MONGODB_AUDIT_COLLECTION` or `audit_runs` | Collection where audit information for each execution is stored.                                       |
| `--audit-progress-every` |                                      `100` | Updates audit progress every N records. Use `0` to disable periodic checkpoints.                       |
| `--delay`                |                                      `2.5` | Minimum delay, in seconds, between requests to the same domain.                                        |
| `--timeout`              |                                       `20` | Timeout, in seconds, for article downloads and browser fallback operations.                            |
| `--robots-timeout`       |                                        `5` | Timeout, in seconds, for retrieving the `robots.txt` file.                                             |
| `--resume`               |                                   Disabled | Skips documents that already exist in MongoDB based on `eid + language + keywords`.                    |
| `--skip-empty-content`   |                                   Disabled | Prevents news articles from being stored in MongoDB when the `contenido` field could not be extracted. |

## Examples

### Standard execution

```bash
python news_extractor.py
```

### Resume execution without scraping existing documents again

```bash
python news_extractor.py --resume
```

### Do not store news articles without extracted content

```bash
python news_extractor.py --skip-empty-content
```

### Update audit progress every 10 records

```bash
python news_extractor.py --audit-progress-every 10
```

### Change the timeout values

```bash
python news_extractor.py --timeout 10 --robots-timeout 3
```

### Change the per-domain delay

```bash
python news_extractor.py --delay 1.5
```

### Use a different whitelist directory

```bash
python news_extractor.py --whitelist another_white_list
```

### Use a different MongoDB collection

```bash
python news_extractor.py --collection news_test
```

### Combine multiple flags

```bash
python news_extractor.py \
  --resume \
  --skip-empty-content \
  --audit-progress-every 10 \
  --timeout 10
```

## Running with Docker

Add the flags after the script command:

```bash
docker compose run --rm scraper \
  python news_extractor.py --resume
```

Complete example:

```bash
docker compose run --rm scraper \
  python news_extractor.py \
  --resume \
  --skip-empty-content \
  --audit-progress-every 10
```

## Displaying command-line help

To view all available options, run:

```bash
python news_extractor.py --help
```

Alternatively, using Docker:

```bash
docker compose run --rm scraper python news_extractor.py --help
```
