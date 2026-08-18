from fastapi import APIRouter

router = APIRouter()


@router.post("/deadlines")
def create_deadline() -> None:
    raise NotImplementedError
