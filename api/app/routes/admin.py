from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/campaigns")
def create_campaign():
    return {"message": "Admin create campaign endpoint shell"}
