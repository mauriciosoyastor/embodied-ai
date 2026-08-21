export function createMissionControls(sim) {
  const bar = document.createElement('div');
  bar.className = 'mission-bar';

  const primary = document.createElement('button');
  primary.className = 'mission-primary';
  const abort = document.createElement('button');
  abort.className = 'mission-abort';
  abort.textContent = 'Abortar';

  primary.addEventListener('click', () => sim.toggleMission());
  abort.addEventListener('click', () => sim.abortMission());

  function render() {
    const m = sim.state.mission;
    primary.textContent =
      m === 'RUNNING' ? 'Pausar' :
      m === 'PAUSED' ? 'Reanudar' :
      m === 'COMPLETED' ? 'Misión completada — reiniciar' :
      m === 'ABORTED' ? 'Reintentar' :
      'Iniciar misión';
    abort.disabled = m !== 'RUNNING' && m !== 'PAUSED';
  }

  render();
  bar.append(primary, abort);
  return { bar, render };
}

export function missionStatus(state) {
  const label =
    state.mission === 'RUNNING' ? 'EN CURSO' :
    state.mission === 'PAUSED' ? 'PAUSADA' :
    state.mission === 'COMPLETED' ? 'COMPLETADA' :
    state.mission === 'ABORTED' ? 'ABORTADA' :
    'EN ESPERA';
  return { label, tone: state.mission };
}

export function missionProgress(state, total) {
  const current = Math.min(state.waypoint + 1, total);
  return state.mission === 'COMPLETED'
    ? `${total}/${total}`
    : `${current}/${total}`;
}
