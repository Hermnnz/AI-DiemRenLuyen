from fastapi import APIRouter

router = APIRouter(prefix="/bcs", tags=["BCS"])


@router.get("/campaigns/{campaign_id}/overview")
def get_campaign_overview(campaign_id: str):
    return {"message": "BCS overview endpoint shell"}
