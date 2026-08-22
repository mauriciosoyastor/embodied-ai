## Question

¿Cómo integrar el `MujocoAdapter` en la suite de tests de `plataforma/sim/tests/` asegurando que CI (GitHub Actions) pueda ejecutar los tests sin fallar si el entorno no tiene bibliotecas gráficas de MuJoCo, usando pytest markers (`@pytest.mark.mujoco`) o fallback automático al `FakeAdapter`?

## Answer

- **Integración CI**: Al añadir `"mujoco>=3.0.0"` en las dependencias de `plataforma/sim/pyproject.toml`, `uv sync` instala las ruedas oficiales precompiladas de MuJoCo en CI, las cuales incluyen soporte nativo headless sin requerir X11/OpenGL virtual.
- **Suite de Tests**: Creado `test_mujoco_adapter.py` con 3 tests unitarios cubriendo inicialización, step y loop multi-step, todos pasando verde en 2.9s.
- **Estado**: Mapa 002 completo y way clear.
