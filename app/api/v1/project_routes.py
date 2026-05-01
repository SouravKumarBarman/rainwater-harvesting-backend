from fastapi import APIRouter, HTTPException
from datetime import datetime
from bson import ObjectId
from fastapi import Depends

from app.db.dbConnect import get_project_collection
from app.models.project_model import HarvestResult, ProjectCreate
from app.models.userModel import userOut
from app.services.calculations import calculate_harvest
from app.services.pricing_service import estimate_project_cost
from ...services.user_services import get_current_user

router = APIRouter()


def objid_to_str(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.post("/calculate", response_model=dict)
async def calculate_and_create_project(
    payload: ProjectCreate,
    current_user: userOut = Depends(get_current_user),
    project_col=Depends(get_project_collection),
):
    # 1. Run calculations
    result: HarvestResult = calculate_harvest(payload.input)
    cost_estimate = await estimate_project_cost(payload.input, result)
    result.cost_estimate = cost_estimate
    result.products = cost_estimate.products
    result.estimated_cost = cost_estimate.total

    # 2. Save to MongoDB
    project_doc = {
        "user_id": current_user.id,
        "input": payload.input.model_dump(),
        "result": result.model_dump(),
        "created_at": datetime.utcnow(),
    }

    res = await project_col.insert_one(project_doc)
    project_doc["_id"] = res.inserted_id

    return {
        "project_id": str(res.inserted_id),
        "result": result,
    }


@router.get("/", summary="List current user's projects")
async def list_projects(
    limit: int = 20,
    skip: int = 0,
    current_user: userOut = Depends(get_current_user),
    project_col=Depends(get_project_collection),
):
    cursor = project_col.find({"user_id": current_user.id}).skip(skip).limit(limit)
    projects = []
    async for doc in cursor:
        projects.append(objid_to_str(doc))
    return projects


@router.get("/user/{user_id}", summary="List projects by user")
async def list_projects_by_user(
    user_id: str,
    limit: int = 20,
    skip: int = 0,
    current_user: userOut = Depends(get_current_user),
    project_col=Depends(get_project_collection),
):
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID.")
    if user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Cannot access another user's projects."
        )

    cursor = project_col.find({"user_id": user_id}).skip(skip).limit(limit)
    projects = []
    async for doc in cursor:
        projects.append(objid_to_str(doc))
    return projects


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    current_user: userOut = Depends(get_current_user),
    project_col=Depends(get_project_collection),
):
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=400, detail="Invalid project ID.")

    project = await project_col.find_one(
        {"_id": ObjectId(project_id), "user_id": current_user.id}
    )
    if not project:
        raise HTTPException(
            status_code=404, detail="Project not found or unauthorized."
        )

    project["_id"] = str(project["_id"])
    project["user_id"] = str(project["user_id"])
    return project
