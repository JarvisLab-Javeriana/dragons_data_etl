# Docker — Quick Start

## 1. Configurar variables de entorno

Copia el archivo de ejemplo:

```bash
cp .env.example .env
```

Edita `.env` y agrega tus credenciales de MongoDB Atlas.

> No subas `.env` al repositorio.

## 2. Construir la imagen

Desde la raíz del proyecto:

```bash
docker compose build
```

## 3. Ejecutar consultas

```bash
docker compose run --rm query
```

## 4. Cargar `news.json` a MongoDB

```bash
docker compose run --rm loader
```

## 5. Ejecutar el scraper

```bash
docker compose run --rm scraper
```

Con argumentos, por ejemplo `--resume`:

```bash
docker compose run --rm scraper python news_extractor.py --resume
```

## 6. Si cambias el código

No necesitas reconstruir la imagen.

Solo vuelve a ejecutar el servicio correspondiente.

## 7. Si cambias dependencias

Si modificas `requirements.txt` o `Dockerfile`, reconstruye:

```bash
docker compose build
```

## Requisitos

Solo necesitas tener instalados:

- Docker
- Docker Compose

No necesitas crear `.venv` ni instalar Python o las librerías manualmente.
