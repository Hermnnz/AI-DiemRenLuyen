from fastapi import APIRouter

router = APIRouter(prefix="/gvcn", tags=["GVCN"])


@router.get("/campaigns/{campaign_id}/final-scores.csv")
def get_final_scores_csv(campaign_id: str):
    return {"message": "GVCN export csv endpoint shell"}
