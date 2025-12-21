from functools import lru_cache
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1 import auth, rainfall, project_routes
from .db import dbConnect
from . import config

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to the database
    await dbConnect.connect_db()
    yield
    # Shutdown: Disconnect from the database
    await dbConnect.disconnect_db()


app = FastAPI(title="Rainwater Harvesting API", version="1.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change "*" to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@lru_cache
def get_settings():
    return config.Settings()

app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(rainfall.router, prefix="/api/v1/rainfall")
app.include_router(project_routes.router, prefix="/api/v1/projects")
