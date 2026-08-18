from fastapi import APIRouter

router = APIRouter()


@router.get("/institutional")
def institutional_reports() -> None:
    raise NotImplementedError
