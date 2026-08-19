export function createMockSim() {
  const state = {
    x: 0,
    y: 0,
    theta: 0,
    vx: 0,
    omega: 0,
    time: 0,
    stepsPerSecond: 56100,
    frameTimeMs: 8.2,
    agents: 1,
    modelSize: 0,
    mission: 'IDLE',
    waypoint: 0,
  };

  const dt = 1 / 60;
  const waypoints = [
    [6, 0],
    [6, 5],
    [-6, 5],
    [-6, -5],
    [0, -5],
    [0, 0],
  ];
  const totalWaypoints = waypoints.length;
  const V_MAX = 2.5;
  const OMEGA_MAX = 2.2;

  function step() {
    state.time += dt;

    // Telemetría con jitter leve para que "viva" siempre, aunque la misión no corra
    state.stepsPerSecond = Math.round(56100 + Math.sin(state.time * 3) * 400);
    state.frameTimeMs = 8.2 + Math.sin(state.time * 5) * 0.6;

    if (state.mission !== 'RUNNING') {
      state.vx = 0;
      state.omega = 0;
      return;
    }

    const [tx, ty] = waypoints[state.waypoint];
    const dx = tx - state.x;
    const dy = ty - state.y;
    const dist = Math.hypot(dx, dy);
    if (dist < 0.35) {
      state.waypoint += 1;
      if (state.waypoint >= totalWaypoints) {
        state.mission = 'COMPLETED';
        state.vx = 0;
        state.omega = 0;
        return;
      }
    }

    const heading = Math.atan2(dy, dx);
    let dTheta = heading - state.theta;
    dTheta = Math.atan2(Math.sin(dTheta), Math.cos(dTheta));

    state.vx = Math.min(V_MAX, 0.7 + dist * 0.5);
    state.omega = Math.max(-OMEGA_MAX, Math.min(OMEGA_MAX, dTheta * 3));

    // Modelo de transmisión diferencial exacto
    state.x += state.vx * Math.cos(state.theta) * dt;
    state.y += state.vx * Math.sin(state.theta) * dt;
    state.theta += state.omega * dt;
  }

  function startMission() {
    state.x = 0;
    state.y = 0;
    state.theta = 0;
    state.time = 0;
    state.waypoint = 0;
    state.mission = 'RUNNING';
  }

  function pauseMission() {
    if (state.mission === 'RUNNING') state.mission = 'PAUSED';
  }

  function resumeMission() {
    if (state.mission === 'PAUSED') state.mission = 'RUNNING';
  }

  function abortMission() {
    state.mission = 'ABORTED';
    state.vx = 0;
    state.omega = 0;
  }

  function toggleMission() {
    if (state.mission === 'RUNNING') pauseMission();
    else if (state.mission === 'PAUSED') resumeMission();
    else startMission();
  }

  return {
    state,
    step,
    startMission,
    pauseMission,
    resumeMission,
    abortMission,
    toggleMission,
    waypoints,
    totalWaypoints,
  };
}
