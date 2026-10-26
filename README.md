# Tawseel Parcel API — DSC26 Software Engineering W2

Contract-first FastAPI service for creating, retrieving, listing, and updating parcel lifecycle state.

## Setup

Use Python 3.12 in a virtual environment, then install the pinned requirements:

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
pytest -q
```

Run locally with:

```bash
uvicorn app.api:app --reload
```

OpenAPI docs are available at `/docs` while the server is running.

## Endpoints

- `POST /v1/parcels` — create a parcel
- `GET /v1/parcels/{parcel_id}` — retrieve a parcel
- `GET /v1/parcels?state=&limit=&cursor=` — list parcels in creation order
- `POST /v1/parcels/{parcel_id}/events` — apply a lifecycle event

All error responses use `application/problem+json`.
