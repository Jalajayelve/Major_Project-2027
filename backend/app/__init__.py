from fastapi import FastAPI


def create_app() -> FastAPI:
    """Application factory for the FastAPI backend."""
    app = FastAPI(title="Study Abroad AI API", version="1.0.0")

    from app.routes.health_routes import router as health_router
    from app.routes.profile_routes import router as profile_router
    from app.routes.matching_routes import router as matching_router

    app.include_router(health_router)
    app.include_router(profile_router)
    app.include_router(matching_router)

    return app


app = create_app()
