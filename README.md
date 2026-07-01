# IncidentIQ — AI-Assisted Incident Intelligence & Log Analysis

IncidentIQ ingests raw application logs and turns them into ranked, explained
incidents. A real analysis **engine** does the work — parsing, template mining,
clustering, frequency analysis, anomaly detection, severity scoring and
correlation. An LLM is used **only** to phrase the engine's structured output in
plain language, with a deterministic fallback so every feature works offline.

> **Thesis:** the detection engine is the product; the AI is an assistant. No log
> is ever sent to a model to "figure out what happened" — the engineering
> computes the analysis, and the model only explains it.

---

## Pipeline

```
Upload / sample  ─►  Parser  ─►  Normalization  ─►  Drain template mining
                                                          │
                                                          ▼
      Correlation  ◄─  Severity  ◄─  Anomaly  ◄─  Frequency  ◄─  Clustering
           │
           ▼
     Incidents  ─►  API  ─►  Dashboard · Explorer · Incident Detail
                                                    │
                                                    ▼
                                   AI explanation (Gemini or deterministic)
```

Everything left of the API is a pure, framework-independent Python package
(`backend/app/engine`) with no FastAPI or SQLAlchemy imports.

---

## The engine (the interesting part)

| Stage | File | What it does |
|---|---|---|
| **Parser** | `engine/parser.py` | Multi-format: NDJSON (flexible keys), structured text (`ts LEVEL service msg`, bracketed levels, syslog-ish), and a never-drop fallback. Synthetic monotonic clock for timestamp-less lines. |
| **Normalization** | `engine/normalize.py` | Ordered regex masking of variable tokens (UUID, IP, email, URL, duration, size, hex, path, number …) to typed sentinels, so `db-7 after 1423ms` and `db-3 after 88ms` collapse to one template. |
| **Template mining** | `engine/templates.py` | A from-scratch **Drain-inspired** miner: fixed-depth parse tree (length layer → prefix layers → leaf), similarity match against candidates, wildcard generalization on divergence. ~O(depth) per line vs O(n²) pairwise. |
| **Clustering** | `engine/clustering.py` | Lifts templates into enriched clusters (services, level, first/last seen, examples). |
| **Frequency** | `engine/frequency.py` | Buckets each cluster's events over the window; computes recent-vs-baseline rate and growth %. |
| **Anomaly** | `engine/anomaly.py` | Robust **peak detection**: median baseline, MAD/Poisson-floored scale, and a **√(2·ln n) scan correction** so the max over many buckets isn't fooled by normal noise. Flags active vs. resolved spikes. |
| **Severity** | `engine/severity.py` | Transparent weighted blend — anomaly (0.30), level (0.25), service criticality (0.15), volume (0.15), growth (0.10), breadth (0.05) → Critical/High/Medium/Low. Separate confidence signal from evidence strength. |
| **Correlation** | `engine/correlation.py` | Directed cause chains from a static service-dependency graph (+ temporal co-occurrence). Surfaces "checkout 5xx is downstream of DB pool exhaustion". |

Run it standalone:

```bash
cd backend
python -m app.data.generate_samples          # write sample datasets
python -c "from app.engine import pipeline; from pathlib import Path; \
  r=pipeline.analyze_text('demo', Path('app/data/samples/ecommerce-cascade.log').read_text()); \
  print(len(r.incidents), 'incidents,', len(r.correlations), 'correlations')"
```

---

## Stack

- **Backend:** FastAPI · SQLAlchemy (SQLite) · Pydantic · pure-Python engine.
- **Frontend:** React · Vite · TypeScript · Tailwind · Recharts.
- **AI:** Gemini (optional) via `google-generativeai`, with a deterministic
  rule-based explainer as fallback.

---

## API surface

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Liveness + whether AI is configured |
| `GET` | `/api/samples` · `POST /api/samples/{name}/load` | List / analyze bundled datasets |
| `POST` | `/api/logs/upload` | Analyze an uploaded file |
| `GET` | `/api/dashboard` | KPIs, timeline, health, top clusters, severity dist, insights |
| `GET` | `/api/incidents` | Filter by `severity` / `status` / `q` |
| `GET` | `/api/incidents/{id}` | Full detail: template, normalized log, stats, severity factors, correlation chain |
| `POST` | `/api/incidents/{id}/explain` | Generate explanation (Gemini or deterministic) |
| `GET` | `/api/incidents/export` | CSV export |
| `GET` | `/api/analytics` | Trends, cluster frequency, incident timeline |
| `GET`/`PUT` | `/api/settings` | Detection thresholds (wired into the engine) |

---

## Local development

**Backend** (http://localhost:8000):

```bash
cd backend
pip install -r requirements.txt          # or requirements-dev.txt for tests
python -m app.data.generate_samples
uvicorn app.main:app --reload --port 8000
```

**Frontend** (http://localhost:5173, proxies `/api` → :8000):

```bash
cd frontend
npm install
npm run dev
```

Open the app, click **Upload logs**, and load `ecommerce-cascade.log` to
reproduce the full incident board including the payments → checkout cascade.

To enable live Gemini explanations, set `GEMINI_API_KEY` in `backend/.env`
(copy from `.env.example`). Without it, the deterministic explainer is used.

---

## Testing

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q          # engine golden-fixture tests + API tests
```

Covers parsing formats, normalization stability, template grouping/merging,
cascade detection, severity ordering, resolved-incident detection, pipeline
determinism, and the full API surface.

---

## Deployment

Architecture: the browser calls same-origin `/api`, and Vercel rewrites those
requests to the Render backend server-side (`vercel.json`), so **no CORS is
exercised** in production and there is no build-time API URL to configure.

**Backend → Render** (`backend/render.yaml` blueprint):
- Create a Blueprint from this repo (Blueprint Path `backend/render.yaml`).
- Build generates the sample datasets; start runs uvicorn; health check is
  `/api/health`.
- `GEMINI_API_KEY` is optional (blank → deterministic explainer).
- Note your service's URL (e.g. `https://incidentiq-api-xxxx.onrender.com`) — it
  goes into `vercel.json` below. The backend also allows `*.vercel.app` via CORS
  (`CORS_ORIGIN_REGEX`) in case you prefer direct calls instead of the proxy.

**Frontend → Vercel** (`frontend/vercel.json`):
- Set the Vercel project's **Root Directory to `frontend`** (monorepo).
- In `vercel.json`, set the `/api/:path*` rewrite **destination** to your Render
  URL + `/api/:path*`. This is the one value to update per deployment.
- Do **not** set `VITE_API_BASE` in Vercel — leaving it unset makes the app use
  the same-origin `/api` proxy. (Set it only if you intentionally want direct
  cross-origin calls to Render instead of the proxy.)
- `vercel.json` builds the Vite app, serves `dist/`, and falls back all routes
  to `index.html` for client-side routing.

> **Data persistence:** the backend uses SQLite on Render's ephemeral free-tier
> disk, so uploaded runs reset on redeploy/cold start. On startup the app
> auto-seeds the `ecommerce-cascade` sample (via the real engine) if the database
> is empty, so a fresh deploy is never blank. Free instances also cold-start
> (~50s) after idle — the UI shows a "waking up" state and a Retry button.

## Live demo

- **App:** https://incident-iq-mu.vercel.app
- **API:** https://incidentiq-api-ozj5.onrender.com (`/api/health` for a liveness check)

> The backend runs on Render's free tier — the first request after idle may take
> ~50s to cold-start, and the app auto-seeds a sample analysis so it's never blank.

## Author

**Pranathi Vallamreddy** — [github.com/Pranathi-Vallamreddy](https://github.com/Pranathi-Vallamreddy)

---

## Deliberate scope choices

To keep the focus on engineering depth, some product surfaces are intentionally
simplified while preserving the experience: no authentication (single demo
workspace); Settings tabs other than **Detection** are presentational; the "Live"
badge reflects a batch analysis run rather than a streaming pipeline; report
Email/PDF use the browser print path. None of these touch the analysis engine,
which is the core of the project.
