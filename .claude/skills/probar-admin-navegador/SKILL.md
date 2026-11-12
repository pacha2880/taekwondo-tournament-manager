---
name: probar-admin-navegador
description: Cómo manejar el navegador automatizado (mcp__Claude_Browser__*) contra el admin, local o en Render, sin perder envíos de formularios. Usar antes de probar pantallas del admin con el navegador.
---

# Probar el admin con el navegador

- Después de cada envío, esperar a que la página recargue y comprobarlo antes de escribir el siguiente
  campo. El plan gratis de Render puede tardar más de 2 s, y escribir sobre el formulario viejo cancela el
  envío.
- Las referencias (`ref_N`) se invalidan al recargar: volver a pedirlas.
- Si el formulario no entra en el viewport, usar `find` en vez de `read_page`.
