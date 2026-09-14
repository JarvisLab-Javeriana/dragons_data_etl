# News Query Client (GDELT / BigQuery)

A command-line interface (CLI) for searching news articles using keywords, tags, languages (`en`, `es`, `hu`), media outlets, date ranges, and the `--limit` option.

The client queries **BigQuery directly**. It **does not use the public GDELT API**, thereby avoiding HTTP 429 rate-limit errors.

## Credentials (JSON)

A Google Cloud service account `.json` file is required.

> **Security warning:** Do not upload or commit this file to Git. Share it only through a secure private channel.

The path `C:\path\...` shown in previous messages was only an **example**. You must use the actual path to the credentials file, for example:

```text
C:\Users\vivgo\Downloads\dragons-data-etl-e4c3aa1016a0.json
```

## How to Run the Client

### 1. Open PowerShell

Open **PowerShell** and verify that the prompt begins with something similar to:

```text
PS C:\Users\...>
```

If the prompt appears without `PS`, for example:

```text
C:\Users\...>
```

you are using `cmd.exe`. In that case, do not use the `$env:` syntax.

### 2. Open the Cloned Repository

Navigate to the cloned repository directory using `cd` until you reach the `dragons_data_etl` folder.

Example:

```powershell
cd C:\path\to\dragons_data_etl
```

### 3. Create the Virtual Environment and Install Dependencies

Run these commands only once:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install google-cloud-bigquery python-dotenv PyYAML pymongo certifi
```

## Recommended Method: Use `--credentials`

The simplest option is to provide the service account JSON file directly through the `--credentials` argument. This method does not require an environment variable.

Run the following command in **PowerShell as a single line**:

```powershell
.venv\Scripts\python.exe news_client\client.py --credentials "C:\Users\vivgo\Downloads\dragons-data-etl-e4c3aa1016a0.json" --keywords "biodiversity" --start-date 2024-01-01 --end-date 2024-01-31 --limit 10
```

Replace the credentials path with the actual location of your service account JSON file.

## Alternative Method: Use an Environment Variable

### PowerShell

Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable:

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = "C:\Users\vivgo\Downloads\dragons-data-etl-e4c3aa1016a0.json"
```

Then run the client:

```powershell
.venv\Scripts\python.exe news_client\client.py --keywords "biodiversity" --start-date 2024-01-01 --end-date 2024-01-31 --limit 10
```

The environment variable applies only to the current PowerShell session unless it is configured permanently.

### Command Prompt (`cmd.exe`)

If your prompt does not begin with `PS`, use the following commands:

```cmd
set GOOGLE_APPLICATION_CREDENTIALS=C:\Users\vivgo\Downloads\dragons-data-etl-e4c3aa1016a0.json
.venv\Scripts\python.exe news_client\client.py --keywords biodiversity --start-date 2024-01-01 --end-date 2024-01-31 --limit 10
```

## Output

The query results are saved to:

```text
results.json
```

## Query Behavior and GDELT Tags

The MongoDB pipeline searches using only **keywords and dates**. For example, it searches for `biodiversity` in GDELT GKG topics such as:

```text
ENV_BIODIVERSITY
```

Previously, when the client received `--tags environment`, it returned no results because GDELT does not use the literal word `environment` as the corresponding tag prefix.

The client now translates:

```text
environment → env
```

This allows it to match GDELT topics beginning with:

```text
ENV_*
```

If all three supported languages (`en`, `es`, and `hu`) are requested, the client does **not** filter by `TranslationInfo`. This behavior is consistent with the MongoDB pipeline.

## Test Equivalent to the ETL Query

To run a test equivalent to the ETL process, execute the following command in PowerShell as a single line:

```powershell
.venv\Scripts\python.exe news_client\client.py --credentials "C:\Users\vivgo\Downloads\dragons-data-etl-e4c3aa1016a0.json" --keywords "biodiversity" --start-date 2015-02-01 --end-date 2026-06-30 --limit 100
```

Before running it, replace the example credentials path with the actual path to your service account JSON file.
