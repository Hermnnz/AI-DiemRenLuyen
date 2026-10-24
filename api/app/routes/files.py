from fastapi import APIRouter

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("/{file_id}")
def get_file(file_id: str):
    return {"message": "Files secure download endpoint shell"}
