from fastapi import APIRouter

router = APIRouter()

@router.post("/login")
async def login(username: str, password: str):
    # Dummy authentication logic
    if username == "admin" and password == "secret":
        return {"message": "Login successful"}
    return {"message": "Invalid credentials"}

@router.post("/register")
async def register(username: str, password: str):
    # Dummy registration logic
    return {"message": f"User {username} registered successfully"}

@router.post("/logout")
async def logout():
    # Dummy logout logic
    return {"message": "Logout successful"}

