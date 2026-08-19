import * as THREE from 'three';
import { createRenderer } from '../renderer.js';
import { createRobot, applyPose } from '../robot.js';
import { missionStatus, missionProgress } from '../mission.js';

export const cinematic = {
  name: 'Cinemático minimalista',
  mount(container, sim) {
    const state = sim.state;
    container.classList.add('v-cine');
    const r = createRenderer(container);
    r.controls.enabled = false;

    const robot = createRobot();
    r.scene.add(robot.group);

    const readout = document.createElement('div');
    readout.className = 'cine-readout';
    container.appendChild(readout);

    const camPos = new THREE.Vector3(5, 4, 7);
    const look = new THREE.Vector3();
    const behind = new THREE.Vector3();
    const ahead = new THREE.Vector3();

    sim.startMission();

    r.setUpdate((dt) => {
      sim.step();
      applyPose(robot, state, dt);

      behind.set(
        state.x - Math.cos(state.theta) * 4,
        3.2,
        state.y - Math.sin(state.theta) * 4
      );
      camPos.lerp(behind, 0.05);
      ahead.set(state.x, 0, state.y);
      look.lerp(ahead, 0.12);

      r.camera.position.copy(camPos);
      r.camera.lookAt(look);

      const st = missionStatus(state);
      readout.innerHTML = `
        <div class="cine-big">${state.vx.toFixed(2)} m/s · ${state.omega.toFixed(2)} rad/s</div>
        <div class="cine-small">${st.label} · waypoint ${missionProgress(state, sim.totalWaypoints)} · x ${state.x.toFixed(2)} · y ${state.y.toFixed(2)} · θ ${(state.theta * 180 / Math.PI).toFixed(0)}° · steps/s ${state.stepsPerSecond.toLocaleString()}</div>`;
    });

    return {
      dispose() {
        r.dispose();
        readout.remove();
        container.classList.remove('v-cine');
      },
    };
  },
};
