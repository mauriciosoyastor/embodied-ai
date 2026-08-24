"""GzAdapter — SimAdapter via gazebosim/ros_gz bridge (headless mock).

Mapeo `research 039`: CmdVel -> Twist@gz.msgs.Twist ROS_TO_GZ,
Odometry@gz.msgs.Odometry GZ_TO_ROS, Clock. Sin requerir ROS/Gazebo
instalado: _FakeGzTransport mock pub/sub en-memoria para CI headless.
Para runtime real reemplazar _FakeGzTransport por gz.transport.Node
+ ros_gz_bridge YAML.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from plataforma.sim.models import CmdVel, SimMetrics, SimObservation


@dataclass(slots=True)
class _GzTwist:
    """Mock gz.msgs.Twist — linear.x=v_x, angular.z=omega_z."""

    linear_x: float = 0.0
    linear_y: float = 0.0
    linear_z: float = 0.0
    angular_x: float = 0.0
    angular_y: float = 0.0
    angular_z: float = 0.0


@dataclass(slots=True)
class _GzOdometry:
    """Mock gz.msgs.Odometry — pose+twist world-frame SI."""

    x: float
    y: float
    yaw: float
    v_x: float
    v_y: float
    omega_z: float
    ts: float
    frame_id: int


@dataclass(slots=True)
class _FakeGzTransport:
    """Mock gz-transport pub/sub sin instalación — solo memoria."""

    _subs: dict[str, list[Callable[[object], None]]] = field(default_factory=dict)
    published: list[tuple[str, object]] = field(default_factory=list)

    def advertise(self, topic: str) -> None:
        self._subs.setdefault(topic, [])

    def subscribe(self, topic: str, cb: Callable[[object], None]) -> None:
        self._subs.setdefault(topic, []).append(cb)

    def publish(self, topic: str, msg: object) -> None:
        self.published.append((topic, msg))
        for cb in self._subs.get(topic, []):
            cb(msg)


class GzAdapter:
    """SimAdapter vía gz.msgs — headless mock, protocolo agnóstico.

    Concepto 042: GzAdapter es peer directo de MujocoAdapter/FakeAdapter
    bajo adapter.SimAdapter Protocol, intercambiable sin cambios caller.
    Whiteboard last_identidades es proyección lectura, no afecta CmdVel.
    ABORTED overlay-only: GzAdapter no filtra, la FSM decide no actuar.
    """

    gz_cmd_vel_topic: str = "/model/turtlebot/cmd_vel"
    gz_odom_topic: str = "/model/turtlebot/odometry"

    def __init__(self, transport: _FakeGzTransport | None = None) -> None:
        self._gz: _FakeGzTransport = (
            transport if transport is not None else _FakeGzTransport()
        )
        self._gz.advertise(self.gz_cmd_vel_topic)
        self._gz.advertise(self.gz_odom_topic)
        self._x: float = 0.0
        self._y: float = 0.0
        self._yaw: float = 0.0
        self._v_x: float = 0.0
        self._omega_z: float = 0.0
        self._frame_id: int = 0
        self._steps: int = 0
        self._wall_ms: float = 0.0
        self._last_dt: float = 100.0
        self._gz.subscribe(self.gz_odom_topic, self._on_gz_odom)

    def _on_gz_odom(self, msg: object) -> None:
        if isinstance(msg, _GzOdometry):
            self._x = msg.x
            self._y = msg.y
            self._yaw = msg.yaw
            self._v_x = msg.v_x
            self._omega_z = msg.omega_z

    def send_cmd_vel(self, cmd: CmdVel) -> None:
        # clamp defensivo aunque Pydantic ya valida
        v = max(-1.0, min(1.0, cmd.v_x))
        w = max(-1.5, min(1.5, cmd.omega_z))
        self._v_x = v
        self._omega_z = w
        twist = _GzTwist(linear_x=v, angular_z=w)
        self._gz.publish(self.gz_cmd_vel_topic, twist)

    def get_observation(self) -> SimObservation:
        return SimObservation(
            x=self._x,
            y=self._y,
            yaw=self._yaw,
            v_x=self._v_x,
            v_y=0.0,
            omega_z=self._omega_z,
            ts=time.time() * 1000.0,
            frame_id=self._frame_id,
        )

    def get_metrics(self) -> SimMetrics:
        sps = 1000.0 / self._last_dt if self._last_dt > 0 else 0.0
        return SimMetrics(
            steps=self._steps,
            wall_time_ms=self._wall_ms,
            dt_ms=self._last_dt,
            steps_per_s=sps,
        )

    def step(self, dt_ms: float = 100.0) -> SimObservation:
        dt = dt_ms / 1000.0
        self._yaw = math.atan2(
            math.sin(self._yaw + self._omega_z * dt),
            math.cos(self._yaw + self._omega_z * dt),
        )
        self._x += self._v_x * math.cos(self._yaw) * dt
        self._y += self._v_x * math.sin(self._yaw) * dt
        self._frame_id += 1
        self._steps += 1
        self._wall_ms += dt_ms
        self._last_dt = dt_ms
        odom = _GzOdometry(
            x=self._x,
            y=self._y,
            yaw=self._yaw,
            v_x=self._v_x,
            v_y=0.0,
            omega_z=self._omega_z,
            ts=time.time() * 1000.0,
            frame_id=self._frame_id,
        )
        self._gz.publish(self.gz_odom_topic, odom)
        return self.get_observation()

    @staticmethod
    def bridge_yaml() -> str:
        return """- ros_topic_name: "/turtlebot/cmd_vel"
  gz_topic_name: "/model/turtlebot/cmd_vel"
  ros_type_name: "geometry_msgs/msg/Twist"
  gz_type_name: "gz.msgs.Twist"
  direction: ROS_TO_GZ
- ros_topic_name: "/turtlebot/odometry"
  gz_topic_name: "/model/turtlebot/odometry"
  ros_type_name: "nav_msgs/msg/Odometry"
  gz_type_name: "gz.msgs.Odometry"
  direction: GZ_TO_ROS"""
