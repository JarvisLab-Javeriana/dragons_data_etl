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

# INFORME SEMANAL - AGOSTO 17-23 (MARLON)
