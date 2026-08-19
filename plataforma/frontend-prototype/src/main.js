import { createMockSim } from './sim.js';
import { variants } from './variants/index.js';
import './styles.css';

const sim = createMockSim();
const keys = Object.keys(variants);
let active = null;

function currentKey() {
  return new URL(window.location.href).searchParams.get('variant') ?? keys[0];
}

function mount(key) {
  if (active) active.dispose();
  const container = document.getElementById('app');
  container.innerHTML = '';
  const spec = variants[key];
  active = spec.mount(container, sim.state);
  document.getElementById('variant-label').textContent = `${key.toUpperCase()} — ${spec.name}`;
}

function switchTo(key) {
  const url = new URL(window.location.href);
  url.searchParams.set('variant', key);
  history.replaceState({}, '', url);
  mount(key);
}

function cycle(dir) {
  const i = (keys.indexOf(currentKey()) + dir + keys.length) % keys.length;
  switchTo(keys[i]);
}

document.getElementById('prev').addEventListener('click', () => cycle(-1));
document.getElementById('next').addEventListener('click', () => cycle(1));
window.addEventListener('keydown', (e) => {
  const t = e.target;
  if (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable) return;
  if (e.key === 'ArrowLeft') cycle(-1);
  if (e.key === 'ArrowRight') cycle(1);
});

mount(currentKey());
