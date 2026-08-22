## Question

¿Cómo implementar `plataforma/sim/mujoco_adapter.py` implementando el `Protocol` de `adapter.py`, inicializando `mujoco.MjModel` y `mujoco.MjData`, corriendo el bucle de simulación a 10Hz mediante `mujoco.mj_step`, y traduciendo la observación del estado físico a `SimObservation`?

## Answer

- **Implementación**: Creado `plataforma/sim/mujoco_adapter.py` con modelo MJCF inline (cilindro libre + 2 ruedas con actuadores de velocidad).
- **Protocolo**: Cumple totalmente con `SimAdapter` (`get_observation`, `send_cmd_vel`, `get_metrics`, `step`).
- **Traducción**: Extracción de posición `(x, y)` y yaw a partir de quaternion del freejoint root, y velocidades espaciales, pasando los tests de `plataforma/sim`.
