# English Flashcards (MVP2)

App web para estudiar inglés con flashcards (frases/vocabulario), con **frontend React + TypeScript (Vite)**, **backend Python + FastAPI**, y **PostgreSQL en Docker**.

## Demo local (UI)

- Frontend: `http://localhost:5173`
- Vista principal: práctica con flashcards, selector de tópicos, búsqueda, audio (“Listen / Listen example”), etc.

---

## Arquitectura (alto nivel)

**React (Vite)** → **API (FastAPI)** → **PostgreSQL (Docker)**

### Base de datos (PostgreSQL)

Actualmente existen estas tablas principales:

- `entries` (flashcards / frases / vocabulario)
- `examples` (ejemplos asociados a entries)
- `topics` (tópicos/categorías)
- `topic_entries` (tabla puente topic ↔ entry)

> Nota: el contenedor de Postgres suele llamarse `english_db` (según `docker-compose.yml`).

---

## Estructura del repo (orientativa)

- `english-flashcards-frontend/` → Frontend (React + TS + Vite)
  - `src/pages/MainFlashcard.tsx` (pantalla principal de flashcards)
  - `src/pages/Landing.tsx` (landing)
  - `src/api/` (cliente / llamadas a backend)
  - `src/components/` (componentes UI)
  - `src/styles.css` y estilos inline en algunos componentes
- `english-flashcards-backend/` → Backend (Python + FastAPI)
  - `main.py` (entrypoint típico de FastAPI)
  - módulos de rutas/servicios/modelos (según la implementación actual)
- `docker-compose.yml` → Postgres (y opcionalmente backend/frontend si está dockerizado)
- `.env` → variables locales (NO commitear). Usa `.env.example`.

Si algún path cambia, actualiza esta sección para mantenerla como “fuente de verdad”.

---

## Requisitos

- Node.js (recomendado LTS)
- Python 3.10+ (o la versión que uses en backend)
- Docker + Docker Compose

---

## Variables de entorno

Crea un `.env` en la raíz o en cada subproyecto (según el setup actual). Ejemplo:

### `.env.example`

```bash
# Postgres (Docker)
POSTGRES_USER=english
POSTGRES_PASSWORD=english
POSTGRES_DB=english

# Backend
DATABASE_URL=postgresql://english:english@localhost:5432/english
# (si usas otra forma de config, agrega aquí tus variables reales)

# Frontend (si aplica)
VITE_API_BASE_URL=http://localhost:8000
```

## Instrucciones utiles

1. Levantar Postgres con Docker

Desde la raíz del repo:

docker compose up -d

Verifica contenedor:

docker ps

Conectar a la DB:

docker exec -it english_db psql -U english

Listar tablas:

\dt

2. Levantar el backend (FastAPI)

En una terminal:

cd english-flashcards-backend
python -m venv .venv

# Windows:

.venv\Scripts\activate

# macOS/Linux:

source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

API: http://localhost:8000

Docs: http://localhost:8000/docs

Si el entrypoint no es main:app, ajusta el comando según tu archivo/app real.

3. Levantar el frontend (Vite + React)

En otra terminal:

cd english-flashcards-frontend
npm install
npm run dev

App: http://localhost:5173

Comandos de calidad (antes de hacer PR / merge)
Frontend
cd english-flashcards-frontend
npm run build
npm run lint
