from fastapi import APIRouter, Body, status, Cookie
from fastapi.exceptions import HTTPException
from app.models.userModel import registerUserModel, userOut, UserInDB
from app.db.dbConnect import get_user_collection
from app.utils.authUtils import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from fastapi.responses import JSONResponse
from typing import Annotated
from fastapi.security import  OAuth2PasswordRequestForm
from fastapi import Depends
from ...services.user_services import get_current_user

router = APIRouter()


############################ Register User ############################
@router.post(
    "/register", description="Register a new user", status_code=status.HTTP_201_CREATED
)
async def register_user(payload: registerUserModel = Body(...)):
    # check if user already exists
    user_collection = await get_user_collection()
    existing_user = await user_collection.find_one({"email": payload.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User already exists"
        )

    # Hash the password before storing
    payload.password = hash_password(payload.password)

    #  Prepare the document for insertion using the UserInDB structure
    user_db_data = UserInDB(
        email=payload.email,
        username=payload.username,
        hashed_password=payload.password
    )
    user_dict = user_db_data.model_dump(by_alias=True, exclude={"id"})

    # Create a new user
    insert_result=await user_collection.insert_one(user_dict)
    new_user_doc = await user_collection.find_one({"_id": insert_result.inserted_id})
    return userOut.model_validate(new_user_doc)


############################# Login User ############################


@router.post(
    "/login",
    response_description="User Login",
    status_code=status.HTTP_200_OK,
)
async def login_user(logindata: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user_collection = await get_user_collection()
    # verfiy if user exists
    user = await user_collection.find_one({"email": logindata.username})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password"
        )
    if not verify_password(logindata.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password"
        )
    # return jwt token or session info here in real application
    user_id_str = str(user["_id"])
    access_token = create_access_token(data={"sub": user_id_str})
    refresh_token = create_refresh_token(data={"sub": user_id_str})
    # save refresh token in db
    await user_collection.update_one(
        {"email": logindata.username}, {"$set": {"refresh_token": refresh_token}}
    )
    response = JSONResponse(
        content={"message": "Login successful", "access_token": access_token, "token_type": "bearer"}
    )
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    return response


############################## Logout User ############################


@router.post(
    "/logout",
    description="User Logout",
    status_code=status.HTTP_200_OK,
)
async def logout_user(refresh_token: str = Cookie(None)):
    user_col = await get_user_collection()

    decoded = decode_refresh_token(refresh_token)
    email = decoded["sub"]

    # remove refresh token
    await user_col.update_one({"email": email}, {"$unset": {"refresh_token": ""}})

    return {"message": "Logged out successfully"}


############################## Refresh Token ############################


@router.post("/refresh")
async def refresh(refresh_token: str = Cookie(None)):
    user_col = await get_user_collection()

    decoded = decode_refresh_token(refresh_token)
    email = decoded["sub"]

    user = await user_col.find_one({"email": email})

    if not user or user.get("refresh_token") != refresh_token:
        raise HTTPException(401, "Invalid refresh token")

    new_access = create_access_token({"sub": email})
    new_refresh = create_refresh_token({"sub": email})

    # update refresh token
    await user_col.update_one(
        {"email": email}, {"$set": {"refresh_token": new_refresh}}
    )
    response = JSONResponse(content={"message": "Token refreshed successfully"})
    response.set_cookie(key="access_token", value=new_access, httponly=True)
    response.set_cookie(key="refresh_token", value=new_refresh, httponly=True)
    return response


############################# Change Password ############################

# @router.post("/change-password")
# async def change_password(
#     payload: changePasswordModel,
#     token: str = Depends(oauth2_scheme)
# ):
#     user_col = await get_user_collection()

#     from app.auth.jwt_handler import decode_access_token
#     decoded = decode_access_token(token)
#     email = decoded["sub"]

#     user = await user_col.find_one({"email": email})

#     if not verify_password(payload.old_password, user["password"]):
#         raise HTTPException(400, "Old password is incorrect")

#     new_hashed = hash_password(payload.new_password)

#     await user_col.update_one(
#         {"email": email},
#         {"$set": {"password": new_hashed}}
#     )
#     return {"message": "Password changed successfully"}


@router.get("/current-user")
async def current_user_route(current_user=Depends(get_current_user)):
    return current_user
