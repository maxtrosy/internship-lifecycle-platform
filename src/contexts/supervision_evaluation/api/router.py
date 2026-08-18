from fastapi import APIRouter

router = APIRouter()


@router.post("/progress-reports")
def submit_progress_report() -> None:
    raise NotImplementedError
