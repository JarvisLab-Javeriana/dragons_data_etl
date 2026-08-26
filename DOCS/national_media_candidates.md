# Informe ejecutivo de medios nacionales candidatos

## 1. Propósito de la evaluación

El equipo de Analítica y Desarrollo evaluó Media Cloud para estimar el volumen de noticias relacionadas con biodiversidad e identificar medios digitales candidatos en Colombia, Reino Unido y Hungría.

La revisión se desarrolló en dos partes:

1. Consulta de los medios definidos previamente por los socios del proyecto.
2. Búsqueda nacional para verificar si esos medios aparecían entre las fuentes con mayor cantidad de noticias relacionadas con biodiversidad.

> **Importante:** los resultados son exploratorios y deben ser validados por los socios investigadores antes de definir los medios y artículos que integrarán el corpus del proyecto.

## 2. ¿Qué es Media Cloud?

Media Cloud es una plataforma abierta para buscar, organizar, visualizar y analizar noticias publicadas en medios digitales.

Su archivo se alimenta principalmente mediante fuentes RSS y mapas de sitio. La herramienta permite realizar búsquedas por palabras clave, periodos, medios específicos y colecciones nacionales.

En la interfaz web se pueden revisar:

* Cantidad de noticias encontradas.
* Comportamiento de la cobertura a través del tiempo.
* Ejemplos de noticias.
* Medios que publican con mayor frecuencia sobre el tema.
* Palabras frecuentes en los títulos.

Media Cloud facilita el descubrimiento y la comparación de medios, pero sus resultados dependen de las fuentes incorporadas, la fecha desde la cual cada medio fue recopilado y la disponibilidad de sus publicaciones.

## 3. ¿Cómo se utilizó?

### 3.1 Uso desde la interfaz web

En la interfaz de Media Cloud se configuraron las siguientes palabras, de acuerdo con el idioma de cada país:

* Colombia: `biodiversidad`.
* Reino Unido: `biodiversity`.
* Hungría: `biodiverzitás`.

También se seleccionaron los medios definidos por los socios o las colecciones nacionales correspondientes. El periodo consultado estuvo comprendido entre el **1 de enero de 2016 y el 24 de agosto de 2026**.

Las pantallas de resultados permitieron revisar la cantidad de noticias, su comportamiento en el tiempo, algunos ejemplos de publicaciones y los medios con mayor presencia en los resultados.

### 3.2 Uso mediante la API

La API de Media Cloud se utilizó para obtener datos descriptivos y metadatos asociados con las noticias encontradas. Entre estos datos se encuentran:

* Medio o fuente.
* País e idioma.
* Fecha de publicación.
* Título.
* URL de la noticia.
* Palabras clave identificadas.
* Resultado de la revisión de relevancia.

Estos datos permiten organizar y dimensionar el posible corpus, pero no garantizan la recuperación completa del contenido de las noticias.

Para construir el corpus, el equipo técnico deberá desarrollar un proceso de extracción específico para cada medio. Esta extracción deberá adaptarse a la estructura y disponibilidad de información de cada sitio.

Dependiendo del medio, podría recuperarse:

* Contenido completo de la noticia.
* Nombre de la persona autora.
* Fecha y hora de publicación.
* Imágenes, videos u otros recursos asociados.
* Cantidad de reacciones o “me gusta”.
* Número de veces que se compartió o reenvió la publicación.
* Comentarios asociados.
* Respuestas a los comentarios.
* Otras métricas públicas de interacción.

> **Importante:** la información disponible dependerá de cada medio. No todos los portales publican comentarios, reacciones o métricas de interacción, y algunos pueden limitar el acceso a estos datos.

## 4. Metodología aplicada

### 4.1 Parte 1: medios definidos por los socios

La primera parte buscó estimar la cantidad de noticias que podría recuperarse de los medios digitales indicados por los socios del proyecto:

* **Hungría:** *Index*, *Telex* y *Magyar Nemzet*.
* **Reino Unido:** *The Guardian* y BBC. En esta prueba se utilizó BBC como alternativa a *Daily Mail*.
* **Colombia:** *El Tiempo* y *El Espectador*.

Para cada país se consultó la palabra equivalente a biodiversidad en su idioma. Posteriormente, se comparó la cantidad de noticias mostrada en la interfaz web con los registros recuperados mediante la API.

Cada registro se interpretó como una noticia o artículo periodístico identificado por Media Cloud.

### 4.2 Parte 2: revisión en las colecciones nacionales

La segunda parte consistió en realizar una búsqueda dentro de las colecciones nacionales de Media Cloud.

El objetivo fue revisar si los medios definidos por los socios aparecían entre las fuentes con mayor cantidad de noticias relacionadas con biodiversidad en cada país.

La comparación se realizó a partir del número de registros encontrados, considerando cada registro como una noticia o artículo periodístico. Esta revisión también permitió reconocer otros medios que podrían evaluarse como candidatos para ampliar el corpus.

## 5. Resultados de los medios definidos por los socios

| País        | Consulta      | Medio         | Coincidencias en la web | Registros recuperados |
| ----------- | ------------- | ------------- | ----------------------: | --------------------: |
| Colombia    | biodiversidad | El Tiempo     |                  12.539 |                 1.487 |
| Colombia    | biodiversidad | El Espectador |                     585 |                   368 |
| Reino Unido | biodiversity  | The Guardian  |                   7.272 |                 2.000 |
| Reino Unido | biodiversity  | BBC           |                   2.742 |                 2.000 |
| Hungría     | biodiverzitás | Index         |                     243 |                   243 |
| Hungría     | biodiverzitás | Magyar Nemzet |                     153 |                   153 |
| Hungría     | biodiverzitás | Telex         |                      16 |                    16 |
| **Total**   |               |               |              **23.550** |             **6.267** |

Los resultados muestran que:

* En Colombia, *El Tiempo* presentó una cantidad de coincidencias considerablemente mayor que *El Espectador*.
* En Reino Unido, *The Guardian* concentró la mayor cantidad de noticias. La consulta de BBC reunió resultados de `bbc.co.uk` y `bbc.com`.
* En Hungría, *Index* presentó el mayor volumen entre los tres medios definidos. *Telex* mostró una cantidad reducida de registros para la búsqueda utilizada.

> **Importante:** la cantidad mostrada en la interfaz web no equivale necesariamente al número de noticias recuperadas mediante la API. Pueden existir diferencias por límites de descarga, organización de las páginas, disponibilidad de los registros y filtros aplicados durante la preparación de los datos.

## 6. Medios nacionales candidatos

Las búsquedas nacionales permitieron identificar los medios con mayor cantidad de noticias relacionadas con biodiversidad dentro de las colecciones de Media Cloud.

Estas cifras deben utilizarse como una orientación inicial y no como una selección definitiva de medios.

### 6.1 Colombia

| Medio candidato          | Coincidencias |
| ------------------------ | ------------: |
| Infobae                  |        19.752 |
| El Tiempo                |        12.539 |
| Extra                    |         6.736 |
| Diario del Sur           |         1.949 |
| HSB Noticias             |         1.918 |
| La República             |         1.724 |
| Diario La Libertad       |         1.234 |
| La Patilla               |           962 |
| Hoy Diario del Magdalena |           951 |
| Minuto30                 |           938 |

### 6.2 Reino Unido

| Medio candidato  | Coincidencias |
| ---------------- | ------------: |
| The Guardian     |         7.272 |
| The Independent  |         4.828 |
| The Conversation |         3.711 |
| Daily Mail       |         3.306 |
| Herald Scotland  |         1.835 |
| The Scotsman     |         1.407 |
| Evening Standard |         1.391 |
| Daily Express    |         1.344 |
| Daily Record     |         1.007 |
| WalesOnline      |           953 |

### 6.3 Hungría

| Medio candidato | Coincidencias |
| --------------- | ------------: |
| Portfolio       |           613 |
| HVG             |           312 |
| Index           |           243 |
| Origo           |           229 |
| InfoStart       |           171 |
| HAON            |           167 |
| BOON            |           163 |
| 24.hu           |           159 |
| Népszava        |           158 |
| Magyar Nemzet   |           153 |

> **Criterio de lectura:** una cifra alta indica que Media Cloud encontró una mayor cantidad de noticias relacionadas con la palabra consultada. Esto no demuestra por sí solo que el medio tenga alcance nacional, mayor calidad o mayor pertinencia para el proyecto DRAGONS.

## 7. Verificación de las exportaciones

| Exportación                     | Registros | Cobertura                                         | Observación                             |
| ------------------------------- | --------: | ------------------------------------------------- | --------------------------------------- |
| Medios definidos por los socios |     6.267 | Colombia: 1.855; Reino Unido: 4.000; Hungría: 412 | No se identificaron URL duplicadas      |
| Búsqueda nacional               |    18.518 | Colombia                                          | 17.140 relevantes y 1.378 no relevantes |

En la exportación de los medios definidos por los socios:

* 4.895 registros fueron marcados como relevantes.
* 960 fueron marcados como no relevantes.
* 412 no recibieron clasificación.

Los 412 registros sin clasificación corresponden a Hungría. Este resultado evidencia la necesidad de revisar con los expertos de dominio el vocabulario y los criterios aplicados al contenido en húngaro.

## 8. Limitaciones y consideraciones metodológicas

### 8.1 Cobertura de Media Cloud

La cantidad de noticias depende de los medios incorporados a Media Cloud y de la fecha desde la cual cada fuente comenzó a ser recopilada. Por esta razón, los resultados no representan necesariamente la totalidad de las publicaciones realizadas por cada medio.

### 8.2 Primera exploración mediante la palabra biodiversidad

La búsqueda basada únicamente en la palabra biodiversidad se utilizó como una primera exploración o “abrebocas” para conocer la disponibilidad de noticias y medios en cada país.

El equipo técnico ya cuenta con un listado más amplio de palabras clave. El objetivo de las siguientes recolecciones será utilizar ese vocabulario para recuperar la mayor cantidad posible de medios y artículos relacionados con el proyecto.

A medida que avance la recopilación, se podrán actualizar:

* Cantidad de noticias por país.
* Cantidad de noticias por medio.
* Distribución temporal.
* Palabras y temas encontrados.
* Muestras de artículos.
* Resultados de relevancia.
* Medios candidatos.

Estas métricas y muestras serán presentadas a los socios investigadores para validar su pertinencia. Si se requiere filtrar, excluir o incorporar un medio, la decisión podrá revisarse con el equipo técnico para ajustar la metodología y la recolección.

### 8.3 Definición de medio nacional

Las colecciones nacionales pueden incluir medios cuyo alcance supera un solo país. Por ejemplo, *Infobae* publica contenidos para Colombia, pero también cuenta con ediciones y cobertura en otros países de América Latina.

Por esta razón, es necesario definir qué se entenderá por “medio nacional” dentro del proyecto. Se pueden considerar, al menos, dos criterios:

1. Un medio es nacional cuando su origen y operación principal se encuentran en el país, como podría ocurrir con *El Tiempo* o *El Espectador* en Colombia.
2. Un medio puede considerarse dentro del ecosistema nacional cuando, aunque sea multinacional, publica noticias relacionadas directamente con el país.

> **Insumo requerido:** los socios investigadores deberán indicar cuál de estos criterios responde mejor a los objetivos del proyecto. Esta definición se incorporará como una actualización de la metodología de uso de Media Cloud.

### 8.4 Disponibilidad de contenido e interacciones

La recuperación de contenido, autores, comentarios y métricas de interacción dependerá de la estructura de cada medio y de la información pública disponible.

Por ello, el equipo técnico deberá evaluar cada portal y definir un proceso de extracción ajustado a sus características. No debe asumirse que todos los medios permitirán recuperar los mismos campos.

## 9. Recomendaciones

* Validar con los socios investigadores los medios candidatos, considerando su alcance, orientación editorial, relevancia temática, diversidad y disponibilidad histórica.
* Definir el criterio que permitirá clasificar una fuente como medio nacional o multinacional con cobertura nacional.
* Utilizar el listado ampliado de palabras clave preparado por el equipo técnico.
* Desarrollar y documentar un proceso de extracción para cada medio seleccionado.
* Actualizar periódicamente las métricas y las muestras conforme avance la recopilación.
* Presentar muestras de noticias a los socios para validar su pertinencia.
* Revisar con el equipo técnico cualquier solicitud de inclusión, exclusión o filtrado de medios.
* Documentar para cada ejecución las palabras utilizadas, los medios consultados, el periodo, la fecha y los filtros aplicados.

## 10. Conclusión

La evaluación permitió comprobar que Media Cloud es útil para reconocer fuentes, estimar el volumen potencial de noticias y verificar la presencia de los medios definidos por los socios dentro de las colecciones nacionales.

Los resultados constituyen una primera exploración y no representan todavía el corpus definitivo. La construcción del corpus requerirá ampliar las consultas con el vocabulario preparado por el equipo técnico, desarrollar procesos de extracción para los medios seleccionados y actualizar las métricas conforme se recuperen nuevos artículos.

La selección final de medios deberá realizarse conjuntamente con los socios investigadores. Sus criterios permitirán definir qué medios se consideran nacionales, cuáles deben incluirse o excluirse y qué contenidos son pertinentes para los objetivos del proyecto DRAGONS.

## Fuentes revisadas

* `Medios.docx`: capturas de las búsquedas en los medios definidos por los socios.
* `Medios nacionales.docx`: capturas de las búsquedas realizadas en las colecciones nacionales.
* `export_mediacloud.xlsx`: registros recuperados de los medios definidos.
* `export_mediacloud_national.xlsx`: registros disponibles de la búsqueda nacional.
* [Documentación de Media Cloud](https://www.mediacloud.org/documentation).
* [Guía de búsqueda de Media Cloud](https://www.mediacloud.org/documentation/search-tool-guide).
* [Guía de la API de Media Cloud](https://www.mediacloud.org/documentation/search-api-guide).
* [Preguntas frecuentes de Media Cloud](https://www.mediacloud.org/documentation/faqs).
