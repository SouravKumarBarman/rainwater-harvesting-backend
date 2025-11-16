from fastapi import FastAPI
from .api.v1 import users
from .api.v1 import auth

app = FastAPI()

app.include_router(users.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")



@app.get("/")
async def root():
    return {"message": "Hello World"}
