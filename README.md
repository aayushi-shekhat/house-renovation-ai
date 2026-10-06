# AI-Based Exterior House Renovation & Cost Estimation System

This repository contains a runnable prototype for exterior house renovation planning. It preserves the original upload and validation pipeline, then continues through region review, material assignment, deterministic estimation, editable rates, a material-color preview, and a PDF report.

## Prerequisites

- Python 3.11+
- Node.js 20+ and npm
- PostgreSQL 15+ with the `postgres` user and a local database server

Docker is optional. The current Windows setup uses the official PostgreSQL installer.

## Windows local setup

1. Install PostgreSQL from the official Windows installer: <https://www.postgresql.org/download/windows/>. Keep the default port `5432`, remember the password chosen for the `postgres` user, and allow the installer to register the PostgreSQL Windows service.
2. Open a new PowerShell window and verify the client/service:

```powershell
psql --version
Get-Service *postgres*
```

Start the service if it is installed but stopped. The service name varies by version, so use the name returned by `Get-Service`:

```powershell
Start-Service postgresql-x64-16
```

3. From the repository root, create and activate the Python environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Set-Location frontend
npm install
Set-Location ..
```

4. Configure the local environment. The repository includes an ignored `.env` with safe local defaults. If it is missing, copy the template:

```powershell
Copy-Item .env.example .env
```

Set `DATABASE_URL` to the password selected during PostgreSQL installation:

```text
DATABASE_URL=postgresql+psycopg://postgres:<your-password>@localhost:5432/house_renovation
```

5. Create the database once. This does not drop or recreate an existing database:

```powershell
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE house_renovation;"
```

If PostgreSQL reports that the database already exists, continue.

6. Apply Alembic migrations:

```powershell
\.venv\Scripts\alembic.exe upgrade head
```

7. Start the backend:

```powershell
$env:PYTHONPATH = "backend"
\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

The API is available at `http://localhost:8000`. The frontend remains a separate process:

```powershell
Set-Location frontend
npm run dev
```

## Configure

`.env` is ignored by Git. Do not commit database passwords or API keys. `DATABASE_URL` must be a PostgreSQL URL; `postgres://...` and `postgresql://...` are normalized to the psycopg SQLAlchemy driver automatically.

## Deployment

### Frontend

Deploy the `frontend` directory to Vercel. Vercel builds the Vite application with `npm run build` and serves the generated `dist` directory.

### Backend

Deploy the repository root as a Render Python web service. The included `render.yaml` provisions the API service and a PostgreSQL database when Blueprint deployment is available.


From the repository root:

Deploy the repository root to Vercel. The root `vercel.json` configures two services in one project: the Vite frontend and the FastAPI API. The frontend is public at `/`, while API requests under `/api/` are routed to the API service. The API service remains internal except for that rewrite.
py -3.12 -m venv .venv
The frontend uses same-origin `/api/v1` requests in production. Set `VITE_API_BASE_URL=http://localhost:8000` only for local development when the Vite dev server and API run on separate ports.
.\.venv\Scripts\Activate.ps1
The API still requires a PostgreSQL `DATABASE_URL` and any optional provider/storage variables listed below. Run the Alembic migration as part of the API deployment or from a deployment shell.
python -m pip install -e ".[dev]"
\.venv\Scripts\alembic.exe upgrade head
2. Import the repository into Vercel with the repository root as the project root.
\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
3. Configure the API service environment variables, including `DATABASE_URL`, `CORS_ORIGINS`, and any optional provider keys. Leave `OPENAI_API_KEY` empty to use the deterministic preview fallback.
In a second terminal:
4. Run the production migration from the API service shell or deployment command:
```powershell
5. Verify `/api/v1/health`, `/api/v1/health/db`, and `/docs` on the Vercel domain.
npm install
 `VITE_API_BASE_URL`: optional frontend API base URL; defaults to same-origin `/api/v1` in production.
```
 `VITE_API_BASE_URL`: optional frontend API base URL, defaulting to same-origin `/api/v1`; use `http://localhost:8000` for the separate local Vite/API setup.
### Production environment variables

Backend:

- `APP_NAME`
- `ENVIRONMENT`
- `DATABASE_URL`
- `STORAGE_ROOT`
- `CORS_ORIGINS`
- `OPENAI_API_KEY`
- `OPENAI_IMAGE_MODEL`
- `YOLOE_MODEL_PATH`
- `MAX_UPLOAD_BYTES`
- `MIN_IMAGE_WIDTH`
- `MIN_IMAGE_HEIGHT`
- `MAX_IMAGE_WIDTH`
- `MAX_IMAGE_HEIGHT`
- `MAX_IMAGE_ASPECT_RATIO`

Frontend:

- `VITE_API_BASE_URL`

### Deployment steps

1. Push the repository to GitHub without `.env`, `data/assets`, `.venv`, or `frontend/node_modules`.
2. In Render, create a Blueprint from the GitHub repository and select `render.yaml`, or create a Python web service manually with the configuration below.
3. In Render, provide `CORS_ORIGINS` temporarily as the Vercel URL after the frontend is created. Leave `OPENAI_API_KEY` empty to use the deterministic preview fallback.
4. In Vercel, import the same GitHub repository, set the root directory to `frontend`, and set `VITE_API_BASE_URL` to the Render API URL ending in `/api/v1`.
5. Run the production migration from the Render service shell or deploy command:

```bash
alembic upgrade head
```

6. Set Render `CORS_ORIGINS` to the final HTTPS Vercel URL, redeploy the backend, and verify `/api/v1/health`, `/api/v1/health/db`, and `/docs`.

### Assessment Workflow

Upload → Validation → Region Review → Material Assignment → Renovation Preview → Measurement → Estimate → Report

### Prototype Limitations

- Measurements are visual and approximate, not survey-grade.
- Output and costs are advisory, not contractual.
- No structural engineering or safety certification is performed.
- The prototype supports exterior renovation only.
- Generated designs preserve the existing structure as an approximation.
- Costs depend on the configured material and labor rates.
- Single-image measurements are estimates.
- Assets use local filesystem storage. On Render's ephemeral filesystem, uploaded images, previews, and PDFs can be lost after a redeploy or service restart; this is acceptable for a short-lived assessment demo.
- OpenAI image editing is optional; without `OPENAI_API_KEY`, the deterministic material-color preview remains available.

## Database and migrations

The expected local database is `house_renovation`, using the `postgres` database user. Create it with `psql` as shown above, then run:

```powershell
\.venv\Scripts\alembic.exe upgrade head
```

The migration creates projects, image assets, region revisions, material catalog data, assignments, measurements, estimates, renders, and reports. Future schema changes should use generated, reviewed Alembic revisions.

Alembic reads the same `DATABASE_URL` as the application through `backend/alembic/env.py`; credentials are not stored in `alembic.ini`.

## Run the backend

```powershell
$env:PYTHONPATH = "backend"
\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

Health checks: `GET http://localhost:8000/api/v1/health` and `GET http://localhost:8000/api/v1/health/db`.

## Configuration

Important environment variables:

- `DATABASE_URL`: PostgreSQL connection string.
- `STORAGE_ROOT`: local filesystem directory for image, preview, and PDF assets.
- `MAX_UPLOAD_BYTES`, `MAX_IMAGE_WIDTH`, `MAX_IMAGE_HEIGHT`: upload limits.
- `YOLOE_MODEL_PATH`: optional local YOLOE model path. When unavailable, analysis returns an empty manual region set.
- `OPENAI_API_KEY`: optional image-editing key. When absent or unavailable, rendering uses the deterministic material-color fallback.
- `OPENAI_IMAGE_MODEL`: optional OpenAI image model name.
- `VITE_API_BASE_URL`: frontend API base URL, defaulting to `http://localhost:8000/api/v1`.

## Upload an image

Create a project in PostgreSQL, then send a multipart request to:

```text
POST /api/v1/projects/{project_id}/images
```

The upload field is named `file`. JPEG/JPG, PNG, and WEBP are supported. The API validates the extension, declared MIME type, file signature, decodability, file size, dimensions, aspect ratio, and basic image quality. EXIF orientation is normalized into an RGB PNG processing copy while the original upload is preserved unchanged. A successful response includes the image ID, both asset IDs, dimensions, validation status, and any warnings.

Local storage writes originals and processing copies under `STORAGE_ROOT` using generated project/image keys; user filenames are never used as paths. Image binaries are not stored in PostgreSQL.

Upload behavior is covered by the integration suite:

```powershell
pytest backend/tests/integration/test_image_upload.py
```

The frontend upload screen uses the same endpoint and sends the selected file in the `file` multipart field. Set `VITE_API_BASE_URL` when the API is not at `http://localhost:8000/api/v1`.

## Workflow endpoints

- `POST /api/v1/projects`
- `POST /api/v1/projects/{project_id}/images`
- `POST /api/v1/images/{image_id}/analysis`
- `GET /api/v1/images/{image_id}/regions`
- `POST /api/v1/region-sets/{region_set_id}/regions`
- `PATCH /api/v1/regions/{region_id}`
- `DELETE /api/v1/regions/{region_id}`
- `POST /api/v1/region-sets/{region_set_id}/approve`
- `GET /api/v1/materials`
- `POST /api/v1/design-revisions/{design_revision_id}/assignments`
- `GET /api/v1/design-revisions/{design_revision_id}/assignments`
- `POST /api/v1/design-revisions/{design_revision_id}/measurements`
- `POST /api/v1/design-revisions/{design_revision_id}/estimates`
- `PATCH /api/v1/estimates/{estimate_id}/rates`
- `POST /api/v1/design-revisions/{design_revision_id}/render`
- `POST /api/v1/estimates/{estimate_id}/report`
- `GET /api/v1/assets/{asset_id}`

## Run tests

```powershell
\.venv\Scripts\python.exe -m pytest
\.venv\Scripts\python.exe -m compileall -q backend/app
Set-Location frontend
npm run build
Set-Location ..
```

## Optional Docker Compose database

Docker is not required for the current Windows setup. On a machine with Docker Desktop, the included `infra/docker-compose.yml` starts only PostgreSQL with the same local database, user, password, and port:

```powershell
docker compose -f infra/docker-compose.yml up -d
\.venv\Scripts\alembic.exe upgrade head
```

Stop it with `docker compose -f infra/docker-compose.yml down`.

## Troubleshooting

- **`psql` is not recognized:** install PostgreSQL using the official installer and open a new PowerShell window so its `bin` directory is on `PATH`.
- **No PostgreSQL service or connection refused on `localhost:5432`:** start the versioned service returned by `Get-Service *postgres*`, or rerun the installer with the server component selected.
- **Password authentication failed:** update `DATABASE_URL` with the password chosen for the local `postgres` user. Do not put the password in `alembic.ini`.
- **Database does not exist:** run `psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE house_renovation;"`.
- **Port `5432` is already in use:** identify the owning process with `Get-NetTCPConnection -LocalPort 5432`; either stop the conflicting service or change PostgreSQL's port and the port in `DATABASE_URL`.
- **API port `8000` is already in use:** start Uvicorn with `--port 8001` and set `VITE_API_BASE_URL` accordingly before starting the frontend.

## Prototype assumptions and limitations

- YOLOE is an optional adapter; model inference is not required for the manual workflow. SAM 2 is represented by the retained provider contract but is not bundled.
- OpenAI image editing is an optional provider boundary. The current render path always remains usable through deterministic translucent material overlays.
- Measurements are manual square-foot entries unless reference pixels and feet are supplied. Results are advisory and do not claim structural, contractor, or tax accuracy.
- Storage is local filesystem storage. There is no Redis, Celery, PostGIS, authentication, multi-user authorization, or production deployment configuration.
- The frontend is a compact prototype workflow rather than a full design editor; pan, advanced polygon editing, and server-side image serving authorization remain out of scope.

## Demo flow

1. Start PostgreSQL, run `alembic upgrade head`, and start the API.
2. Start the frontend with `npm run dev`.
3. Create a project and upload a JPEG, PNG, or WEBP house image.
4. Validate it, run optional analysis, add or edit polygons, and approve the region set.
5. Assign seeded compatible materials, enter manual areas, generate a preview, and calculate the estimate.
6. Edit rates and download the generated PDF report.
