"""FastAPI composition root with no domain logic."""

from fastapi import FastAPI

from apps.api.commands import router as command_router
from apps.api.corrections import router as correction_router
from apps.api.identities import router as identity_router
from apps.api.media import router as media_router
from apps.api.reviews import router as review_router
from apps.api.timelines import router as timeline_router
from apps.services.timeline_editing import TimelineEditingService
from packages.foundation.settings import get_settings
from packages.persistence.command_repository import CommandRepository
from packages.persistence.correction_repository import CorrectionRepository
from packages.persistence.database import create_database_engine
from packages.persistence.identity_repository import IdentityRepository
from packages.persistence.project_repository import ProjectRepository
from packages.persistence.review_repository import ReviewRepository
from packages.persistence.timeline_repository import TimelineRepository


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="NarratoPro API", version="0.1.0")
    app.state.database_engine = create_database_engine(settings.database_url)
    app.state.command_repository = CommandRepository()
    app.state.correction_repository = CorrectionRepository()
    app.state.identity_repository = IdentityRepository()
    app.state.project_repository = ProjectRepository()
    app.state.review_repository = ReviewRepository()
    app.state.timeline_repository = TimelineRepository()
    app.state.timeline_editing_service = TimelineEditingService(
        engine=app.state.database_engine,
        repository=app.state.timeline_repository,
    )
    app.include_router(command_router)
    app.include_router(correction_router)
    app.include_router(identity_router)
    app.include_router(media_router)
    app.include_router(review_router)
    app.include_router(timeline_router)

    @app.get("/health/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    async def ready() -> dict[str, str]:
        return {"status": "ready", "environment": settings.environment}

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("apps.api.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    run()
