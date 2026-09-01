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
├── config/                       # General project and source configuration
│
├── docs/                         # Technical and data model documentation
│
├── experiments/
│   └── source_discovery/         # Exploratory source assessment and discovery artifacts
│
├── gdelt/                        # GDELT-specific implementation and supporting resources
│
├── logs/                         # Execution and processing logs
│
├── queries/
│   └── gdelt/                    # Versioned queries used for GDELT acquisition
│
├── scripts/                      # Operational and execution scripts
│
├── src/                          # Core ETL implementation
│
├── tests/                        # Unit and integration tests
│
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
```
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
