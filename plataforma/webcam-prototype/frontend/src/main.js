import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import "./styles.css";

const video = document.getElementById("video");
const camCanvas = document.getElementById("cam");
const overlayCanvas = document.getElementById("overlay");
const camCtx = camCanvas.getContext("2d");
const ovCtx = overlayCanvas.getContext("2d");
const chipGesto = document.getElementById("chip-gesto");
const chipLoop = document.getElementById("estado-loop");
const telemetria = document.getElementById("telemetria");

const COLORES = ["#58a6ff", "#3fb950", "#d29922", "#f85149", "#bc8cff", "#39c5cf"];
const GESTO_FSM = { open_palm: "PAUSED", fist: "ABORTED", thumbs_up: "RUNNING", none: "—" };

const CAM_W = 640;
const CAM_H = 480;

// ---- escena Three.js (render del navegador) ----
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0d1117);
const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100);
camera.position.set(4, 3.5, 5);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({ antialias: true });
document.getElementById("scene").appendChild(renderer.domElement);

const grid = new THREE.GridHelper(10, 10, 0x30363d, 0x21262d);
scene.add(grid);

const suelo = new THREE.Mesh(
  new THREE.PlaneGeometry(10, 10),
  new THREE.MeshStandardMaterial({ color: 0x161b22, roughness: 1 })
);
suelo.rotation.x = -Math.PI / 2;
scene.add(suelo);

const robot = new THREE.Group();
const base = new THREE.Mesh(
  new THREE.BoxGeometry(0.8, 0.4, 0.9),
  new THREE.MeshStandardMaterial({ color: 0x3fb950 })
);
base.position.y = 0.2;
robot.add(base);
const cabeza = new THREE.Mesh(
  new THREE.BoxGeometry(0.3, 0.25, 0.3),
  new THREE.MeshStandardMaterial({ color: 0x58a6ff })
);
cabeza.position.y = 0.55;
robot.add(cabeza);
scene.add(robot);

scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 1.1));

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

function resize() {
  const el = document.getElementById("scene");
  const w = el.clientWidth || 300;
  const h = el.clientHeight || 300;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h, false);
}

function animar() {
  requestAnimationFrame(animar);
  controls.update();
  robot.rotation.y += 0.003;
  renderer.render(scene, camera);
}

// ---- webcam ----
async function iniciarWebcam() {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: { ideal: CAM_W }, height: { ideal: CAM_H } },
    audio: false,
  });
  video.srcObject = stream;
  await video.play();
  camCanvas.width = CAM_W;
  camCanvas.height = CAM_H;
  overlayCanvas.width = CAM_W;
  overlayCanvas.height = CAM_H;

  const dibujar = () => {
    camCtx.drawImage(video, 0, 0, CAM_W, CAM_H);
    requestAnimationFrame(dibujar);
  };
  dibujar();
}

// ---- websocket + envio de frames ----
let ws = null;
let enviados = 0;
let recibidos = 0;
let t0 = performance.now();
let ultimoMensaje = 0;

function conectar() {
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.binaryType = "blob";
  ws.onopen = () => {
    chipLoop.textContent = "loop: conectado";
    chipLoop.classList.replace("off", "on");
    setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        camCanvas.toBlob((blob) => {
          if (blob && ws.readyState === WebSocket.OPEN) {
            ws.send(blob);
            enviados++;
          }
        }, "image/jpeg", 0.7);
      }
    }, 80);
  };
  ws.onmessage = (e) => {
    recibidos++;
    ultimoMensaje = performance.now();
    const r = JSON.parse(e.data);
    chipGesto.textContent = `gesto: ${r.gesto} → ${GESTO_FSM[r.gesto]}`;
    chipGesto.classList.toggle("on", r.gesto !== "none");
    chipGesto.classList.toggle("off", r.gesto === "none");
    dibujarDetecciones(r.objetos);
    const fps = ((enviados / (performance.now() - t0)) * 1000).toFixed(0);
    telemetria.textContent =
      `env ${enviados} · recv ${recibidos} · ${fps} fps · ` +
      `total ${r.total_ms.toFixed(0)} ms · yolo ${r.yolo_ms.toFixed(0)} · mano ${r.mano_ms.toFixed(0)} · ` +
      `${r.objetos.length} obj`;
  };
  ws.onclose = () => {
    chipLoop.textContent = "loop: reconectando…";
    chipLoop.classList.replace("on", "off");
    setTimeout(conectar, 1500);
  };
  ws.onerror = () => ws.close();
}

function dibujarDetecciones(objetos) {
  ovCtx.clearRect(0, 0, CAM_W, CAM_H);
  for (const [i, o] of objetos.entries()) {
    const color = COLORES[i % COLORES.length];
    ovCtx.strokeStyle = color;
    ovCtx.lineWidth = 2;
    ovCtx.strokeRect(o.x1, o.y1, o.x2 - o.x1, o.y2 - o.y1);
    ovCtx.fillStyle = color;
    ovCtx.font = "12px system-ui";
    const etiqueta = `${o.etiqueta} ${(o.conf * 100).toFixed(0)}%`;
    const w = ovCtx.measureText(etiqueta).width + 8;
    ovCtx.fillRect(o.x1, o.y1 - 18, w, 18);
    ovCtx.fillStyle = "#000";
    ovCtx.fillText(etiqueta, o.x1 + 4, o.y1 - 5);
  }
}

resize();
window.addEventListener("resize", resize);
iniciarWebcam();
conectar();
animar();
