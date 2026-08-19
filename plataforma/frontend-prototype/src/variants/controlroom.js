import { createRenderer } from '../renderer.js';
import { createRobot, applyPose } from '../robot.js';

export const controlroom = {
  name: 'Control room',
  mount(container, state) {
    container.classList.add('v-room');
    const wrap = document.createElement('div');
    wrap.className = 'room-layout';
    const viewport = document.createElement('div');
    viewport.className = 'room-viewport';
    const dash = document.createElement('div');
    dash.className = 'room-dash';
    wrap.append(viewport, dash);
    container.appendChild(wrap);

    const r = createRenderer(viewport);
    const robot = createRobot();
    r.scene.add(robot.group);

    dash.innerHTML = `
      <div class="room-head">PANEL DE MISIÓN</div>
      <div class="room-cards">
        <div class="room-card"><span>steps/s</span><b id="m-sps">–</b></div>
        <div class="room-card"><span>frame time</span><b id="m-ft">–</b></div>
        <div class="room-card"><span>agentes</span><b id="m-ag">–</b></div>
        <div class="room-card"><span>VRAM</span><b id="m-vram">–</b></div>
      </div>
      <div class="room-table">
        <div><span>x</span><b id="m-x">–</b></div>
        <div><span>y</span><b id="m-y">–</b></div>
        <div><span>θ</span><b id="m-th">–</b></div>
        <div><span>v_x</span><b id="m-vx">–</b></div>
        <div><span>ω_z</span><b id="m-om">–</b></div>
      </div>
      <div class="room-spark">
        <span>steps/s · últimos 30 s</span>
        <canvas id="m-spark" width="240" height="60"></canvas>
      </div>
      <button id="m-reset">Resetear escenario</button>`;

    const sparkCtx = dash.querySelector('#m-spark').getContext('2d');
    const sparkData = [];
    dash.querySelector('#m-reset').addEventListener('click', () => state.reset());

    r.setUpdate((dt) => {
      state.step();
      applyPose(robot, state, dt);
      dash.querySelector('#m-sps').textContent = state.stepsPerSecond.toLocaleString();
      dash.querySelector('#m-ft').textContent = `${state.frameTimeMs.toFixed(1)} ms`;
      dash.querySelector('#m-ag').textContent = state.agents;
      dash.querySelector('#m-vram').textContent = 'n/d (visor web)';
      dash.querySelector('#m-x').textContent = state.x.toFixed(2);
      dash.querySelector('#m-y').textContent = state.y.toFixed(2);
      dash.querySelector('#m-th').textContent = `${(state.theta * 180 / Math.PI).toFixed(0)}°`;
      dash.querySelector('#m-vx').textContent = `${state.vx.toFixed(2)} m/s`;
      dash.querySelector('#m-om').textContent = `${state.omega.toFixed(2)} rad/s`;
      sparkData.push(state.stepsPerSecond);
      if (sparkData.length > 60) sparkData.shift();
      drawSpark(sparkCtx, sparkData);
    });

    return {
      dispose() {
        r.dispose();
        wrap.remove();
        container.classList.remove('v-room');
      },
    };
  },
};

function drawSpark(ctx, data) {
  const w = ctx.canvas.width;
  const h = ctx.canvas.height;
  ctx.clearRect(0, 0, w, h);
  if (data.length < 2) return;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  ctx.strokeStyle = '#38bdf8';
  ctx.lineWidth = 2;
  ctx.beginPath();
  data.forEach((v, i) => {
    const x = (i / 59) * w;
    const y = h - 6 - ((v - min) / span) * (h - 12);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}
