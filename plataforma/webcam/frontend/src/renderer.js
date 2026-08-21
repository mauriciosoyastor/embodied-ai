import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export function createRenderer(container) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0f14);

  const grid = new THREE.GridHelper(24, 24, 0x2a3a4d, 0x18222e);
  scene.add(grid);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x223344, 1.0));
  const sun = new THREE.DirectionalLight(0xffffff, 1.2);
  sun.position.set(6, 12, 5);
  scene.add(sun);

  const w = container.clientWidth || 800;
  const h = container.clientHeight || 600;
  const camera = new THREE.PerspectiveCamera(55, w / h, 0.1, 200);
  camera.position.set(6, 6, 8);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(w, h);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.target.set(0, 0, 0);

  let raf = 0;
  let running = true;
  let update = () => {};
  const clock = new THREE.Clock();

  function tick() {
    if (!running) return;
    raf = requestAnimationFrame(tick);
    const dt = clock.getDelta();
    update(dt);
    controls.update();
    renderer.render(scene, camera);
  }
  tick();

  function dispose() {
    running = false;
    cancelAnimationFrame(raf);
    controls.dispose();
    scene.traverse((o) => {
      if (!o.isMesh) return;
      o.geometry?.dispose();
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of mats) m?.dispose();
    });
    renderer.dispose();
    renderer.forceContextLoss?.();
  }

  return { scene, camera, controls, renderer, setUpdate: (fn) => { update = fn; }, dispose };
}
