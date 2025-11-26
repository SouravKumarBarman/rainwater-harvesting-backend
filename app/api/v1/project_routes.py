from fastapi import APIRouter, HTTPException
from datetime import datetime
from bson import ObjectId
from fastapi import Depends

from app.db.dbConnect import db
from app.models.project_model import RooftopInput, HarvestResult, ProjectCreate
from app.services.calculations import calculate_harvest
from ...services.user_services import get_current_user

router = APIRouter()

def objid_to_str(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

@router.post("/calculate", response_model=dict)
async def calculate_and_create_project(payload: ProjectCreate, current_user: dict = Depends(get_current_user)):
    # 1. Run calculations
    result: HarvestResult = calculate_harvest(payload.input)

    # 2. Save to MongoDB
    project_doc = {
        "user_id": ObjectId(current_user["_id"]), 
        "input": payload.input.model_dump(),
        "result": result.model_dump(),
        "created_at": datetime.utcnow(),
    }

    res = await db["projects"].insert_one(project_doc)
    project_doc["_id"] = res.inserted_id

    return {
        "project_id": str(res.inserted_id),
        "result": result,
    }

@router.get("/{project_id}")
async def get_project(project_id: str, current_user: dict = Depends(get_current_user)):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID.")

    project = await db["projects"].find_one(
        {"_id": ObjectId(project_id), "user_id": ObjectId(current_user["_id"])}
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or unauthorized.")

    project["_id"] = str(project["_id"])
    project["user_id"] = str(project["user_id"])
    return project

@router.get("/", summary="List all projects")
async def list_projects(limit: int = 20, skip: int = 0):
    cursor = db["projects"].find().skip(skip).limit(limit)
    projects = []
    async for doc in cursor:
        projects.append(objid_to_str(doc))
    return projects
