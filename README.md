# 🐉 DRAGONS Data ETL

### Data Engineering Component of the DRAGONS Project

- **Project:** DRAGONS – *Diffusing biodiversity Response-able Action and awareness raising through citizen empowerment, inclusive engagement and innovative Governance of Nature and Society*
- **Work Package:** WP1 – Understanding societal perceptions, awareness, and engagement responses to biodiversity loss
- **Institution:** Pontificia Universidad Javeriana
- **Related Repository:** `dragons-data-analytics`

---

## Objective

Develop the data engineering component responsible for collecting, transforming, validating, and storing information obtained from public or authorised online sources, including social media, news outlets, and other permitted data acquisition mechanisms.

The main objective is to build a reproducible data workflow capable of consolidating textual content and metadata into a MongoDB document database, ensuring traceability, data quality, and availability for subsequent use by the `dragons-data-analytics` repository.

---

## Project Team

### Project Leadership

Responsible for jointly guiding the technical, analytical, scientific, and domain strategy of the component, ensuring alignment between data engineering, analytics, and the biodiversity research objectives.

**Members:**

- **PhD Luis Gabriel Moreno Sandoval**  
  **Technical & Data Analytics Lead**  
  Section Head and Faculty Member, Department of Systems Engineering  
  Pontificia Universidad Javeriana  

  Responsible for the technical and methodological direction of the data component, architecture definition, analytics and artificial intelligence strategy, technical oversight, and validation of engineering and analytical deliverables.  
  📧 [morenoluis@javeriana.edu.co](mailto:morenoluis@javeriana.edu.co)

- **PhD Juan David Amaya Espinel**  
  **Biodiversity Research & Domain Lead**  
  Associate Professor, Department of Ecology and Territory  
  Pontificia Universidad Javeriana  

  Responsible for the scientific and thematic leadership of the biodiversity component. He guides the definition of research questions, conceptual criteria for source selection and evaluation, and the interpretation of results from the biodiversity domain perspective.  
  📧 [jamayae@javeriana.edu.co](mailto:jamayae@javeriana.edu.co)

---

### Project Coordination

Responsible for coordinating the execution of the ETL component across technical and domain workstreams, connecting data acquisition and processing requirements with the scientific criteria of the biodiversity research component.

**Members:**

- **Juan Pablo Arias Buitrago**  
  **Data Scientist & Technical Project Coordinator**  

  Responsible for the operational and technical coordination of the project, activity and deliverable tracking, integration between `dragons-data-etl` and `dragons-data-analytics`, definition of data requirements, monitoring of acquisition, transformation, and quality processes, and validation that ETL outputs can support the analytical dataset and downstream analysis.  
  📧 [ariasj.u@javeriana.edu.co](mailto:ariasj.u@javeriana.edu.co)

- **Pabla Lozano Ramírez**  
  **Biodiversity Domain Lead & Research Project Coordinator**  

  Responsible for the scientific and thematic coordination of the ETL component, supporting the definition and validation of data sources, search terms and queries, content-selection criteria, and thematic relevance of the collected corpus. She also contributes to the thematic quality review of the data and validates that acquired sources and records remain aligned with the biodiversity research objectives.  
  📧 [pabla-lozano@javeriana.edu.co](mailto:pabla-lozano@javeriana.edu.co)

---

### Data Science and Analytical Validation

Responsible for supporting the definition of analytical data requirements and ensuring that the information produced by the ETL component is suitable for downstream analytics.

**Member:**

- **Sergio Pardo Hurtado**  
  **NLP Data Scientist & Lead Data Analyst**  

  Participates in the ETL component from the analytical perspective, supporting the definition of fields, variables, and data-quality criteria required for downstream analysis. He also contributes to validating that the collected and transformed data are suitable for the analytical dataset, statistical analysis, NLP, and artificial intelligence processes.  
  📧 [sergio_pardo@javeriana.edu.co](mailto:sergio_pardo@javeriana.edu.co)

---

### Data Engineering and Platform Team

Responsible for developing the acquisition, transformation, validation, storage, and infrastructure components supporting the ETL workflow.

**Members:**

- **Viviana Gómez León**  
  **Data Engineer & Platform Developer**  

  Responsible for developing source connectors, integrating external data sources, implementing extraction and transformation processes, persisting data in MongoDB, supporting communication between components, and contributing to the data platform implementation.  
  📧 [gomezlv@javeriana.edu.co](mailto:gomezlv@javeriana.edu.co)

- **Marlon Jhoan Garcia Restrepo**  
  **Data Engineer & DevOps Engineer**  

  Responsible for developing and maintaining ETL pipelines, data-quality and storage components, automation, environment configuration, containerisation, continuous integration, deployment, and technical infrastructure support.  
  📧 [mjgarcia@javeriana.edu.co](mailto:mjgarcia@javeriana.edu.co)

---

## General Workflow

```text
Public and authorised sources
             │
             ▼
       Data acquisition
             │
             ▼
          Validation
             │
             ▼
   Cleaning and normalisation
             │
             ▼
       Data quality
             │
             ▼
           MongoDB
             │
             ▼
    dragons-data-analytics
```

---

## Core Technologies

* **Programming language:** Python
* **Database:** MongoDB
* **Integration:** REST APIs, RSS feeds, and external data services
* **Containers:** Docker
* **Version control:** Git / GitHub

---

## Project Structure

The current repository structure is organised as follows:

```text
dragons_data_etl/
│
├── config/
│   ├── settings/
│   │   ├── logging.yaml          # Logging configuration
│   │   ├── mongodb.yaml          # MongoDB connection and persistence settings
│   │   └── pipeline.yaml         # General ETL pipeline configuration
│   │
│   └── sources/
│       ├── crawler.yaml          # Web crawling source configuration
│       ├── gdelt.yaml            # GDELT source configuration
│       ├── newspapers.yaml       # Newspaper source definitions
│       └── social_media.yaml     # Social media source definitions
│
├── data/
│   ├── events/
│   │   └── DRAGONS_T1.1_Biodiversity_events_2016-2026_v2.xlsx
│   │                              # Biodiversity events used as temporal/contextual references
│   │
│   ├── samples/                   # Small reproducible samples for validation and inspection
│   │
│   └── DRAGONS T1_1_1_DA_Keywords_Methodology.xlsx
│                                  # Keyword and search methodology reference
│
├── gdelt/
│   ├── logs/
│   │   └── dragons_data_etl.log  # GDELT-specific execution log
│   │
│   └── scripts/
│       └── test_gdelt_history.py # Historical GDELT extraction experiment
│
├── logs/
│   ├── dragons_data_etl.crawled_data.csv
│   │                              # Results from web content retrieval attempts
│   ├── dragons_data_etl.execution_metrics.csv
│   │                              # Pipeline execution and performance metrics
│   ├── dragons_data_etl.gkg_records.csv
│   │                              # Exported GDELT GKG sample records
│   └── dragons_data_etl.log      # General ETL execution log
│
├── news_client/
│   ├── README.md                 # News client documentation
│   ├── client.py                 # News retrieval client implementation
│   └── test_client.py            # News client tests
│
├── queries/
│   └── gdelt/
│       ├── analysis/
│       │   ├── keyword_count.sql # Keyword-level analytical queries
│       │   └── yearly_count.sql  # Temporal aggregation by year
│       │
│       ├── extraction/
│       │   ├── articles.sql
│       │   ├── articles_by_event.sql
│       │   └── articles_client.sql
│       │                          # Queries used to retrieve GDELT records
│       │
│       └── metadata/
│           ├── columns.sql
│           ├── min_max_date.sql
│           └── tables.sql
│                                  # Metadata inspection queries
│
├── scripts/
│   ├── gdelt/
│   │   └── test_gdelt_history.py # GDELT historical extraction testing
│   │
│   ├── mediacloud/
│   │   └── Mediacloud_export.ipynb
│   │                              # MediaCloud news consolidation and exploratory analysis
│   │
│   ├── export_mongo_sample.py    # Export MongoDB samples for inspection
│   ├── run_crawler.py            # Execute the web crawler
│   ├── run_gdelt.py              # Execute GDELT acquisition workflow
│   ├── seed_events.py            # Load biodiversity events into the processing workflow
│   └── test_gdelt_history.py     # Historical GDELT test script
│
├── src/                          # Core ETL implementation
│
├── tests/                        # Unit and integration tests
│
├── .env.example                  # Example environment variables
├── LICENSE
└── README.md
```
### `config/`

Contains general configuration required by the ETL processes, including source-specific settings and execution parameters.

### `docs/`

Contains technical documentation related to the architecture, MongoDB document model, data structures, and processing decisions.

### `experiments/source_discovery/`

Contains exploratory and experimental artifacts used during the identification, assessment, and comparison of potential data sources.

Content stored in this directory is not considered production configuration and should not be consumed directly by the operational ETL pipeline until the corresponding source has been reviewed and approved.

### `gdelt/`

Contains implementation components and supporting resources specifically related to data acquisition through GDELT.

### `logs/`

Stores execution logs generated during acquisition, transformation, validation, and testing processes.

### `queries/gdelt/`

Contains the versioned search queries used for GDELT data acquisition, enabling traceability and reproducibility of the retrieved datasets.

### `scripts/`

Contains executable scripts used to run acquisition, processing, validation, maintenance, or other operational workflows.

### `src/`

Contains the main application code for the ETL component, including source collectors, processing logic, validation, persistence, and reusable services.

### `tests/`

Contains unit and integration tests used to validate source connectors, processing logic, persistence, and other ETL components.

---

## Event pipeline (GDELT + scraper)

Collections in MongoDB (`MONGODB_DATABASE`, default `dragons`):

- `eventos` — seeded from [`data/events/DRAGONS_T1.csv`](data/events/DRAGONS_T1.csv) (68 events; skip the title row).
- `queries` — one BigQuery statement per event (`id`, `id_evento`, `consulta`).
- `whitelist` — up to **100** GKG rows per query (`id`, `hash`, `url`, full GKG payload, `id_query`, `id_scrapper`, `id_metric`).
- `metrics` — one document per query (same counters as the previous execution metrics, plus `id` and `id_query`).
- `scrapper` — article content from the news extractor (`id`, `hash_whitelist`, `contenido`).

Configure Atlas locally in `.env` (see `.env.example`). Do not commit `.env`.

```text
python scripts/seed_events.py
python scripts/run_gdelt.py --max-events 1 --skip-scrape
python scripts/run_gdelt.py --event-id UK-01 --event-id CO-01 --row-limit 100
```

`--max-events` / `--event-id` keep the Atlas free-tier sample small. Full 68 events × 100 rows plus HTML can exceed M0 storage.

The HTML extractor lives in `src/gdelt/collectors/web/news_extractor.py` (from `test/news-scraper-pipeline`).

---

## Relationship with DRAGONS Data Analytics

The overall architecture between both components is:

```text
Online sources
      │
      ▼
dragons-data-etl
      │
      ▼
    MongoDB
      │
      ▼
dragons-data-analytics
```

`dragons-data-etl` is responsible for data acquisition, transformation, validation, quality control, and storage.

`dragons-data-analytics` consumes the resulting data to build the analytical dataset and mining view, and to perform subsequent statistical, NLP, AI, and data-analysis processes.

---

## License

This project is distributed under the **Apache License 2.0**.

The licence applies to the source code contained in this repository. Data collected from external sources remain subject to the access, licensing, and usage conditions established by each source or data provider.

---

## Contact

**Technical & Data Analytics Lead**

**PhD Luis Gabriel Moreno Sandoval**

Pontificia Universidad Javeriana

📧 [morenoluis@javeriana.edu.co](mailto:morenoluis@javeriana.edu.co)
