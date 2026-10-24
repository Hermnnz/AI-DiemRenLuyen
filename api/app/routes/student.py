from fastapi import APIRouter

router = APIRouter(prefix="/student", tags=["Student"])


@router.get("/current")
def get_student_current():
    return {"message": "Student current endpoint shell"}
