from fastapi import APIRouter
router = APIRouter()

@router.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id, "name": f"User {user_id}"}