# INFORME SEMANAL - AGOSTO 17-23 (VIVIANA)

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


# Instituciones Ambientales Hungria
- Hungria no tiene ministerio de ambiente, por lo tanto no tiene un equivalente a Humboldt.
- NO necesario de investigar (Att Pabla) -> Queremos publico general, no un nicho de expertos. EVITAR SESGO.

# Fuentes a usar (Att Juanpa & Pabla)
- X
- Facebook
- Instagram
- Youtube
- Revistas/Periodicos

# Periodicos Hungria
*Ver excel*
- Elegir entre 2-3.

# Herramientas open source relevantes para scraping y almacenamiento
 
### Web scraping de periódicos
 
| Herramienta | Qué hace | Licencia | Limitaciones conocidas |
|---|---|---|---|
| **Scrapy** | Framework completo de Python para construir arañas (spiders) de scraping a gran escala, con manejo de colas, exportación estructurada y middlewares | BSD | Curva de aprendizaje mayor que soluciones simples; no ejecuta JavaScript por sí solo (requiere integrarlo con Splash o Playwright para sitios con mucho JS) |
| **Playwright** | Automatización de navegador (headless) para Python/Node/etc., permite scrapear sitios con contenido dinámico (JS-heavy), incluyendo interacción con paywalls suaves | Apache 2.0 | Más pesado en recursos que peticiones HTTP simples; los sitios con detección anti-bot avanzada (fingerprinting) pueden seguir bloqueando |
| **Trafilatura** | Extracción de texto principal, metadatos y comentarios de páginas de noticias; en comparativas recientes es de las opciones más robustas y activamente mantenidas | Apache 2.0/GPL (dual, verificar versión) | No hace crawling por sí sola (solo extracción); <cite index="106-1">es mantenida activamente por Adrien Barbaresi, investigador de la BBAW, con lanzamientos regulares</cite> |
| **Newspaper4k** (sucesor mantenido de newspaper3k) | Extracción de artículos, títulos y metadatos orientada específicamente a sitios de noticias | MIT | <cite index="108-1">Newspaper4k nació como un fork de newspaper3k, que no recibía actualizaciones desde septiembre de 2020; mantiene compatibilidad de API con el original</cite>. **Importante:** no usar `newspaper3k` (paquete original) porque está efectivamente abandonado; usar `newspaper4k` en su lugar. |
| **BeautifulSoup** | Parseo de HTML/XML para extracción manual dirigida cuando se conoce la estructura del sitio | MIT | Requiere combinarse con `requests` o similar; no maneja JS ni crawling a gran escala por sí sola |
 
### Captura de redes sociales sin herramientas de pago tipo Apify
 
Esta es el área con más limitaciones actuales, y es importante ser honesto con el equipo al respecto:
 
| Herramienta | Qué hace | Licencia | Limitaciones conocidas |
|---|---|---|---|
| **snscrape / Twint** | Scraping histórico de Twitter/X sin necesidad de API oficial | GPL-3.0 (Twint) / Lesser GPL (snscrape) | **[Advertencia fuerte]** <cite index="96-1">Twint fue abandonado hace años, y snscrape dejó de funcionar cuando X eliminó el acceso anónimo tipo "guest" en 2023</cite>. **No se recomienda construir el pipeline del proyecto sobre estas herramientas para X/Twitter en 2026.** |
| **Twikit / twscrape / Tweety / Scweet** | Alternativas más recientes que sí funcionan actualmente para X, pero requieren sesión con cuenta propia logueada (no son 100% anónimas) | Varía por proyecto (MIT/GPL, verificar cada repo) | <cite index="102-1">Requieren proxies residenciales y una cuenta logueada para datos completos, y tienden a romperse cada dos a cuatro semanas cuando X rota sus tokens de invitado e identificadores GraphQL</cite>. Mantenimiento intensivo, riesgo de bloqueo de la cuenta usada. |
| **PRAW (Python Reddit API Wrapper)** | Acceso a la API oficial (gratuita dentro de límites) de Reddit para extraer posts/comentarios | BSD | Sujeta a los términos de uso y rate limits de la API oficial de Reddit, que han cambiado varias veces en los últimos años; verificar condiciones vigentes antes de construir el pipeline |
| **RSS feeds nativos de medios/portales** | No es "scraping social" propiamente, pero permite capturar de forma legal y estable la publicación de artículos de los medios ya listados en la Sección 1 (ej. Telex tiene RSS confirmado) | N/A (protocolo abierto) | Solo cubre contenido nuevo desde que se empieza a monitorear; no da histórico retroactivo |
 

# Puntos a revisar/investigar más
- Traducir del hungaro a ingles (Gemini?)
- Google trends
- Recurso Pabla
- Scrapping Youtube
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
# INFORME SEMANAL - AGOSTO 17-23 (MARLON)

## Investigación de Apify para extracción de datos de redes sociales

Durante esta semana se investigó **Apify** como posible herramienta para la recopilación automatizada de datos públicos provenientes de redes sociales para el proyecto de investigación.

Apify funciona mediante herramientas denominadas **Actors**, que son programas especializados en tareas de scraping y automatización. Dentro de Apify Store existen Actors desarrollados directamente por Apify y otros desarrollados por terceros, por lo que sus funcionalidades, precios y limitaciones pueden variar.

Para el proyecto se identificaron alternativas para obtener información de:

* Instagram
* TikTok
* YouTube
* X (antes Twitter)

Dependiendo del Actor utilizado, es posible obtener publicaciones, videos, perfiles, comentarios y diferentes métricas de interacción, como número de likes, visualizaciones, comentarios, fecha de publicación, descripción o caption, entre otros datos.

## Costos de extracción

Un aspecto importante es que **Apify no tiene un precio único por cada red social**. El costo depende del Actor seleccionado y de su modelo de cobro.

Algunos Actors utilizan un modelo **Pay Per Event / Pay Per Result**, donde se cobra según la cantidad de elementos obtenidos. Otros pueden cobrar por uso de recursos computacionales o requerir una tarifa propia.

Como referencia, algunos Actors actualmente disponibles presentan los siguientes precios:

| Plataforma  | Actor de referencia                | Tipo de dato      | Precio aproximado por 1.000 resultados |
| ----------- | ---------------------------------- | ----------------- | -------------------------------------: |
| Instagram   | Instagram Post Scraper (Apify)     | Publicaciones     |                      desde **US$1,00** |
| Instagram   | Instagram Comments Scraper (Apify) | Comentarios       |                      desde **US$1,90** |
| TikTok      | TikTok Scraper (Clockworks)        | Resultados/videos |                      desde **US$1,70** |
| YouTube     | YouTube Scraper (Streamers)        | Videos            |                      desde **US$2,40** |
| X / Twitter | Tweet Scraper V2 (API Dojo)        | Tweets            |                      desde **US$0,40** |

Estos valores deben considerarse **precios de referencia y no tarifas generales de Apify**, debido a que existen múltiples Actors para una misma plataforma y los precios pueden cambiar.

Por ejemplo, solamente para Instagram existen Actors alternativos que cobran aproximadamente **US$1,30 por 1.000 publicaciones y US$2,00 por 1.000 comentarios**, mientras que otros Actors pueden ofrecer precios menores o mayores.

Por lo tanto, para el proyecto no sería correcto asumir un costo promedio único de US$0,50–US$2,60 por cada 1.000 publicaciones. El costo debe calcularse a partir de los Actors específicos que finalmente se seleccionen.

## Ejemplo de costos para el proyecto

Tomando únicamente los Actors de referencia anteriores, se puede realizar una primera estimación:

| Cantidad | Instagram posts | TikTok videos | YouTube videos |   Tweets |
| -------: | --------------: | ------------: | -------------: | -------: |
|    1.000 |         US$1,00 |       US$1,70 |        US$2,40 |  US$0,40 |
|   10.000 |        US$10,00 |      US$17,00 |       US$24,00 |  US$4,00 |
|   50.000 |        US$50,00 |      US$85,00 |      US$120,00 | US$20,00 |
|  100.000 |       US$100,00 |     US$170,00 |      US$240,00 | US$40,00 |

**Nota:** esta tabla es una proyección lineal basada en el precio anunciado “desde” por cada Actor. El costo real puede variar por descuentos del plan, modelo de cobro, configuración del Actor y otros recursos consumidos.

### Ejemplo incluyendo comentarios

Los comentarios pueden representar un costo adicional importante.

Utilizando como referencia el Instagram Comments Scraper oficial de Apify:

| Comentarios extraídos | Costo de referencia |
| --------------------: | ------------------: |
|                 1.000 |             US$1,90 |
|                10.000 |            US$19,00 |
|                50.000 |            US$95,00 |
|               100.000 |           US$190,00 |

Esto es relevante para la investigación porque una estrategia que recopile publicaciones **y todos sus comentarios** puede generar muchos más registros que una estrategia enfocada únicamente en publicaciones.

Por ejemplo, extraer 10.000 publicaciones y posteriormente 100.000 comentarios asociados puede resultar considerablemente más costoso que obtener únicamente las publicaciones.

## Planes de Apify

Además del precio particular de cada Actor, Apify maneja planes mensuales que proporcionan créditos para utilizar la plataforma y Apify Store.

| Plan       | Precio mensual | Crédito incluido |  Compute Unit |
| ---------- | -------------: | ---------------: | ------------: |
| Free       |           US$0 |     **US$5/mes** |    US$0,20/CU |
| Starter    |  **US$29/mes** |    **US$29/mes** |    US$0,20/CU |
| Scale      | **US$199/mes** |   **US$199/mes** |    US$0,16/CU |
| Business   | **US$999/mes** |   **US$999/mes** |    US$0,13/CU |
| Enterprise |  Personalizado |    Personalizado | Personalizado |

Una **Compute Unit (CU)** corresponde aproximadamente al uso de **1 GB de memoria durante una hora**.

Es importante aclarar que pagar US$29 por Starter **no significa necesariamente pagar US$29 adicionales más todo el scraping realizado**. El plan incluye US$29 de uso prepagado que puede utilizarse para Actors de Apify Store o consumo de la plataforma. Si se supera ese valor, el consumo adicional se cobra bajo el esquema *pay as you go*.

Los planes superiores también ofrecen descuentos para determinados Actors de Apify Store, además de mayores límites de ejecución y recursos.

## Corrección sobre la limitación de 10 resultados

Inicialmente se consideró que el plan gratuito de Apify solamente permitía visualizar o extraer 10 elementos. Sin embargo, esta afirmación **no aplica de forma general a Apify**.

Los datasets de Apify pueden contener y exportar grandes cantidades de resultados y pueden descargarse en formatos como:

* JSON
* JSONL
* CSV
* Excel (XLSX)
* XML
* HTML
* RSS

La API de datasets tampoco establece un límite general de 10 elementos.

La confusión se debe a que **algunos Actors particulares sí imponen restricciones a los usuarios gratuitos**.

Por ejemplo, Tweet Scraper V2 para X/Twitter indica actualmente que los usuarios gratuitos están limitados a **5 ejecuciones mensuales con un máximo de 10 elementos por ejecución**. Esta es una restricción establecida por ese Actor específico y no por el sistema de datasets de Apify en general.

Por esta razón, antes de seleccionar una herramienta para el proyecto es necesario revisar individualmente las condiciones de cada Actor.

## Capacidad del plan gratuito

Actualmente, el plan Free proporciona aproximadamente **US$5 mensuales de crédito** para utilizar Apify Store o ejecutar Actors propios.

Esto permitiría realizar pruebas y experimentos pequeños antes de contratar un plan.

Como ejemplo teórico, ignorando otros posibles costos:

| Actor                      | Precio por 1.000 | Cantidad aproximada cubierta por US$5 |
| -------------------------- | ---------------: | ------------------------------------: |
| X / Tweet Scraper V2       |          US$0,40 |                       ~12.500 tweets* |
| Instagram Post Scraper     |          US$1,00 |                          ~5.000 posts |
| TikTok Scraper             |          US$1,70 |                     ~2.940 resultados |
| Instagram Comments Scraper |          US$1,90 |                    ~2.630 comentarios |
| YouTube Scraper            |          US$2,40 |                         ~2.080 videos |

*Tweet Scraper V2 establece restricciones adicionales para usuarios gratuitos, por lo que esta cantidad representa únicamente la equivalencia económica del crédito y **no necesariamente la cantidad que puede extraerse utilizando el Actor en modalidad gratuita**.

## Costos de almacenamiento

Además del scraping, Apify puede generar costos asociados al almacenamiento y las operaciones realizadas sobre los datasets.

Como referencia, para los planes Free/Starter, Apify muestra aproximadamente:

| Recurso                   |            Precio de referencia |
| ------------------------- | ------------------------------: |
| Almacenamiento de dataset |             US$0,024 por GB/día |
| Lecturas                  | US$0,0004 por 1.000 operaciones |
| Escrituras                |  US$0,005 por 1.000 operaciones |

Para datasets relativamente pequeños estos costos pueden ser bajos frente al costo de extracción, pero deben considerarse si el proyecto pretende almacenar grandes cantidades de publicaciones, comentarios y metadatos durante periodos prolongados.

## Recomendación para el proyecto

Para una fase inicial de investigación, el **plan Free** puede utilizarse para probar distintos Actors, estudiar la estructura de los datos obtenidos y estimar cuántos resultados se necesitan realmente.

Para una extracción de mayor escala, el **plan Starter de US$29 mensuales** sería una alternativa inicial más adecuada, debido a que incluye US$29 mensuales de crédito, acceso a los Actors de Apify Store, soporte por chat y descuentos de nivel Bronze en el Store.

Sin embargo, antes de contratarlo se recomienda realizar una estimación basada en:

1. Número de publicaciones que se desea analizar por plataforma.
2. Número promedio de comentarios que se desea obtener por publicación.
3. Frecuencia con la que se ejecutará la extracción.
4. Actor específico que se utilizará para cada plataforma.
5. Necesidad de conservar históricos o ejecutar el proceso periódicamente.

Si el proyecto requiere recopilar cientos de miles o millones de registros de forma recurrente, sería conveniente comparar los planes **Scale, Business y Enterprise**, además de contactar directamente a Apify para evaluar una solución personalizada.

## Conclusión

El costo de Apify no depende únicamente de “usar Apify”, sino principalmente del **Actor seleccionado, el número y tipo de registros extraídos, el plan contratado y los recursos adicionales consumidos**.

Por este motivo, el siguiente paso recomendado es definir el volumen aproximado de publicaciones y comentarios requerido para la investigación y, con base en ello, comparar los Actors disponibles para determinar la combinación con mejor relación costo-beneficio.
