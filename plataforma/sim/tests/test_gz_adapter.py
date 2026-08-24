"""Tests headless GzAdapter — sin ROS/Gazebo instalado."""

import pytest

from plataforma.sim.gazebo_adapter import (
    GzAdapter,
    _FakeGzTransport,
    _GzOdometry,
    _GzTwist,
)
from plataforma.sim.models import CmdVel


def test_gz_adapter_obs_advances_on_step() -> None:
    gz = _FakeGzTransport()
    adapter = GzAdapter(transport=gz)
    obs0 = adapter.get_observation()
    assert obs0.frame_id == 0
    adapter.send_cmd_vel(CmdVel(v_x=0.5, omega_z=0.0))
    obs1 = adapter.step(dt_ms=100.0)
    assert obs1.frame_id == 1
    assert obs1.x > obs0.x
    assert obs1.v_x == pytest.approx(0.5)
    metrics = adapter.get_metrics()
    assert metrics.steps == 1
    assert metrics.steps_per_s == pytest.approx(10.0)


def test_gz_adapter_cmd_vel_publishes_twist() -> None:
    gz = _FakeGzTransport()
    adapter = GzAdapter(transport=gz)
    adapter.send_cmd_vel(CmdVel(v_x=0.5, omega_z=0.1))
    assert len(gz.published) == 1
    topic, msg = gz.published[0]
    assert topic == "/model/turtlebot/cmd_vel"
    assert isinstance(msg, _GzTwist)
    assert msg.linear_x == pytest.approx(0.5)
    assert msg.angular_z == pytest.approx(0.1)


def test_gz_adapter_step_publishes_odometry() -> None:
    gz = _FakeGzTransport()
    adapter = GzAdapter(transport=gz)
    adapter.send_cmd_vel(CmdVel(v_x=0.3, omega_z=0.0))
    gz.published.clear()
    adapter.step(dt_ms=100.0)
    # step publica odometry GZ→ROS
    assert len(gz.published) == 1
    topic, msg = gz.published[0]
    assert topic == "/model/turtlebot/odometry"
    assert isinstance(msg, _GzOdometry)
    assert msg.frame_id == 1
    obs = adapter.get_observation()
    assert obs.frame_id == 1


def test_gz_adapter_yaw_integration() -> None:
    gz = _FakeGzTransport()
    adapter = GzAdapter(transport=gz)
    adapter.send_cmd_vel(CmdVel(v_x=0.0, omega_z=1.0))
    obs = adapter.step(dt_ms=1000.0)
    # yaw debe haber girado ~1 rad en 1s
    assert obs.yaw == pytest.approx(1.0, abs=0.01)
    assert obs.omega_z == pytest.approx(1.0)


def test_gz_adapter_bridge_yaml_contains_ros_gz() -> None:
    yaml = GzAdapter.bridge_yaml()
    assert "geometry_msgs/msg/Twist" in yaml
    assert "gz.msgs.Twist" in yaml
    assert "ROS_TO_GZ" in yaml
    assert "GZ_TO_ROS" in yaml
