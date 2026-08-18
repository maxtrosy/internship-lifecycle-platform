from fastapi import FastAPI

from src.contexts.agreements.api.router import router as agreements_router
from src.contexts.applications_eligibility.api.router import router as applications_router
from src.contexts.notifications.api.router import router as notifications_router
from src.contexts.opportunities.api.router import router as opportunities_router
from src.contexts.placements.api.router import router as placements_router
from src.contexts.reporting.api.router import router as reporting_router
from src.contexts.supervision_evaluation.api.router import router as supervision_router

app = FastAPI(title="Internship & Practicum Management System")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(opportunities_router, prefix="/opportunities", tags=["opportunities"])
app.include_router(applications_router, prefix="/applications", tags=["applications"])
app.include_router(agreements_router, prefix="/agreements", tags=["agreements"])
app.include_router(placements_router, prefix="/placements", tags=["placements"])
app.include_router(supervision_router, prefix="/supervision", tags=["supervision"])
app.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
app.include_router(reporting_router, prefix="/reporting", tags=["reporting"])
