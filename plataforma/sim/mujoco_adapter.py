"""MujocoAdapter — simulación física real con MuJoCo Python bindings."""

import math
import time
from typing import Any

import mujoco

from plataforma.sim.models import CmdVel, SimMetrics, SimObservation

TURTLEBOT_MJCF = """
<mujoco model="turtlebot_diff">
  <compiler angle="radian" autolimits="true"/>
  <option timestep="0.01" gravity="0 0 -9.81"/>
  <worldbody>
    <light pos="0 0 3" dir="0 0 -1"/>
    <geom name="floor" type="plane" size="10 10 0.1"/>
    <body name="base" pos="0 0 0.05">
      <freejoint name="root"/>
      <geom name="body_geom" type="cylinder" size="0.15 0.05" mass="2.0"/>
      <body name="wheel_left" pos="0 0.11 -0.02">
        <joint name="joint_left" type="hinge" axis="0 1 0"/>
        <geom name="geom_left" type="cylinder" size="0.033 0.01"
              mass="0.1" euler="1.5708 0 0"/>
      </body>
      <body name="wheel_right" pos="0 -0.11 -0.02">
        <joint name="joint_right" type="hinge" axis="0 1 0"/>
        <geom name="geom_right" type="cylinder" size="0.033 0.01"
              mass="0.1" euler="1.5708 0 0"/>
      </body>
    </body>
  </worldbody>
  <actuator>
    <velocity name="act_left" joint="joint_left" kv="20"/>
    <velocity name="act_right" joint="joint_right" kv="20"/>
  </actuator>
</mujoco>
"""


class MujocoAdapter:
    """Adapter físico basado en MuJoCo model/data."""

    def __init__(self) -> None:
        self.model: Any = mujoco.MjModel.from_xml_string(TURTLEBOT_MJCF)
        self.data: Any = mujoco.MjData(self.model)
        self._v_x: float = 0.0
        self._omega_z: float = 0.0
        self._frame_id: int = 0
        self._steps: int = 0
        self._wall_ms: float = 0.0
        self._last_dt: float = 100.0

        # Geometría diferencial
        self.wheel_track: float = 0.22  # 0.11 - (-0.11)
        self.wheel_radius: float = 0.033

    def send_cmd_vel(self, cmd: CmdVel) -> None:
        self._v_x = max(-1.0, min(1.0, cmd.v_x))
        self._omega_z = max(-1.5, min(1.5, cmd.omega_z))

        # Cinemática inversa diferencial: (v_x, omega) -> (omega_l, omega_r)
        v = self._v_x
        omega = self._omega_z
        L = self.wheel_track
        R = self.wheel_radius

        omega_l = (v - (omega * L / 2.0)) / R
        omega_r = (v + (omega * L / 2.0)) / R

        # Aplicar a actuadores de velocidad en MuJoCo (control ctrl)
        if len(self.data.ctrl) >= 2:
            self.data.ctrl[0] = omega_l
            self.data.ctrl[1] = omega_r

    def get_observation(self) -> SimObservation:
        # qpos: [x, y, z, qw, qx, qy, qz] para freejoint root
        x = float(self.data.qpos[0])
        y = float(self.data.qpos[1])
        # Extraer yaw de quaternion (qw, qx, qy, qz)
        qw, qx, qy, qz = (
            float(self.data.qpos[3]),
            float(self.data.qpos[4]),
            float(self.data.qpos[5]),
            float(self.data.qpos[6]),
        )
        yaw = math.atan2(2.0 * (qw * qz + qx * qy), 1.0 - 2.0 * (qy * qy + qz * qz))

        # qvel: [vx, vy, vz, wx, wy, wz] (velocidad espacial del cuerpo base)
        v_x = float(self.data.qvel[0])
        v_y = float(self.data.qvel[1])
        omega_z = float(self.data.qvel[5])

        return SimObservation(
            x=x,
            y=y,
            yaw=yaw,
            v_x=v_x,
            v_y=v_y,
            omega_z=omega_z,
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
        dt_s = dt_ms / 1000.0
        sim_dt = float(self.model.opt.timestep)  # ej. 0.01s
        substeps = max(1, int(round(dt_s / sim_dt)))

        for _ in range(substeps):
            mujoco.mj_step(self.model, self.data)

        self._frame_id += 1
        self._steps += 1
        self._wall_ms += dt_ms
        self._last_dt = dt_ms
        return self.get_observation()
