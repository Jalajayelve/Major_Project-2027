import os

import reflex as rx

config = rx.Config(
    app_name="meridian",
    api_url=os.environ.get("REFLEX_API_URL", "http://127.0.0.1:8000"),
    show_built_with_reflex=False,
    disable_plugins=[rx.plugins.SitemapPlugin],
)
