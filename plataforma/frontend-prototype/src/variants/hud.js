import * as THREE from 'three';
import { createRenderer } from '../renderer.js';
import { createRobot, applyPose } from '../robot.js';

export const hud = {
  name: 'HUD táctico',
  mount(container, state) {
    container.classList.add('v-hud');
    const r = createRenderer(container);
    const robot = createRobot();
    r.scene.add(robot.group);

    const panel = document.createElement('div');
    panel.className = 'hud-panel';
    container.appendChild(panel);

    const ctl = document.createElement('div');
    ctl.className = 'hud-controls';
    const followBtn = document.createElement('button');
    followBtn.textContent = 'Seguir: OFF';
    const resetBtn = document.createElement('button');
    resetBtn.textContent = 'Reset';
    ctl.append(followBtn, resetBtn);
    container.appendChild(ctl);

    let follow = false;
    followBtn.addEventListener('click', () => {
      follow = !follow;
      followBtn.textContent = follow ? 'Seguir: ON' : 'Seguir: OFF';
    });
    resetBtn.addEventListener('click', () => state.reset());

    const target = new THREE.Vector3();
    r.setUpdate((dt) => {
      state.step();
      applyPose(robot, state, dt);
      if (follow) {
        target.set(state.x, 0, state.y);
        r.controls.target.lerp(target, 0.2);
      }
      panel.innerHTML = `
        <div class="hud-title">TELEMETRÍA</div>
        <div class="hud-row"><span>steps/s</span><b>${state.stepsPerSecond.toLocaleString()}</b></div>
        <div class="hud-row"><span>frame time</span><b>${state.frameTimeMs.toFixed(1)} ms</b></div>
        <div class="hud-row"><span>agentes</span><b>${state.agents}</b></div>
        <div class="hud-row"><span>pose x/y/θ</span><b>${state.x.toFixed(2)} / ${state.y.toFixed(2)} / ${(state.theta * 180 / Math.PI).toFixed(0)}°</b></div>
        <div class="hud-row"><span>cmd_vel</span><b>${state.vx.toFixed(2)} m/s / ${state.omega.toFixed(2)} rad/s</b></div>`;
    });

    return {
      dispose() {
        r.dispose();
        panel.remove();
        ctl.remove();
        container.classList.remove('v-hud');
      },
    };
  },
};
