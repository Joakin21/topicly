# English Flashcards (MVP2)

App web para estudiar ingles con flashcards de frases y vocabulario. Incluye practica por temas, busqueda, audio y login con Google. Frontend React (Vite), backend FastAPI y base de datos Postgres en Docker.

## Que puedes hacer

- Practicar flashcards con frases y vocabulario
- Filtrar por topicos
- Buscar palabras o frases
- Escuchar pronunciacion y ejemplos
- Iniciar sesion con Google
- Cerrar sesion de forma segura (cookie HttpOnly)

## Stack

- Frontend: React + TypeScript + Vite
- Backend: Python + FastAPI
- Base de datos: PostgreSQL (Docker)
- Auth: Google Identity Services + sesiones en backend

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

## Autenticacion Google (local)

### 1) Configurar OAuth client en Google Cloud

En Google Cloud Console:

1. Ve a `Google Auth Platform`.
2. En `Clients`, crea un OAuth Client tipo `Web application`.
3. En `Authorized JavaScript origins` agrega:
   - `http://localhost:5173`
   - `http://127.0.0.1:5173`
4. En `Audience`, deja `Testing` y agrega tu correo en `Test users`.
5. Copia el `Client ID` (termina en `.apps.googleusercontent.com`).

### 2) Configurar variables

Backend (misma terminal donde inicias FastAPI):

```powershell
$env:GOOGLE_CLIENT_ID="tu_client_id.apps.googleusercontent.com"
$env:FRONTEND_ORIGINS="http://localhost:5173"
$env:AUTH_COOKIE_SECURE="false"
```

Frontend (`english-flashcards-frontend/.env`):

```env
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=tu_client_id.apps.googleusercontent.com
```

Importante: cuando cambies variables en `.env`, reinicia `npm run dev`.

## Variables de entorno

Crea un archivo `.env` si lo necesitas. Ejemplo:

```bash
# Postgres (Docker)
POSTGRES_USER=english
POSTGRES_PASSWORD=english
POSTGRES_DB=english

# Backend
DATABASE_URL=postgresql+psycopg://english:english@localhost:5432/english
GOOGLE_CLIENT_ID=tu_client_id.apps.googleusercontent.com
FRONTEND_ORIGINS=http://localhost:5173
AUTH_COOKIE_SECURE=false
SESSION_TTL_DAYS=30

# Frontend
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=tu_client_id.apps.googleusercontent.com
```

## Base de datos (auth)

Ademas de las tablas de flashcards (`entries`, `examples`, `topics`, `topic_entries`), el backend usa:

- `users`
- `user_sessions`

Estas tablas se crean automaticamente al iniciar el backend (si no existen).

## Endpoints de autenticacion

- `POST /auth/google`
- `GET /auth/me`
- `POST /auth/logout`

## Troubleshooting rapido

- Error `The given origin is not allowed for the given client ID`:
  revisa `Authorized JavaScript origins` en Google Cloud y asegurate de incluir exactamente el origen usado (`localhost` vs `127.0.0.1`, puerto correcto).
- `GET /auth/me 401` al cargar login o despues de logout:
  comportamiento esperado cuando no hay sesion activa.
- En desarrollo puedes ver 2 llamadas a `/auth/me` por `React.StrictMode`.

## Produccion

- Usa HTTPS.
- Configura `AUTH_COOKIE_SECURE=true`.
- Ajusta `FRONTEND_ORIGINS` al dominio real de frontend.
- No expongas ni uses `Client Secret` en frontend.

## Estructura del repo (resumen)

- `english-flashcards-frontend/` frontend React
- `english-flashcards-backend/` backend FastAPI
- `docker-compose.yml` Postgres
