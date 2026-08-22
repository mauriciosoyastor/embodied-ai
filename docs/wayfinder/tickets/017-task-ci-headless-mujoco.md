## Question

¿Cómo integrar el `MujocoAdapter` en la suite de tests de `plataforma/sim/tests/` asegurando que CI (GitHub Actions) pueda ejecutar los tests sin fallar si el entorno no tiene bibliotecas gráficas de MuJoCo, usando pytest markers (`@pytest.mark.mujoco`) o fallback automático al `FakeAdapter`?
