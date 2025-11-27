# Rainwater Harvesting — Backend

This repository contains the backend API for the Rainwater Harvesting project (FastAPI + MongoDB).

**Overview**
- **Stack:** `FastAPI`, `Uvicorn`, `PyMongo` (MongoDB), `pydantic-settings` for configuration
- **API base path:** `/api/v1` (routes for auth, rainfall, projects)

**Quick Start**

1. Clone the repository

```bash
git clone https://github.com/SouravKumarBarman/rainwater-harvesting-backend.git
cd rainwater-harvesting-backend
```

2. Install dependencies with `uv`

```bash
uv sync
```

This creates a `.venv` and installs all dependencies from `pyproject.toml`.

3. (Optional) Activate the virtual environment

```bash
source .venv/bin/activate
```

Or simply prefix commands with `uv run` to use the environment without activating.

**Configuration / Environment**

The project uses `pydantic-settings` and reads a `.env` file (see `app/config.py`). Create a `.env` in the project root with the values your environment requires. Example:

```env
# MongoDB connection string
MONGODB_URL=mongodb://localhost:27017

# Optional: weather API key used by rainfall services
WEATHER_API_KEY=your_weather_api_key_here

# Port the server should run on (default in settings: 8000)
PORT=8000
```

Note: The keys above correspond to the Pydantic settings fields:
- `mongodb_url`
- `weather_api_key`
- `port`

**Run (Development)**

Start the app using `uv run` (recommended) from the project root:

```bash
uv run fastapi dev app/main.py
```

Or with `uvicorn` directly:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit the interactive API docs at `http://localhost:8000/docs` when the server is running.

**MongoDB ObjectId usage**

When querying by MongoDB `_id`, convert string IDs to `ObjectId` (from the `bson` package). Example used in the codebase (see `app/services/user_services.py`):

```python
from bson import ObjectId
user = await users_collection.find_one({"_id": ObjectId(user_id_str)})
```

If the string is not a valid ObjectId, handle `bson.errors.InvalidId` and return a `400` error to the client.

**Project Structure (important files)**

- `app/main.py` — FastAPI application factory and router registration
- `app/config.py` — Pydantic settings and environment config
- `app/api/v1` — API route modules (`auth.py`, `rainfall.py`, `project_routes.py`)
- `app/services` — Business logic and helpers (e.g., `user_services.py`, `rainfallService.py`)
- `app/db/dbConnect.py` — MongoDB connection utilities

**Notes and troubleshooting**

- If you see a circular import error involving `oauth2_scheme`, it may be because a router imports something that imports `app.main`. The project places `oauth2_scheme` in `app/utils/authUtils.py` to avoid that. Keep auth helpers in a separate module.
- Ensure MongoDB is running and reachable at the `MONGODB_URL` you provide.
- If you get dependency issues, run `uv sync` again and check your Python version (the project lists `requires-python = ">=3.14"` in `pyproject.toml`).

**Next steps / Suggestions**

- Add a `tests/` folder and a `pytest` configuration to enable automated testing.
- Add CI (GitHub Actions) to run linting and tests on push/PRs.
- Provide Postman/Insomnia collection or example requests for the main endpoints.

If you want, I can:
- Add example `.env` to the repo (ignored by git via `.gitignore`),
- Add a simple `Makefile` with common tasks,
- Or update docs with example API requests for auth and project endpoints.

---

If you'd like any of the optional additions, tell me which and I'll add them.
