import os

import reflex as rx

config = rx.Config(
    app_name="study_path",
    frontend_port=int(os.getenv("STUDYPATH_FRONTEND_PORT", "3001")),
    backend_port=int(os.getenv("STUDYPATH_BACKEND_PORT", "8001")),
)
