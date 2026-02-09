# English Flashcards (MVP2)

App web para estudiar ingles con flashcards de frases y vocabulario. Incluye practica por temas, busqueda y audio. Frontend React (Vite), backend FastAPI y base de datos Postgres en Docker.

## Que puedes hacer

- Practicar flashcards con frases y vocabulario
- Filtrar por topicos
- Buscar palabras o frases
- Escuchar pronunciacion y ejemplos

## Stack

- Frontend: React + TypeScript + Vite
- Backend: Python + FastAPI
- Base de datos: PostgreSQL (Docker)

## Inicio rapido (local)

1. Levanta Postgres con Docker

```bash
docker compose up -d
docker ps
```

2. Levanta el backend (FastAPI)

```bash
cd english-flashcards-backend
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API: `http://localhost:8000`
Docs: `http://localhost:8000/docs`

3. Levanta el frontend (Vite + React)

```bash
cd english-flashcards-frontend
npm install
npm run dev
```

App: `http://localhost:5173`

## Variables de entorno

Crea un archivo `.env` si lo necesitas. Ejemplo:

```bash
# Postgres (Docker)
POSTGRES_USER=english
POSTGRES_PASSWORD=english
POSTGRES_DB=english

# Backend
DATABASE_URL=postgresql://english:english@localhost:5432/english

# Frontend
VITE_API_BASE_URL=http://localhost:8000
```

## Estructura del repo (resumen)

- `english-flashcards-frontend/` frontend React
- `english-flashcards-backend/` backend FastAPI
- `docker-compose.yml` Postgres
