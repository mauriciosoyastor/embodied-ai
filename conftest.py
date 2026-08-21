# conftest raíz — ancla pytest (rootdir) e inyecta la raíz a sys.path
# Necesario para `from plataforma...` en local/CI (ver ADR-0002).
# No borrar: sin esto falla ModuleNotFoundError: No module named 'plataforma'.
