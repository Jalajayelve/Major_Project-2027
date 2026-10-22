"""FastAPI entry point; model availability is separate from service health."""
from fastapi import FastAPI
from .routes import health_routes, profile_routes, matching_routes


def create_app():
    app = FastAPI(title="Meridian analysis API")
    for module in (health_routes, profile_routes, matching_routes):
        app.include_router(module.router)
    return app


app = create_app()
