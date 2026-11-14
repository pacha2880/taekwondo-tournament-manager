from fastapi.templating import Jinja2Templates

from app.models import Grade
from app.version import __version__
from app.web.labels import es_label, match_status_badge_class, tournament_status_badge_class

templates = Jinja2Templates(directory="app/templates")
templates.env.filters["es_label"] = es_label
templates.env.filters["match_status_badge_class"] = match_status_badge_class
templates.env.filters["tournament_status_badge_class"] = tournament_status_badge_class
templates.env.globals["app_version"] = __version__
# (valor, texto) de cada grado, para los <select>: las plantillas no pueden usar `.value`.
templates.env.globals["grade_options"] = [(grade.value, es_label(grade)) for grade in Grade]
