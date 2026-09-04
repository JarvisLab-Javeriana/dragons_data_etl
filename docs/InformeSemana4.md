# Actualización del informe ejecutivo: avances y entregables de la Tarea 1.1

El equipo técnico avanzó en la organización de la metodología y en la exploración inicial de medios digitales para la Tarea 1.1. Este trabajo permitió consolidar propuestas metodológicas, revisar las fuentes sugeridas por los socios y generar muestras que sirven como insumo para las siguientes decisiones del equipo investigador.

En la carpeta `docs` del repositorio se encuentra el documento [`Metodologia_task1.1.md`](https://github.com/JarvisLab-Javeriana/dragons_data_etl/blob/main/DOCS/Metodologia_task1.1.md)). Allí se organizaron conceptos, alcances, limitaciones y posibles estrategias para la búsqueda, recopilación y validación de información. El documento no representa una metodología definitiva: reúne recomendaciones técnicas que deberán revisarse con los socios y expertos investigadores para definir conjuntamente los criterios finales de la tarea.

Como punto de partida para la exploración de noticias, se tomaron los medios propuestos por los socios del proyecto:

* **Hungría:** *Index*, *Telex* y *Magyar Nemzet*.
* **Reino Unido:** *The Guardian*, BBC y *Daily Mail*.
* **Colombia:** *El Tiempo* y *El Espectador*.

El equipo técnico utilizó Media Cloud mediante su página web y su API. Primero se consultó la cantidad de noticias asociadas con biodiversidad disponibles para los medios definidos por los socios. Después se realizaron búsquedas en las colecciones nacionales de Colombia, Reino Unido y Hungría para identificar otros medios con una presencia relevante de noticias relacionadas con el tema. Cada registro encontrado representa una noticia o artículo periodístico y contiene principalmente datos descriptivos, como el medio, el título, la fecha y el enlace de publicación.

La metodología, los medios revisados y los resultados generales de esta exploración se documentaron en [`national_media_candidates.md`](https://github.com/JarvisLab-Javeriana/dragons_data_etl/blob/main/docs/national_media_candidates.md). Las consultas, exportaciones, muestras y resultados obtenidos se encuentran en la carpeta [`experiments/source_discovery`](https://github.com/JarvisLab-Javeriana/dragons_data_etl/tree/main/experiments/source_discovery).

A partir de esta exploración se definió Media Cloud como una fuente útil para descubrir medios, estimar el volumen inicial de noticias y obtener sus enlaces y datos descriptivos. Sin embargo, la herramienta no proporciona necesariamente el contenido completo de cada noticia. Para la recolección posterior, el equipo técnico deberá desarrollar un extractor específico para cada medio, de acuerdo con su estructura y con la información disponible. Esto permitirá recuperar, cuando sea posible, el texto de la noticia, su autor, fecha de publicación, contenido multimedia, reacciones, veces compartida y comentarios.

Los medios identificados todavía deben ser validados por los socios y expertos investigadores. Esta revisión permitirá decidir cuáles se mantienen, incluyen o excluyen, así como precisar qué se entenderá por “medio nacional”: un medio originado y operado principalmente en el país o también un medio multinacional que publica noticias sobre dicho territorio. Conforme avance la recopilación, el equipo técnico actualizará las métricas y las muestras para facilitar esta validación y ajustar los filtros cuando sea necesario.

> **Importante:** los resultados actuales corresponden a una primera exploración y no constituyen el corpus definitivo. El equipo técnico ya cuenta con un listado ampliado de palabras clave que permitirá buscar una mayor cantidad de medios y artículos. La selección final dependerá de la validación temática y territorial realizada conjuntamente con los socios del proyecto.


# Informe ejecutivo de la herramienta GDELT

# Eventos/temas controversiales que pudieron disparar interacciones o fomentar opiniones (Att Pabla)
**Ver documento eventos.md**

# GDELT
### Produce tres tipos de datos:
- **Event Database**: eventos codificados con la taxonomía CAMEO (más de 300 categorías de actividad física/social).
- **Global Knowledge Graph (GKG)**: personas, lugares, organizaciones, temas y emociones extraídas del texto.
- **Visual Global Knowledge Graph (VGKG)**: catalogación de imágenes de noticias.

### Cómo se accede
| Método | Descripción | Enlace oficial |
|---|---|---|
| **Google BigQuery** | El dataset completo de GDELT 2.0 (Events, GKG, GEG) está alojado como dataset público en BigQuery | gdeltproject.org/data.html |
| **DOC 2.0 API** | API de búsqueda de artículos (no de eventos estructurados) sobre una ventana móvil de ~3 meses de cobertura; devuelve artículos, timelines de volumen de cobertura, y resultados de la VGKG en JSON/JSONP | blog.gdeltproject.org/gdelt-doc-2-0-api-debuts |
| **Archivos raw descargables** | Archivos CSV/TSV actualizados cada 15 minutos (Event 2.0) o diariamente (1.0), descargables directamente | data.gdeltproject.org |

### BigQuery

- El acceso a los datasets públicos de GDELT en BigQuery es gratuito en el sentido de que Google no cobra por alojarlos; lo que se paga es el procesamiento de las consultas que el usuario ejecute contra BigQuery.
- Ser cuidadosos en las consultas
- Free Tier (1 TiB consultas - 10 GiB almacenamiento)
- Pago por consulta (Se cobra de acuerdo a bytes procesados por consulta)

### Conexión desde Python

Ejemplo mínimo con `gdeltdoc`:
```python
from gdeltdoc import GdeltDoc, Filters
 
f = Filters(
    keyword="biodiversity loss",
    country="HU",  # Hungría
    start_date="2023-01-01",
    end_date="2023-12-31"
)
gd = GdeltDoc()
articles = gd.article_search(f)          # DataFrame de artículos
timeline = gd.timeline_search("timelinevol", f)  # volumen de cobertura en el tiempo
```

## Notas
- DOC 2.0 API es gratuito y buena opción pero solo tiene retribución de 3 meses atras desde la consulta. Descartado, necesitamos aprox. 10 años.
- BigQuery es la ruta. Se debe evaluar si el Free Tier es suficiente para nuestras consultas y alcance. De no ser así, se paga de acuerdo a los bytes procesados por consulta.
- No SPARQL
- El Global Knowledge Graph (GKG) incluye "Themes" (temas) extraídos automáticamente del texto de las noticias, y GDELT mantiene un diccionario de temas ambientales (p. ej. relacionados con clima, contaminación, desastres naturales) que sí pueden filtrarse. Esto es más útil para el proyecto que el Event Database puro.
- Permite filtrar por país (mediante campos de actor/geo) y por palabra clave (vía DOC 2.0 API)


# GBIF
No aplicable para scrapping directamente.

Lo podriamos usar para:
- fuente de referencia y contexto biológico
- Diccionario de especies y nombres comunes por país: útil para construir listas de palabras clave (nombres de especies emblemáticas o amenazadas) que luego se usen para filtrar el corpus de noticias/redes sociales por país

# Puntos a revisar/investigar más
- Traducir del hungaro a ingles.
- # de comentarios extraibles por que costo

### Fuentes consultadas (enlaces principales)
- https://digiprensa.com/hu/
- https://en.wikipedia.org/wiki/Telex.hu
- https://ahrefs.com/websites/444.hu/competitors
- https://en.wikipedia.org/wiki/N%C3%A9pszava
- https://www.eurotopics.net/en/148730/nepszava
- https://europeanjournalists.org/blog/2026/05/29/hungary-threats-against-the-countrys-last-progressive-daily-newspaper/
- https://nepszava.us/rolunk/
- https://gdeltproject.org/data.html
- http://data.gdeltproject.org/documentation/GDELT-Event_Codebook-V2.0.pdf
- https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
- https://github.com/alex9smith/gdelt-doc-api
- https://gdeltcloud.com/methodology
- https://docs.gdeltcloud.com/api-reference/cameoplus-events/cameo+-events/list-cameo+-events
- https://en.wikipedia.org/wiki/GDELT_Project
- https://data.europa.eu/en/about/sparql
- https://cloud.google.com/bigquery/pricing
- https://techdocs.gbif.org/en/openapi/
- https://datos.gob.es/en/noticias/biodiversity-and-open-data-gbif-international-biodiversity-database-par-excellence
- https://www.humboldt.org.co/sobre-el-instituto
- https://www.humboldt.org.co/atencion-y-servicios/solicitudes
- https://www.minambiente.gov.co/entidad/instituto-humboldt/
- https://www.sgi-network.org/2024/Hungary/Environmental_Sustainability
- https://www.oneplanetnetwork.org/organisations/hungary-ministry-energy
- https://www.eea.europa.eu/en/europe-environment-2025/countries/hungary/terrestrial-protected-areas
- https://en.wikipedia.org/wiki/Joint_Nature_Conservation_Committee
- https://jncc.gov.uk/
- https://www.gov.uk/government/organisations/joint-nature-conservation-committee
- https://scrapfly.io/blog/posts/how-to-scrape-twitter
- https://api.sorsa.io/blog/how-to-scrape-twitter
- https://github.com/AndyTheFactory/newspaper4k
- https://www.contextractor.com/trafilatura-vs-readability-vs-newspaper/
- https://trafilatura.readthedocs.io/en/latest/evaluation.html

---

# Informe ejecutivo de la herramienta Apify

## 1. Propósito de la evaluación

El equipo de Analítica y Desarrollo investigó Apify como una posible herramienta para recolectar conversaciones públicas sobre biodiversidad y asuntos ambientales en X, Facebook e Instagram.

La plataforma cuenta con herramientas de extracción denominadas **Actors**, que permiten buscar información mediante palabras clave, hashtags, cuentas, enlaces, fechas y límites de resultados. Dependiendo de la red social y de la herramienta seleccionada, se pueden obtener publicaciones, comentarios, respuestas, fechas, enlaces, autores públicos y métricas de interacción.

## 2. Estrategia metodológica identificada

La investigación mostró que la recolección no debería limitarse a la palabra “biodiversidad”. Para obtener una visión más completa de las conversaciones digitales, el equipo investigador recomienda considerar:

* Términos ambientales en húngaro, como `biodiverzitás`, `biológiai sokféleség`, `természetvédelem`, `erdőirtás` y `klímaváltozás`.
* Hashtags, especies, territorios, parques, ríos, leyes, conflictos y eventos ambientales.
* Cuentas de instituciones, organizaciones ambientales, comunidades, científicos, medios de comunicación, empresas y personas influyentes.
* Medios relacionados con Hungría, como *Index*, *Telex* y *Magyar Nemzet*, sujetos a verificación.
* Publicaciones con alta y baja interacción, con el fin de reconocer tanto los discursos más visibles como aquellos con menor alcance.

También se identificó la conveniencia de comenzar con búsquedas pequeñas, revisar sus resultados y ampliar progresivamente el vocabulario, las cuentas y los temas de interés. Con lo cual es necesario ir refinando la estrategia metodológica para mejorar la calidad de los resultados.

## 3. Delimitación territorial y de participantes

El idioma de una publicación o comentario no permite determinar con certeza el país, la nacionalidad ni el lugar de residencia de su autor. Una publicación en húngaro puede proceder de una persona ubicada fuera de Hungría, y una publicación en inglés puede haberse generado desde cualquier país.

Por esta razón, el equipo técnico recomienda no afirmar que los datos representan exclusivamente a “personas húngaras”. La formulación metodológicamente podría verse como:

> **Conversaciones públicas asociadas al ecosistema digital húngaro sobre biodiversidad.**

Esta relación con Hungría podría establecerse mediante la combinación de señales como el idioma, las cuentas locales, los medios nacionales, los lugares, los hashtags, los eventos y los temas relacionados con el país.

En algunos casos, Apify podría recuperar información pública del autor, como el nombre visible, el usuario, el enlace del perfil o una ubicación declarada. Sin embargo, estos datos pueden estar ausentes, incompletos o no ser verificables.

> **Disclaimer metodológico:** no se puede asegurar desde dónde publica una persona. Cualquier ubicación disponible debe utilizarse únicamente como un indicador contextual plausible, no como un dato real, una estimación confiable ni una prueba de nacionalidad o residencia.

## 4. Funcionamiento y costos identificados

La revisión permitió identificar dos formas principales de cobro:

| Modalidad          | Descripción                                                                            |
| ------------------ | -------------------------------------------------------------------------------------- |
| Pago por resultado | Se cobra por cada publicación, comentario, respuesta, perfil u otro registro obtenido. |
| Pago por uso       | Se cobra según los recursos utilizados durante la extracción.                          |

El plan Starter tiene un costo de **US$29 mensuales** e incluye el mismo valor como crédito de consumo. Para dos meses, el costo sería de **US$58**. Si el uso supera este monto, se generarían cobros adicionales.

Las tarifas y los datos disponibles pueden variar según la herramienta seleccionada, por lo que deben verificarse antes de realizar una contratación. [Planes de Apify](https://apify.com/pricing).

## 5. Piloto recomendado

El equipo investigador sugirió utilizar los **US$58** correspondientes a dos meses del plan Starter para realizar una prueba piloto, no para iniciar directamente una recolección masiva.

Esta prueba permitiría:

* Comparar herramientas para X, Facebook e Instagram.
* Revisar la cobertura y calidad de los resultados.
* Verificar los datos recuperados por cada herramienta.
* Comprobar la relación entre publicaciones, comentarios y respuestas.
* Evaluar la recuperación de contenido en húngaro.
* Estimar el costo por registro útil.
* Definir las palabras, hashtags, cuentas, periodos y límites de recolección (Ecosistema digital y metodología de recolección).
* Seleccionar las herramientas más adecuadas antes de una extracción de mayor volumen.

Se recomendó evaluar entre **1.000 y 5.000 registros por red** y documentar los resultados, las limitaciones y el costo observado.

## 6. Estimación de una extracción básica

Como referencia, se estimó la recolección de **100.000 comentarios o respuestas por cada red durante los dos meses**, para un total de 300.000 registros. Estos valores se calcularon a partir de tarifas de referencia publicadas para herramientas de [X](https://apify.com/apidojo/tweet-scraper), [Facebook](https://apify.com/apify/facebook-comments-scraper) e [Instagram](https://apify.com/apify/instagram-scraper).

| Red social | Costo de referencia |
| ---------- | ------------------: |
| X          |           **US$45** |
| Facebook   |          **US$145** |
| Instagram  |          **US$235** |
| **Total**  |          **US$425** |

> **Importante:** los valores son aproximados y pueden cambiar según el método de extracción, el volumen, los datos recuperados y las tarifas vigentes. Los costos aumentan de manera diferente en cada red social y dependen de la forma de cobro del Actor seleccionado. Algunos Actors, especialmente en Instagram, pueden cobrar por cada publicación procesada y no por cada comentario obtenido. Por ello, el costo final dependerá del número de publicaciones consultadas y de los comentarios disponibles en cada una.

## 7. Escenario ampliado

La investigación identificó que un análisis más completo podría requerir publicaciones originales, comentarios, respuestas, cuentas, hashtags y métricas de interacción. Con base en estos elementos, se obtuvo la siguiente estimación:

| Componente                                              |     Estimación |
| ------------------------------------------------------- | -------------: |
| Comentarios y respuestas                                |         US$425 |
| Búsqueda de publicaciones, cuentas, hashtags y contexto |       US$25–40 |
| Pruebas adicionales y revisión de calidad               |       US$35–50 |
| Nuevas ejecuciones y resultados adicionales             |       US$75–90 |
| **Presupuesto total estimado**                          | **US$560–605** |

Los **US$58** del plan Starter ya están incluidos en este total y no deben sumarse nuevamente.

## 7.1. Posible descuento académico

Durante la investigación se identificó que Apify contempla posibles beneficios para estudiantes e instituciones académicas. El equipo investigador sugirió consultar directamente con la empresa la disponibilidad de un descuento antes de tomar una decisión sobre una recolección masiva.

Este beneficio no se incluyó en los cálculos. Por ello, el rango de **US$560–605** se mantiene como una estimación conservadora. [Programa de Apify para universidades](https://apify.com/for/universities).

## 8  Herramienta principal de IA: LLM

Después de la recolección y preparación de los datos obtenidos mediante Apify, GDELT y otras fuentes, se propone utilizar un modelo de lenguaje de gran escala (LLM) como herramienta principal de inteligencia artificial para el análisis del proyecto.

### Modelos propuestos

* **Gemini 2.5 Flash:** recomendado para procesar grandes volúmenes de información, ejecutar tareas repetitivas y mantener un menor costo de consumo.
* **Gemini 2.5 Pro:** recomendado para análisis de mayor complejidad que requieran mejor comprensión contextual y capacidad de razonamiento.

Se podrá adoptar una estrategia combinada: utilizar Gemini 2.5 Flash para el procesamiento masivo y reservar Gemini 2.5 Pro para casos complejos o que requieran una revisión más detallada.

Estos modelos también tienen la capacidad de analizar los contenidos directamente en su idioma original y apoyar tareas de traducción. Será necesario verificar mediante pruebas piloto la calidad de los resultados en español, húngaro e inglés.

### Protocolo técnico e investigativo

Antes de iniciar el procesamiento, se deberá definir un protocolo conjunto entre el equipo de desarrollo y el equipo investigativo. Este protocolo establecerá los criterios técnicos y metodológicos para utilizar los modelos, de esta manera poder cumplir con los objetivos del proyecto y optimizar los recursos disponibles.

### Estimación de costo

Con base en las tareas consideradas hasta el momento, se estima un consumo del LLM de entre **US$300 y US$400**. El valor deberá validarse mediante una prueba piloto, ya que dependerá del modelo seleccionado, la cantidad y longitud de los registros, el número de ejecuciones y el tamaño de las instrucciones y respuestas.

| Componente tecnológico                              |   Costo estimado |
| --------------------------------------------------- | ---------------: |
| Recolección de datos con Apify                      |   **US$560–605** |
| Procesamiento con Gemini 2.5 Flash o Gemini 2.5 Pro |   **US$300–400** |
| **Costo tecnológico total estimado**                | **US$860–1.005** |

Los valores son preliminares y podrán modificarse según los resultados de la prueba piloto, el volumen definitivo de información y las tarifas vigentes.


## 9. Conclusión

La principal recomendación es realizar primero una prueba piloto que permita comparar las opciones disponibles, revisar la calidad de los datos y estimar los costos reales de extracción, recolección y procesamiento del corpus.

