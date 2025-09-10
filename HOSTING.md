Self‑host and one‑click cloud hosting

Overview
- The backend (FastAPI) now serves the built frontend directly. When the service is running, opening http://localhost:8000 loads the app.
- For a public link you can click from anywhere, deploy the Dockerized app to a PaaS (Render/Heroku/Railway). This repo includes a Dockerfile, Procfile (Heroku), and render.yaml (Render) so you can deploy with a few clicks.

Option A: Render (free tier)
1) Push this repo to GitHub or GitLab.
2) Visit https://render.com and click “New +” → “Blueprint”.
3) Choose your repository (render.yaml is detected). Click “Deploy”.
4) After the build, Render gives you a public URL like https://price-optim-ai-backend.onrender.com.
   - Open that link — the UI is served from the same origin and just works.
   - If you want a custom name, edit “name” in render.yaml before deploying.

Option B: Heroku (free hobby dyno)
1) Push to GitHub and create a new Heroku app.
2) Add the GitHub connection and deploy. Procfile is detected automatically.
3) Open the app URL (e.g., https://yourapp.herokuapp.com).

Option C: Docker (local)
1) Install Docker Desktop.
2) Using docker compose (recommended):
   docker compose up --build -d
   docker compose logs -f  # watch startup logs
   Open http://localhost:8000

   The container writes exports to product_data/ on your host.

   Or using plain Docker:
   docker build -t price-optim-ai .
   docker run --rm -p 8000:8000 -v ${PWD}/product_data:/app/product_data price-optim-ai
   Open http://localhost:8000

Notes
- The app defaults to SQLite if no external storage env vars are provided.
- For Google Sheets/Airtable/Postgres, set env vars on your hosting provider as needed.
- The backend already enables CORS for common dev origins and serves the SPA from / (including /assets).
