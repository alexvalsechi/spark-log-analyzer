# Spark Log Analyzer - Electron Hybrid Branch

This branch contains only the Electron-hybrid context.

## Scope

- Desktop app in `desktop/` handles local ZIP ingestion and local Python reduction.
- Backend in `backend/` is API/governance for OAuth2, usage policy points, and LLM processing from reduced logs.
- No web SPA frontend is part of this branch.

## Runtime Flow

1. User selects ZIP locally in Electron.
2. Electron runs Python reducer locally and generates `reduced_report`.
3. Electron sends only `reduced_report` + optional `.py` files to `POST /api/upload-reduced`.
4. Backend enqueues async LLM analysis and returns `job_id`.

## Run Backend

```bash
docker compose up -d
```

## Run Desktop

```bash
cd desktop
npm install
npm start
```
