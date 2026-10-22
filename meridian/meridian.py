"""MERIDIAN: a study-abroad dossier, in pure Python Reflex."""
import reflex as rx

from . import theme
from .pages.analysis import analysis_page
from .pages.documents import documents_page
from .pages.landing import landing_page
from .pages.profile import profile_page
from .pages.report import report_page
from .pages.results import results_page
from .state import State
from .pages.account import login_page, register_page, dashboard_page, protected

app = rx.App(
    stylesheets=[theme.GOOGLE_FONTS, "/enhancements.css"],
    head_components=[
        rx.el.link(rel="icon", href="/favicon.svg", type="image/svg+xml"),
        rx.el.style(theme.GLOBAL_CSS),
        rx.el.script(theme.EARLY_JS),
        rx.el.script(src="/land_mask.js", defer=True),
        rx.el.script(src="/scene.js", defer=True),
    ],
    style={"font_family": theme.FONT_SANS},
)

TITLE = "MERIDIAN — You bring the ambition. We map the journey."
app.add_page(landing_page, route="/", title=TITLE)
app.add_page(login_page, route="/login", title="Sign in · MERIDIAN")
app.add_page(register_page, route="/register", title="Create your dossier · MERIDIAN")
app.add_page(dashboard_page, route="/dashboard", title="Dashboard · MERIDIAN", on_load=State.require_auth)
app.add_page(lambda: protected(profile_page()), route="/profile", title="Student profile · MERIDIAN", on_load=State.require_auth)
app.add_page(lambda: protected(documents_page()), route="/documents", title="Documents · MERIDIAN", on_load=State.require_auth)
app.add_page(lambda: protected(analysis_page()), route="/analysis", title="Analysis · MERIDIAN", on_load=State.require_auth)
app.add_page(lambda: protected(results_page()), route="/results", title="Your dossier · MERIDIAN", on_load=State.require_auth)
app.add_page(lambda: protected(results_page()), route="/report", title="Report · MERIDIAN", on_load=State.require_auth)
