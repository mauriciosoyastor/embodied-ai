# R1 — MuJoCo + Gymnasium para la plataforma virtual de entrenamiento (robot diferencial)

Fecha: 2026-08-19. Investigación contra fuentes primarias (docs oficiales de DeepMind MuJoCo y bindings Python, docs y changelog de Gymnasium/Farama, repo `google-deepmind/mujoco_menagerie`, `anair13/mj_envs`, PyPI/conda-forge). Context pointer: issue #29 (https://github.com/mauriciosoyastor/embodied-ai/issues/29).

## Pregunta

¿Cuál es el estado actual (2026) de **MuJoCo + Gymnasium** para el primer escenario de la plataforma (robot diferencial terrestre validado con agente FSM vía `cmd_vel` (v_x, omega_z))? Cubre: versiones de `mujoco`/`mujoco-python`/`gymnasium` y su integración (`gymnasium.envs.mujoco`); modelos de robot diferencial mantenidos (`mujoco_menagerie`, `mj_envs`, car-like/two-wheel) y cuál es más apto para control `cmd_vel`; cómo se expone el entorno como Gym env (obs/acción/reward/step/reset); requisitos y rendimiento en Windows 11 / WSL2 (GLFW, EGL, headless para CI); y un benchmark mínimo de steps/s en CPU.

## Hallazgos

### 1. Versiones actuales (agosto 2026)

- **`mujoco` (PyPI)** — bindings Python canónicos de DeepMind: **v3.11.0** (2026-07-27), `Python >= 3.10`. El paquete incluye el motor MuJoCo embebido (`pip install mujoco`). Versionado: `major.minor.micro` coincide con la versión del motor; el `.postN` indica fixes del binding para la misma versión del motor. La 3.11.0 agrega free-threading (PEP 703) para Python 3.14. Fuente: https://pypi.org/project/mujoco/ y https://github.com/google-deepmind/mujoco/releases/tag/3.11.0
- **`mujoco-python` (conda-forge)** — mismo software bajo nombre de canal conda: última build **3.10.0** (win-64/linux-64/linux-aarch64, subida 2026-06-22); el 3.11.0 aún no está empaquetado en conda-forge. Fuente: https://anaconda.org/conda-forge/mujoco-python
- **`gymnasium` (PyPI)** — **v1.3.0** (2026-04-22), `Python >= 3.10` (soporta 3.10–3.14 en Linux/macOS). Extra oficial para MuJoCo: `pip install "gymnasium[mujoco]"` → instala `mujoco >=2.1.5`, `imageio >=2.14.1`, `packaging >=23.0`. Fuentes: https://pypi.org/project/gymnasium/ y https://github.com/Farama-Foundation/Gymnasium/blob/main/pyproject.toml
- **Integración**: los entornos viven en `gymnasium.envs.mujoco`. La doc marca las versiones **`v5` como recomendadas** (`mujoco >= 2.3.3`, "most features, the least bugs"); `v4` se mantiene por reproducibilidad (`mujoco >= 2.1.3`); `v3`/`v2` (basadas en `mujoco-py`) se **migraron al paquete `gymnasium-robotics`** a partir de gymnasium v1.2. Fuente: https://gymnasium.farama.org/environments/mujoco/ (sección "Versions")

### 2. Cómo se expone el entorno como Gym env (`gymnasium.envs.mujoco.MujocoEnv`)

Clase base `MujocoEnv(gym.Env)` en `gymnasium/envs/mujoco/mujoco_env.py` (Fuente: https://github.com/Farama-Foundation/Gymnasium/blob/main/gymnasium/envs/mujoco/mujoco_env.py):

- **Carga del modelo**: `mujoco.MjModel.from_xml_path(...)`; con `xml_file` se puede apuntar a **cualquier MJCF propio** (soporte de modelos custom desde v5). `frame_skip` controla `dt = model.opt.timestep * frame_skip`.
- **Observación**: el espacio default es `qpos + qvel` concatenados (documentado en la doc de MuJoCo environments); algunos envs agregan `cfrc_ext` (fuerzas externas). En `Ant-v5` la obs default es `Box(-inf, inf, (105,), float64)` (qpos 13 − 2 posiciones excluidas + qvel 14 + cfrc 78), y `exclude_current_positions_from_observation` permite incluir x/y del torso.
- **Acción**: `spaces.Box(low, high, dtype=float32)` construido desde `model.actuator_ctrlrange` (bounds de los actuadores del modelo) → el espacio de acción queda definido por el MJCF.
- **Reward**: por-env; en `Ant-v5`: `healthy_reward + forward_reward − ctrl_cost − contact_cost`, con los términos individuales en `info` (`reward_forward`, `reward_ctrl`, `reward_contact`, `reward_survive`).
- **`step(action)`**: valida dimensión contra `model.nu`, hace `_step_mujoco_simulation(ctrl, frame_skip)` → `mj_step(model, data, nstep=n_frames)` + `mj_rnePostConstraint`, y devuelve `(obs, reward, terminated, truncated, info)`. La truncación por tiempo la aplica el wrapper `TimeLimit` de `make`.
- **`reset()`**: `mj_resetData` + `reset_model()` (setea `qpos`/`qvel`, típicamente con ruido gaussiano/uniforme vía `self.np_random`) y devuelve `(obs, info)`.
- **Rendering**: modos `human` (ventana GLFW), `rgb_array`, `depth_array`, `rgbd_tuple`; el backend OpenGL se selecciona por env var (ver sección 4).

### 3. Modelos de robot diferencial (menagerie vs mj_envs)

- **`mujoco_menagerie` (google-deepmind)** — colección curada y **activamente mantenida** (482 commits; ~100 modelos; CI; sistema de grados de calidad A+/A/B/C pendiente de aplicar). No hay un "toy" two-wheel clásico, pero sí **manipuladores móviles con base diferencial**. El más apto para control tipo `cmd_vel` es **Hello Robot Stretch 2** (`hello_robot_stretch`, requiere **MuJoCo >= 3.3.0**): su base usa un `freejoint` y dos actuadores `motor` sobre tendons que combinan `joint_left_wheel`/`joint_right_wheel`:
  - `<motor name="forward" tendon="forward">` → tendon `forward` = 0.5·left + 0.5·right (≈ velocidad lineal).
  - `<motor name="turn" tendon="turn">` → tendon `turn` = −0.5·left + 0.5·right (≈ velocidad angular).
  - `gear=3`, `ctrlrange=-1..1`, `forcerange=-100..100`, damping 0.3 por rueda.
  Esto **mapea 1:1 al protocolo `cmd_vel` (v_x, omega_z)**: con `forward`/`turn` no hay que resolver cinemática inversa de ruedas por código. Fuente: https://github.com/google-deepmind/mujoco_menagerie/tree/main/hello_robot_stretch y https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/main/hello_robot_stretch/stretch.xml (README + MJCF).
  - Alternativas de base diferencial en menagerie: **PAL TIAGo** (`pal_tiago`, base diferencial con ruedas), **Google Robot** (`google_robot`, base diferencial con brazo). `robot_soccer_kit` es **omnidireccional** (ruedas con rodillos pasivos), no diferencial. Fuente: https://github.com/google-deepmind/mujoco_menagerie (README, lista de modelos).
  - Si se prefiere un escenario mínimalista (menos DOFs, sin brazo), lo más sensato es **escribir un MJCF propio** de dos ruedas + caster y cargarlo con `MujocoEnv(xml_file=...)`; menagerie no tiene un two-wheel de juguete.
- **`mj_envs` (`anair13/mj_envs`)** — colección antigua (2020) de manipulación dextrosa construida sobre **`mujoco-py` + `gym`** (API vieja, no gymnasium); sin mantenimiento (los forks que la usan, ej. `ExPLORe`, están archivados). **No recomendado** para el escenario terrestre. Fuentes: https://github.com/anair13/mj_envs y https://github.com/facebookresearch/ExPLORe (status ARCHIVED).
- **Conclusión**: usar **menagerie + Stretch 2** como primer escenario (actuadores `forward`/`turn` listos para `cmd_vel`), o un MJCF propio si se quiere minimalista. `mj_envs` queda descartado.

### 4. Instalación y rendimiento en Windows 11 / WSL2 (GLFW, EGL, headless)

- **Backends de renderizado** (por env var `MUJOCO_GL`): `glfw` (default; ventana en GPU), `egl` (headless en GPU), `osmesa` (headless en CPU). Fuentes: https://gymnasium.farama.org/environments/mujoco/ (sección "Rendering Backend") y https://mujoco.readthedocs.io/en/stable/programming/index.html (sección OpenGL).
- **Plataformas**: en **Linux** MuJoCo soporta GLX (X11), OSMesa (headless CPU) y EGL (headless GPU). En **Windows y macOS** solo existe la OpenGL canónica del sistema vía GLFW; **EGL/OSMesa son exclusivos de Linux**. El soporte de `osmesa` en Windows/macOS fue rechazado en upstream y `osmesa` además se está retirando de Mesa. Fuentes: https://mujoco.readthedocs.io/en/stable/programming/index.html y https://github.com/google-deepmind/mujoco/issues/2164
- **Headless para CI — punto clave**: la **física no requiere OpenGL** (`mj_step` corre sin contexto gráfico); OpenGL solo se necesita si se llama al renderer (`render_mode != None`). Por lo tanto un benchmark o un loop Gym con `render_mode=None` corre **headless en cualquier OS**, sin instalar GLFW/EGL. Para CI que sí renderice: runners Linux + `MUJOCO_GL=egl` (GPU) u `osmesa` (CPU).
- **Windows**: `mujoco` tiene wheels precompilados win-64. **Gymnasium no soporta Windows oficialmente** ("We support and test for Python 3.10-3.14 on Linux and macOS. We will accept PRs related to Windows, but do not officially support it"). Para desarrollo local en Windows conviene correr el stack en **WSL2** (mismo Linux, GLFW vía WSLg, EGL con driver NVIDIA). Fuentes: https://github.com/Farama-Foundation/Gymnasium (README) y https://github.com/google-deepmind/mujoco (releases win-x86_64).
- **Notas de rendimiento del engine**: para medir SPS con ruido mínimo usar el plan de energía **High Performance** en Windows (evita el throttling de frecuencia) y, en CPUs big.LITTLE, fijar afinidad al mismo tipo de núcleos (`start /affinity` en Windows, `taskset` en Linux). Fuente: https://mujoco.readthedocs.io/en/stable/programming/samples.html (sección `testspeed`).

### 5. Benchmark mínimo (steps/s en CPU)

- **Herramienta oficial**: MuJoCo incluye el sample **`testspeed`** (`sample/testspeed.cc`): rollouts de dinámica pasiva (con ruido de control opcional), `nthread` paralelo (óptimo = núcleos lógicos) y thread-pool interno (`nenginethread`) para escenas grandes. Fuente: https://mujoco.readthedocs.io/en/stable/programming/samples.html
- **Referencia de CPU de DeepMind**: en la discusión oficial de MJX (#2812) se reportan **~2.7M steps/s totales** para un humanoid simple en CPU de 64 núcleos (128 rollouts paralelos, SPS total); el autor de MuJoCo señala que para física las CPUs de muchos núcleos son competitivas frente a GPU y más fáciles de depurar. Fuente: https://github.com/google-deepmind/mujoco/discussions/2812
- **Referencia GPU (contraste)**: MuJoCo Playground (MJX + Madrona batch rendering en A100) mide ~403k steps/s (Cartpole) y ~37k steps/s (Franka) con observaciones de píxeles. Fuente: https://arxiv.org/abs/2502.08844 (Fig. 5) y https://playground.mujoco.org/assets/playground_technical_report.pdf

### 6. Benchmark local (máquina del autor, Windows)

Medición real en esta máquina (Windows, `mujoco` 3.11.0, Python 3.13, venv temporal en `%LOCALAPPDATA%\Temp\opencode`):

- **Modelo**: MJCF mínimo de robot diferencial (chasis + 2 ruedas con motor + caster sobre plano; `nq=13 nv=11 nu=2`, dt=0.01 s, `implicitfast` + `noslip_iterations=2`), el escenario objetivo de la plataforma. Como referencia también se corrió la escena compleja `testdata/model.xml` del paquete.
- **Método**: `mj_step` en loop con `mj_forward` inicial y medición por `time.perf_counter` (patrón del sample `testspeed`, 10.000 pasos, sin renderizado; la física no toca OpenGL).
- **Resultado** (Windows, `mujoco` 3.11.0, Python 3.12, venv temporal en `%LOCALAPPDATA%\Temp\opencode`):
  - Robot diferencial mínimo: **~56,000 steps/s** en un solo hilo (dt=0.01 s → realtime ~560×). Un `step()` de gym con `frame_skip=1` equivale a un `mj_step`; con `frame_skip=5` (dt=0.05 s) el SPS de gym sería ~5× menor en sim-steps pero igual dt por step.
  - Escena compleja de referencia (`model.xml`, 14 bodies): ~19,800 steps/s (dt=0.002 s → ~40×).
  - Núcleos lógicos detectados: **12**; el benchmark fue monohilo (un rollout); `testspeed` con `nthread`=núcleos lógicos escala a ~12 rollouts paralelos.

> Nota: el valor se registró con el plan de energía vigente de la máquina; para números reproducibles conviene el plan High Performance. El renderizado no se usó (headless puro de física).

## Recomendación

1. **Stack de versiones**: `mujoco` 3.11.0 (PyPI) + `gymnasium` 1.3.0 con extra `[mujoco]`. Trabajar en **WSL2** para desarrollo (Linux nativo, EGL/GLFW vía WSLg) aunque `mujoco` corre en Windows; el backend FastAPI/visor Three.js consumirá el env vía Python.
2. **Primer escenario**: robot **Stretch 2 de `mujoco_menagerie`** como base diferencial lista para `cmd_vel`: los actuadores `forward`/`turn` (tendons sobre las dos ruedas) reciben directamente (v_x, omega_z). Si se quiere un escenario mínimalista sin brazo, escribir un **MJCF propio** (dos ruedas + caster) y cargarlo con `MujocoEnv(xml_file=...)` y `frame_skip` para fijar `dt`.
3. **Env Gym**: subclase de `gymnasium.envs.mujoco.MujocoEnv`; acción = `Box` desde `actuator_ctrlrange` (los dos actuadores de la base), obs = `qpos + qvel` (+ opcionalmente posición global x/y para la FSM), reward simple orientado a tarea (avance en x + castigo por control). `step`/`reset`/`terminated`/`truncated` según el contrato de la sección 2.
4. **CI/headless**: la física no necesita GL → benchmarks y tests de `step/reset` con `render_mode=None` corren headless en cualquier runner (incluido Windows). Si el CI necesita imágenes, runner Linux con `MUJOCO_GL=egl` u `osmesa`.
5. **Métricas del recomendador**: con el benchmark local como base se pueden medir **steps/s** (SPS), frame time del visor (independiente: Three.js del lado web), nº de agentes (escalar con `nthread`/rollouts paralelos de `testspeed`) y VRAM (solo releva si se renderiza desde MuJoCo o se usa MJX en GPU; el visor web Three.js no consume VRAM del backend).

## Fuentes

- MuJoCo (PyPI) — bindings Python canónicos: https://pypi.org/project/mujoco/
- MuJoCo releases (3.11.0, 2026-07-27): https://github.com/google-deepmind/mujoco/releases/tag/3.11.0
- MuJoCo changelog: https://mujoco.readthedocs.io/en/stable/changelog.html
- MuJoCo Python bindings docs: https://mujoco.readthedocs.io/en/stable/python.html
- MuJoCo programming / OpenGL y samples (testspeed): https://mujoco.readthedocs.io/en/stable/programming/index.html y https://mujoco.readthedocs.io/en/stable/programming/samples.html
- MuJoCo discusión MJX CPU vs GPU (#2812): https://github.com/google-deepmind/mujoco/discussions/2812
- MuJoCo issue #2164 (osmesa en Windows/macOS): https://github.com/google-deepmind/mujoco/issues/2164
- gymnasium (PyPI): https://pypi.org/project/gymnasium/ ; changelog v1.3.0: https://gymnasium.farama.org/gymnasium_release_notes/index.html
- Gymnasium — MuJoCo environments: https://gymnasium.farama.org/environments/mujoco/
- Gymnasium — `mujoco_env.py` (MujocoEnv): https://github.com/Farama-Foundation/Gymnasium/blob/main/gymnasium/envs/mujoco/mujoco_env.py
- Gymnasium — `ant_v5.py` (contrato obs/action/reward): https://github.com/Farama-Foundation/Gymnasium/blob/main/gymnasium/envs/mujoco/ant_v5.py
- Gymnasium — pyproject.toml (extra `[mujoco]`): https://github.com/Farama-Foundation/Gymnasium/blob/main/pyproject.toml
- mujoco_menagerie (README + modelos): https://github.com/google-deepmind/mujoco_menagerie ; Stretch 2: https://github.com/google-deepmind/mujoco_menagerie/tree/main/hello_robot_stretch y MJCF: https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/main/hello_robot_stretch/stretch.xml
- mj_envs (anair13): https://github.com/anair13/mj_envs ; ExPLoRE (archivado): https://github.com/facebookresearch/ExPLoRE
- mujoco-python (conda-forge): https://anaconda.org/conda-forge/mujoco-python
- MuJoCo Playground paper: https://arxiv.org/abs/2502.08844 y technical report: https://playground.mujoco.org/assets/playground_technical_report.pdf
