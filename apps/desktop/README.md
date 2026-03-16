# Desktop MVP (Electron Hybrid)

This MVP implements the first hybrid desktop flow:

1. User selects a local `.zip` event log (400MB+ supported based on machine capacity).
2. Electron calls the bundled local backend (`server.exe`) to reduce the ZIP.
3. App sends only the reduced report plus optional `.py` files to backend API (`/api/upload-reduced`).
4. Backend runs LLM analysis asynchronously.

## Run

```bash
cd apps/desktop
npm install
npm start
```

## Notes

- End users do not need Python installed. The desktop installer bundles `server.exe`.
- Python is required only for local development (`npm start`) because dev mode runs `python -m backend.app`.
- ZIP file never leaves the local machine in the reduction step; only the reduced report is sent for analysis.
