## Question

¿Cómo instalar y configurar `mujoco` Python package en el entorno uv del monorepo (`pyproject.toml`), y gestionar el step loop headless (sin requerir contexto OpenGL/display gráfico) para tests automáticos y ejecución local?

## Answer

- **Instalación**: Añadido `"mujoco>=3.0.0"` en `plataforma/sim/pyproject.toml` y configurado override `mujoco.*` en mypy.
- **Loop headless**: `mujoco.mj_step(model, data)` corre de forma totalmente headless en CPU/memoria (calculando cinemática y dinámica directa) sin requerir pantalla, X11 ni display OpenGL offscreen cuando solo se actualizan estado y física.
