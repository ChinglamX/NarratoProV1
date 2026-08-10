"""FastAPI composition root with no domain logic."""

from fastapi import FastAPI

from packages.foundation.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="NarratoPro API", version="0.1.0")

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
