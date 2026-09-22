import reflex as rx

config = rx.Config(
    app_name="meridian",
    show_built_with_reflex=False,
    disable_plugins=[rx.plugins.SitemapPlugin],
)
