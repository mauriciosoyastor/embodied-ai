# Ticket 044 — Task: Spike GzAdapter minimal headless

> Parent: `007-map-arquitectura-productiva` · Label: `wayfinder:task` · Estado: **cerrado 2026-08-24** · Tipo: HITL/AFK · Bloqueado por 039 (liberado) — spike aterrizado headless

## Question

Trabajo que **desbloquea** decisión Bridge (único ticket que _hace_ vs decide en esta rama):

Spike `GzAdapter(SimAdapter)` minimal que traduce `SimAdapter` `adapter.py:8` sin requerir ROS/Gazebo instalado.

## Resolution

> Estado: **cerrado 2026-08-24** · Task HITL/AFK ejecutada · Change aterrizado · Verificación verde

**Qué se hizo (spike agnóstico, no toca MujocoAdapter):**

- **`plataforma/sim/gazebo_adapter.py`** (nuevo, 140 líneas) — `GzAdapter(SimAdapter)` headless mock:
  - `_GzTwist` `{linear_x, angular_z}` mock `gz.msgs.Twist`
  - `_GzOdometry` `{x,y,yaw,v_x,v_y,omega_z,ts,frame_id}` mock `gz.msgs.Odometry`
  - `_FakeGzTransport` `{advertise/subscribe/publish}` mock `gz-transport` en-memoria, `published: list[(topic,msg)]`, inyectable `transport` para `pytest` sin `gz`
  - `GzAdapter` `gz_cmd_vel_topic /model/turtlebot/cmd_vel` `gz_odom_topic /model/turtlebot/odometry` + `send_cmd_vel(CmdVel) clamp [-1,1]/[-1.5,1.5] → _GzTwist` `publish`, `get_observation→SimObservation`, `step(dt_ms=100) yaw atan2(sin/cos) + x+=v*cos(yaw)*dt` + `publish _GzOdometry`, `get_metrics`, `bridge_yaml()` ros_gz YAML `ROS_TO_GZ/GZ_TO_ROS`
  - Agnóstico: intercambiable `FakeGzTransport ↔ MuJoCoAdapter ↔ Gazebo Transport C++ API` sin cambios caller (042 Single-Writer + simulación agnóstica)

- **`plataforma/sim/tests/test_gz_adapter.py`** (nuevo, 5 tests) — `test_gz_adapter_obs_advances_on_step`, `test_gz_adapter_cmd_vel_publishes_twist`, `test_gz_adapter_step_publishes_odometry`, `test_gz_adapter_yaw_integration`, `test_gz_adapter_bridge_yaml_contains_ros_gz` — sintéticos headless sin `mujoco`/`ros_gz`

**Verificación (2026-08-24):**

```
uv run ruff format .            → 1 reformatted, 148 unchanged
uv run ruff check --fix .       → 1 fixed, 0 remaining
uv run mypy plataforma/sim      → Success: no issues in 15 source files
uv run pytest plataforma/sim -q → 14 passed in 6.47s
```

Previo `plataforma/sim` 9 tests → ahora 14 (+5). Headless sin cámara/Gazebo/ROS, CI verde. `MujocoAdapter` intacto, `FakeAdapter` fixture compartido.

**Mapa 007 way completo** — frontera vacía, destino alcanzado.

## Blocking

- Bloquea a —. Bloqueado por 039 — **liberado y cerrado**.
