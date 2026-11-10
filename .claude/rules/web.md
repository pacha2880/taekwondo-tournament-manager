---
paths:
  - "app/web/**"
  - "app/templates/**"
---
# Pantallas (admin y públicas)

- Los handlers del admin llaman directo a las funciones de `app/api/*.py` (ej. `create_club_api =
  create_club`, pasando `db` explícito) en vez de reimplementar validaciones. Atrapan
  `HTTPException`/`ValidationError` y re-renderizan la página con el error en español, nunca JSON crudo.
- Todo `<form method="post">` del admin lleva `data-confirm` (`tests/test_admin_confirmations.py`).
- Si un formulario falla, se vuelve a mostrar con lo escrito: `echo_form(...)` en el handler y
  `form.<campo>` en la plantilla.
- Enums en plantillas: `|es_label` (de `app/web/labels.py`), nunca `.value`
  (`tests/test_templates_language.py` falla). Para comparar, `m.status == "pending"`: `{{ status }}`
  imprime `TournamentStatus.DRAFT`, no `draft`.
- Un solo entorno Jinja: `app/web/templating.py`.
