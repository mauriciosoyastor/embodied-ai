# Ticket 039 — Research: gazebosim/ros_gz bridge mapping

> Parent: `007-map-arquitectura-productiva` · Label: `wayfinder:research` · Estado: **cerrado 2026-08-24** · Tipo: AFK · Rama: `research/039-rosgz-bridge` (no prod code modificado)

## Question

¿Qué `message types` y sintaxis `/TOPIC@ROS_MSG@GZ_MSG` de `gazebosim/ros_gz` `ros_gz_bridge parameter_bridge` mapean `CmdVel(v_x,omega_z)` y `SimObservation(x,y,yaw,v_x,v_y,omega_z, timestamp, frame_id)` de `plataforma/sim/adapter.py:8 SimAdapter` para un `GzAdapter(SimAdapter)` headless sin requerir ROS/Gazebo instalado, y qué `ros_gz_sim_demos` + `gz-mujoco` SDFormat↔MJCF sirve como fixture?

## Sources

**Local (verificados 2026-08-24):**
- `plataforma/sim/adapter.py:8 SimAdapter Protocol` + `models.py:6 SimObservation` + `models.py:22 CmdVel(v_x [-1,1], omega_z [-1.5,1.5])`
- `plataforma/sim/mujoco_adapter.py:55 wheel_track 0.22 wheel_radius 0.033` + `fake_adapter.py:23 FakeAdapter headless`

**Externo:**
- `gazebosim/ros_gz` branch `ros2`/`humble` `ros_gz_bridge/README.md` + `gazebosim.org/docs/latest/ros2_integration`
- `gz-mujoco` `sdformat_mjcf` converter

## Resolution

> Estado: **cerrado 2026-08-24** · Research AFK · Mapeo completo + snippet GzAdapter mock sin ROS

### 1. Mapeo SimAdapter → ros_gz

| Dirección | ROS | GZ | Notas |
|---|---|---|---|
| `send_cmd_vel(CmdVel)` → GZ | `geometry_msgs/msg/Twist` | `gz.msgs.Twist` | `linear.x=v_x, angular.z=omega_z` — tabla oficial `ros_gz_bridge/README.md:72` |
| `get_observation()->SimObservation` ← GZ | `nav_msgs/msg/Odometry` | `gz.msgs.Odometry` | pose `x,y,yaw→quat`, twist `v_x,v_y,omega_z`, `stamp=ts, frame_id` |
| Clock | `rosgraph_msgs/msg/Clock` | `gz.msgs.Clock` | `GZ_TO_ROS` `lazy=false` |

Branch: `humble` histórico `ignition.msgs.*`, `ros2`/`jazzy` usan `gz.msgs.*` — usar `gz.msgs.*`.

### 2. Sintaxis parameter_bridge

```
ros2 run ros_gz_bridge parameter_bridge /TOPIC@ROS_MSG@GZ_MSG   # @ = BIDIRECTIONAL
ros2 run ros_gz_bridge parameter_bridge /TOPIC@ROS_MSG[GZ_MSG  # [ = GZ→ROS
ros2 run ros_gz_bridge parameter_bridge /TOPIC@ROS_MSG]GZ_MSG  # ] = ROS→GZ
```

CLI spike:
```bash
ros2 run ros_gz_bridge parameter_bridge /model/turtlebot/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist
ros2 run ros_gz_bridge parameter_bridge /model/turtlebot/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry
gz topic -t /model/turtlebot/cmd_vel -m gz.msgs.Twist -p 'linear:{x:0.5} angular:{z:0.2}'
```

### 3. YAML config recomendado para 044

```yaml
- ros_topic_name: "/turtlebot/cmd_vel"
  gz_topic_name: "/model/turtlebot/cmd_vel"
  ros_type_name: "geometry_msgs/msg/Twist"
  gz_type_name: "gz.msgs.Twist"
  direction: ROS_TO_GZ
- ros_topic_name: "/turtlebot/odometry"
  gz_topic_name: "/model/turtlebot/odometry"
  ros_type_name: "nav_msgs/msg/Odometry"
  gz_type_name: "gz.msgs.Odometry"
  direction: GZ_TO_ROS
```

Template oficial `ros_gz_example_bringup: diff_drive` idéntico.

### 4. Fixture demos

- `ros_gz_sim_demos diff_drive.launch.py` + `diff_drive.sdf` con `gz-sim-diff-drive-system` — canon para 044 ( `ros2 topic pub /model/vehicle_blue/cmd_vel geometry_msgs/Twist "{linear:{x:5.0} angular:{z:0.5}}"` )
- `gz-mujoco` `sdf2mjcf` / `mjcf2sdf --export_world_plugins` — `mjcf2sdf turtlebot.xml turtlebot.sdf` para reutilizar `TURTLEBOT_MJCF`

### 5. Snippet GzAdapter headless (sin ROS/Gazebo, para 044)

`GzAdapter(SimAdapter)` con `_FakeGzTransport` mock pub/sub en-memoria: `send_cmd_vel` clamp `[-1,1]/[-1.5,1.5]` → `publish /model/turtlebot/cmd_vel _GzTwist`; `step(dt_ms=100)` integra `x+=v*cos(yaw)*dt`, `yaw=atan2(sin(yaw+w*dt),cos(...))`, publica `_GzOdometry`; `get_observation/get_metrics` headless. Inyectable `transport` permite `pytest` sin `gz-transport`. Para runtime real reemplazar mock por `gz.transport.Node` + YAML bridge, manteniendo conversión `linear.x/angular.z`.

> Próximo: Ticket 044 toma este mapeo para `plataforma/sim/gazebo_adapter.py` + `tests/test_gz_adapter.py` headless + `adr/0007-gzadapter-bridge.md`. Desbloquea 042 y 044.

## Blocking

- Bloquea a 042,044. Cerrado — desbloquea a 044 inmediatamente, 042 espera también 038.
