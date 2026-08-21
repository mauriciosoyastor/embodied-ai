import * as THREE from 'three';

const WHEEL_R = 0.18;

export function createRobot() {
  const group = new THREE.Group();

  const chassis = new THREE.Mesh(
    new THREE.BoxGeometry(0.9, 0.22, 0.6),
    new THREE.MeshStandardMaterial({ color: 0x3b82f6, roughness: 0.5 })
  );
  chassis.position.y = 0.24;

  const top = new THREE.Mesh(
    new THREE.BoxGeometry(0.4, 0.18, 0.4),
    new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.8 })
  );
  top.position.y = 0.44;

  const wheelMat = new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.9 });
  const wheelGeo = new THREE.CylinderGeometry(WHEEL_R, WHEEL_R, 0.1, 16);
  const wheels = [];
  for (const [sx, sz] of [[-0.3, 0.31], [-0.3, -0.31]]) {
    const pivot = new THREE.Group();
    pivot.position.set(sx, 0.18, sz);
    pivot.rotation.z = Math.PI / 2;
    const wheel = new THREE.Mesh(wheelGeo, wheelMat);
    pivot.add(wheel);
    group.add(pivot);
    wheels.push(wheel);
  }

  const caster = new THREE.Mesh(
    new THREE.SphereGeometry(0.07, 10, 10),
    wheelMat
  );
  caster.position.set(0.32, 0.07, 0);

  group.add(chassis, top, caster);
  return { group, wheels };
}

export function applyPose(robot, state, dt) {
  robot.group.position.set(state.x, 0, state.y);
  robot.group.rotation.y = -state.theta;
  const spin = (state.vx * dt) / WHEEL_R;
  for (const w of robot.wheels) w.rotation.y += spin;
}
