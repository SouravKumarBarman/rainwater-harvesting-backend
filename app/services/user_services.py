from fastapi import  HTTPException, Depends
from bson import ObjectId
from bson.errors import InvalidId
from app.models.userModel import userOut
from app.db.dbConnect import get_user_collection
from app.utils.authUtils import decode_access_token, oauth2_scheme

async def get_current_user(token: str = Depends(oauth2_scheme))->userOut:
    user_col = await get_user_collection()
    decoded = decode_access_token(token)
    user_id = decoded.get("sub")
    print("Decoded user ID:", user_id)
    try:
        object_id = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(400, "Invalid user ID format")
    user = await user_col.find_one(
        {"_id": object_id},
        {"password": 0, "refresh_token": 0, "created_at": 0, "updated_at": 0},
    )
    if user:
        user = userOut.model_validate(user)
    else:
        user = None
    if not user:
        raise HTTPException(404, "User not found")
    return user