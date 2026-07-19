# Bloque 4 — hallazgo Semgrep

- HEAD inspeccionado: `1704a9346d2cef5965f7aba7b08259828b3607ce`.
- El job de formato quedó aprobado; el fallo agregado de Linters correspondía exclusivamente al job Semgrep.
- La regla `frappe-setuser` detectó llamadas directas a `frappe.set_user` dentro de `runtime_smoke.py`.
- La corrección encapsula el cambio de identidad en un contexto exclusivo de prueba que siempre restaura el usuario anterior mediante `finally`.
- No se desactiva la regla ni se añade una supresión `nosemgrep`.
