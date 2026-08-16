# 🐉 DRAGONS Data ETL

### Componente de Ingeniería de Datos del proyecto DRAGONS

**Proyecto:** DRAGONS – *Diffusing biodiversity Response-able Action and awareness raising through citizen empowerment, inclusive engagement and innovative Governance of Nature and Society*
**Componente:** WP1 – Understanding societal perceptions, awareness, and engagement responses to biodiversity loss
**Institución:** Pontificia Universidad Javeriana
**Repositorio relacionado:** `dragons-data-analytics`

---

## Objetivo

Desarrollar el componente de ingeniería de datos encargado de recolectar, transformar, validar y almacenar información proveniente de fuentes públicas o autorizadas en línea, incluyendo redes sociales, medios de comunicación y otros mecanismos de adquisición permitidos.

El objetivo es construir un flujo reproducible que permita consolidar texto y metadatos en una base documental MongoDB, garantizando trazabilidad, calidad y disponibilidad para su posterior explotación en el repositorio `dragons-data-analytics`.

---

## Equipo del Proyecto

### Dirección del Proyecto

Responsables de orientar de manera conjunta la estrategia técnica, analítica, científica y temática del componente, asegurando la articulación entre la ingeniería de datos, la analítica y los objetivos de investigación en biodiversidad.

**Integrantes:**

- **PhD Luis Gabriel Moreno Sandoval**  
  **Technical & Data Analytics Lead**
  JDocente Jefe de Sección, Departamento de Ingeniería de Sistemas
  Pontificia Universidad Javeriana
    
  Responsable de la dirección técnica y metodológica del componente de datos, definición de arquitectura, estrategia de analítica e inteligencia artificial, seguimiento del desarrollo tecnológico y validación de los productos técnicos y analíticos.  
  📧 [morenoluis@javeriana.edu.co](mailto:morenoluis@javeriana.edu.co)

- **PhD Juan David Amaya Espinel**  
  **Biodiversity Research & Domain Lead**  
  Docente Asociado, Departamento de Ecología y Territorio  
  Pontificia Universidad Javeriana  

  Responsable del liderazgo científico y temático del componente de biodiversidad. Orienta la definición de las preguntas de investigación, los criterios conceptuales para la selección y evaluación de las fuentes, y la interpretación de los resultados desde el conocimiento experto del dominio.
  📧 [jamayae@javeriana.edu.co](mailto:jamayae@javeriana.edu.co)  

---

### Coordinación del Proyecto

- **Juan Pablo Arias Buitrago**  
  **Data Scientist & Technical Project Coordinator**  
  Responsable de la coordinación operativa del proyecto, seguimiento de actividades y entregables, articulación entre `dragons-data-etl` y `dragons-data-analytics`, validación de requerimientos, acompañamiento en la integración de los datos recolectados y apoyo en los procesos analíticos del proyecto.  
  📧 [ariasj.u@javeriana.edu.co](mailto:ariasj.u@javeriana.edu.co)

---

### Ciencia de Datos y Validación Analítica

Responsable de orientar y ejecutar los principales procesos de análisis sobre los datos recolectados, así como de apoyar la definición de los requerimientos de información necesarios desde el componente ETL.

**Integrante:**

- **Sergio Pardo Hurtado**  
  **NLP Data Scientist & Lead Data Analyst**  
  Participa en el componente ETL desde la perspectiva analítica, apoyando la definición de campos, variables y criterios de calidad requeridos para los análisis posteriores. Es responsable principal del componente analítico, incluyendo la construcción y validación de la vista minable, análisis estadístico, procesamiento de lenguaje natural, evaluación de modelos de inteligencia artificial y generación de resultados analíticos.  
  📧 [sergio_pardo@javeriana.edu.co](mailto:sergio_pardo@javeriana.edu.co)

---

### Equipo de Ingeniería de Datos y Plataforma

Responsables del desarrollo de los componentes de adquisición, transformación, calidad, almacenamiento e infraestructura que soportan el flujo ETL del proyecto.

**Integrantes:**

- **Viviana Gómez León**  
  **Data Engineer & Platform Developer**  
  Responsable del desarrollo de conectores, integración con fuentes externas, procesos de extracción y transformación, persistencia en MongoDB, servicios de comunicación entre componentes y soporte de plataforma.  
  📧 [gomezlv@javeriana.edu.co](mailto:gomezlv@javeriana.edu.co)

- **Marlon Jhoan Garcia Restrepo**  
  **Data Engineer & DevOps Engineer**  
  Responsable del desarrollo y mantenimiento de pipelines ETL, calidad y almacenamiento de datos, automatización, configuración de ambientes, contenerización, integración continua, despliegue y soporte de la infraestructura técnica del proyecto.  
  📧 [mjgarcia@javeriana.edu.co](mailto:mjgarcia@javeriana.edu.co)

---

### Coordinación de Dominio y Validación Científica

- **Pabla Lozano Ramírez**  
  **Biodiversity Domain Lead & Research Coordinator**
  Responsable de coordinar transversalmente la perspectiva temática y científica del proyecto, garantizando que las fuentes, consultas, criterios de selección, corpus y resultados analíticos mantengan pertinencia y coherencia con los objetivos del componente de biodiversidad.
  📧 [pabla-lozano@javeriana.edu.co](mailto:pabla-lozano@javeriana.edu.co)

---

## Flujo General

```text
Fuentes públicas y autorizadas
             │
             ▼
       Adquisición de datos
             │
             ▼
          Validación
             │
             ▼
    Limpieza y normalización
             │
             ▼
      Control de calidad
             │
             ▼
           MongoDB
             │
             ▼
    dragons-data-analytics
```

---

## Tecnologías Principales

* **Lenguaje de programación:** Python.
* **Base de datos:** MongoDB.
* **Integración:** APIs REST, RSS y servicios externos.
* **Contenedores:** Docker.
* **Control de versiones:** Git / GitHub.

---

## Estructura del Proyecto

```text
dragons-data-etl/
│
├── config/
│   ├── sources/                  # Configuración de fuentes
│   ├── queries/                  # Consultas y términos de búsqueda
│   └── settings/                 # Parámetros generales
│
├── src/
│   ├── collectors/               # Conectores y adquisición de datos
│   ├── processing/               # Limpieza y transformación
│   ├── quality/                  # Validaciones y calidad de datos
│   ├── database/                 # Persistencia y acceso a MongoDB
│   ├── pipelines/                # Flujo ETL
│   └── common/                   # Utilidades compartidas
│
├── scripts/                      # Scripts de ejecución
├── tests/                        # Pruebas
├── docs/                         # Documentación técnica
├── .env.example                  # Variables de entorno
├── .gitignore
├── pyproject.toml
├── LICENSE
└── README.md
```

---

## Relación con DRAGONS Data Analytics

La arquitectura general entre ambos componentes es:

```text
Fuentes en línea
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

`dragons-data-etl` es responsable de la adquisición, transformación, validación y almacenamiento.

`dragons-data-analytics` consume estos datos para construir la vista minable y desarrollar los análisis posteriores.

---

## Licencia

Este proyecto se distribuye bajo la **Apache License 2.0**.

La licencia aplica al código fuente del repositorio. Los datos recolectados estarán sujetos a las condiciones de uso, licenciamiento y acceso definidas por cada fuente o proveedor.

---

## Contacto

**Technical & Data Analytics Lead**
**PhD Luis Gabriel Moreno Sandoval**
Pontificia Universidad Javeriana
📧 [morenoluis@javeriana.edu.co](mailto:morenoluis@javeriana.edu.co)
