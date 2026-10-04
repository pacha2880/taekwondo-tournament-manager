from fastapi.templating import Jinja2Templates

from app.version import __version__
from app.web.labels import es_label, match_status_badge_class

templates = Jinja2Templates(directory="app/templates")
templates.env.filters["es_label"] = es_label
templates.env.filters["match_status_badge_class"] = match_status_badge_class
templates.env.globals["app_version"] = __version__
