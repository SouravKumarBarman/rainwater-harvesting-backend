from contextlib import asynccontextmanager
from fastapi import FastAPI
from .api.v1 import users
from .api.v1 import auth
from .db import dbConnect

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to the database
    await dbConnect.connect_db()
    yield
    # Shutdown: Disconnect from the database
    await dbConnect.disconnect_db()


app = FastAPI(title="Rainwater Harvesting API", version="1.0.0", lifespan=lifespan)



app.include_router(users.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")



@app.get("/")
async def root():
    return {"message": "Hello World"}
