# R1 — Estado actual (2026) del ecosistema MuJoCo + Gymnasium para un robot diferencial terrestre

## Pregunta

¿Cuál es el estado actual (2026) de **MuJoCo + Gymnasium** para armar un escenario de juguete con un robot diferencial terrestre controlado por `cmd_vel` (`v_x`, `omega_z`)? Se investiga: versiones actuales de `mujoco`, `mujoco-python` y `gymnasium` y cómo se integran (`gymnasium.envs.mujoco`); modelos de robot diferencial existentes y mantenidos (`mujoco_menagerie`, `mj_envs`, modelos car-like / two-wheel) y cuál es el más apto para control por velocidad lineal/angular; cómo se expone el entorno como Gym env (observación, acción, reward, step/reset); requisitos de instalación y rendimiento en Windows 11 / WSL2 (GLFW, EGL, headless para CI); y benchmark mínimo de FPS de simulación (steps/s) en CPU.

## Hallazgos

### 1. Versiones actuales: `mujoco`, `mujoco-python`, `gymnasium` y la integración

- **`mujoco` (motor + bindings nativos)**: la versión más reciente es **3.11.0 (27 de julio 2026)**, con 3.10.0 (22 jun 2026), 3.9.0 (27 may 2026) y 3.8.x (abr/may 2026) en la línea estable de 2026. El `mujoco` de PyPI es el paquete canónico (bindings pybind11 mantenidos por Google DeepMind); **el motor se distribuye dentro del wheel** (`pip install mujoco`, Apache-2.0) y no requiere descarga aparte. El número de versión de `major.minor.micro` coincide con la versión del motor. Requiere **Python >=3.10** (v3.11.0); 3.8.0 añadió soporte para Python 3.14 y 3.11.0 añadió bindings con *free-threading* (PEP 703) para 3.14.
  Fuentes: https://mujoco.readthedocs.io/en/stable/changelog.html , https://github.com/google-deepmind/mujoco/releases , https://pypi.org/project/mujoco/ , https://mujoco.readthedocs.io/en/stable/python.html

- **No existe un paquete separado "mujoco-python"**: los bindings oficiales son el paquete `mujoco`. El paquete legado `mujoco-py` (openai) quedó **sin mantenimiento y obsoleto**; Gymnasium migró fuera de él (ver punto 1 de Gymnasium). Para usuarios de `mujoco-py`, MuJoCo publica una guía de migración (`migration-from-mujoco-py`).
  Fuentes: https://mujoco.readthedocs.io/en/stable/python.html (sección "For mujoco-py users") , https://gymnasium.farama.org/environments/mujoco/

- **`gymnasium`**: la versión más reciente es **v1.3.0 (22 abril 2026)**; la serie v1.2.x llegó a v1.2.3 (18 dic 2025). Desde **v1.2.0 (27 jun 2025)**, los entornos MuJoCo v2/v3 (basados en `mujoco-py`) fueron **migrados a `gymnasium-robotics`** y solo se mantienen en Gymnasium las versiones **v5** (recomendada, requiere `mujoco>=2.3.3`) y **v4** (`mujoco>=2.1.3`, mantenida por reproducibilidad). v1.2.0 añadió soporte para Python 3.13 y dejó de soportar 3.8/3.9. La integración se instala con `pip install "gymnasium[mujoco]"` (instala `mujoco` como dependencia).
  Fuentes: https://gymnasium.farama.org/gymnasium_release_notes/index.html , https://github.com/Farama-Foundation/Gymnasium/releases/tag/v1.2.0 , https://gymnasium.farama.org/environments/mujoco/

- **`gymnasium.envs.mujoco`**: módulo de entornos MuJoCo de Gymnasium. Incluye 11 entornos (Ant, HalfCheetah, Hopper, Humanoid, HumanoidStandup, InvertedDoublePendulum, InvertedPendulum, Pusher, Reacher, Swimmer, Walker2D). **Ninguno es un robot diferencial terrestre**; no hay en este módulo un entorno "two-wheel/car" listo. La clase base `MujocoEnv(gym.Env)` es la vía oficial para exponer un modelo MJCF propio como Gym env (ver punto 3).
  Fuente: https://gymnasium.farama.org/environments/mujoco/

### 2. Modelos de robot diferencial existentes y mantenidos

- **`mujoco_menagerie`** (curado por Google DeepMind, Apache-2.0 salvo indicación por modelo): colección activa, CI verde. **No hay ningún robot diferencial puro (two-wheel) de juguete** en el repositorio. Lo más cercano son robots móviles con base sobre ruedas:
  - **TIAGo** (pal_tiago, 22 DoF, requiere MuJoCo >=2.2.2): base con tracción diferencial + torso + brazo; el paquete incluye `scene_velocity.xml`, `scene_motor.xml` y `scene_position.xml`, es decir, **actuadores de velocidad y posición ya definidos** (ideal para probar control por velocidad). Licencia Apache-2.0.
  - **Hello Robot Stretch 2/3** y **TidyBot**: bases móviles diferenciales con brazo.
  - **ToddlerBot 2XC/2XM** y **robot_soccer_kit**: robots sobre ruedas, pero con ruedas pasivas/omnidireccionales modeladas con muchos DoF (no aptos como juguete diferencial simple).
  - `mujoco_menagerie` es **dependencia de solo modelos** (git clone o vía `robot_descriptions`); los modelos se cargan con `mujoco.MjModel.from_xml_path(...)`. Cada modelo declara la versión mínima de MuJoCo en su README.
  Fuentes: https://github.com/google-deepmind/mujoco_menagerie , https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/main/pal_tiago/README.md , https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/main/toddlerbot_2xc/README.md , https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/main/robot_soccer_kit/README.md

- **`mj_envs` (google-deepmind/mj_envs)**: el repo `google-deepmind/mj_envs` ya **no existe (404)**; el proyecto original fue absorbido por **RoboHive** (`vikashplus/robohive`, API gym, suites de manipulación de mano/brazo y Myo). No aporta un robot diferencial terrestre; para el escenario de juguete **no es relevante y no debe usarse**.
  Fuentes: https://github.com/google-deepmind/mj_envs (404) , https://github.com/vikashplus/robohive

- **Modelos car-like / two-wheel oficiales y de referencia**:
  - El repo de MuJoCo incluye **`model/car/car.xml`** (el modelo "car" oficial, car-like con ruedas motorizadas y dirección), usado como referencia por el equipo.
  - El patrón canónico de **robot diferencial de 2 ruedas** está documentado en el discussion #2392 del repo de MuJoCo: chasis con `free joint`, dos ruedas con `hinge` joints y un `motor` (o `velocity` actuator) cada una, más rueda loca (caster). Lección clave de esa discusión: **los `motor` puros (torque) requieren damping (o servos de velocidad/posición) para un comportamiento estable**; la forma típica de "cmd_vel" es usar actuadores de **velocidad** (o posición = fuente de velocidad ideal) y mapear `(v, ω) → (ω_left, ω_right)` con cinemática diferencial: `ω_L = (v − ω·d/2)/r`, `ω_R = (v + ω·d/2)/r`, con `d` = distancia entre ruedas y `r` = radio.
  Fuentes: https://github.com/google-deepmind/mujoco/discussions/2392 , https://github.com/google-deepmind/mujoco/tree/main/model (carpeta `car`)

- **Vía ROS 2 (a futuro)**: `ros-controls/mujoco_ros2_control` expone MuJoCo como hardware interface de `ros2_control`, con soporte explícito de **actuadores `velocity`/`motor` para ruedas** y PID, útil si más adelante se quiere conectar el escenario a un stack de navegación ROS. No es necesario para el juguete.
  Fuente: https://github.com/ros-controls/mujoco_ros2_control

- **Conclusión del modelo recomendado**: para un robot con control `cmd_vel`, lo más apto es **un MJCF propio estilo TurtleBot** (chasis + 2 ruedas motrices con actuadores `velocity` + caster, ~50 líneas), porque (a) no existe un two-wheel puro curado en Menagerie, (b) mapea directo a `cmd_vel`, y (c) es la práctica estándar de la comunidad. Como referencia de un robot diferencial real con actuadores de velocidad ya definidos, se puede partir de **TIAGo (`scene_velocity.xml`) de Menagerie**.

### 3. Cómo se expone el entorno como Gym env (observación, acción, reward, step/reset)

- **Clase base `gymnasium.envs.mujoco.MujocoEnv`**: un entorno MuJoCo propio se crea **subclaseando `MujocoEnv(gym.Env)`** y sobreescribiendo `step`, `reset_model`, `_get_obs` y `_get_reset_info`. El constructor recibe `model_path`, `frame_skip`, `observation_space` y args de render (`render_mode`, `width`, `height`, `camera_id`, `camera_name`, `default_camera_config`, `max_geom`, `visual_options`). Este es el mismo mecanismo que usa el tutorial oficial "load custom quadruped robot environments".
  Fuentes: https://raw.githubusercontent.com/Farama-Foundation/Gymnasium/main/gymnasium/envs/mujoco/mujoco_env.py , https://gymnasium.farama.org/tutorials/gymnasium_basics/load_quadruped_model/

- **Acción**: `_set_action_space()` construye un `spaces.Box` a partir de `model.actuator_ctrlrange` (límites por actuador). Para `cmd_vel`, la acción natural es `Box(2)` = `(v_x, omega_z)` y el `step` convierte a comandos de rueda; alternativamente la acción directa puede ser `(omega_left, omega_right)` si el MJCF usa actuadores de velocidad.
  Fuente: https://raw.githubusercontent.com/Farama-Foundation/Gymnasium/main/gymnasium/envs/mujoco/mujoco_env.py

- **Observación**: por convención los entornos MuJoCo de Gymnasium concatenan `qpos` y `qvel` (`state_vector()`); para un robot diferencial lo típico es exponer pose `(x, y, yaw)`, velocidades lineal/angular y/o sensores (odometría, encoders). Es decisión del env (`_get_obs`).
  Fuente: https://gymnasium.farama.org/environments/mujoco/ (sección "state spaces") y https://raw.githubusercontent.com/Farama-Foundation/Gymnasium/main/gymnasium/envs/mujoco/mujoco_env.py

- **Step/reset**: `step(action)` → `do_simulation(ctrl, n_frames)` escribe `data.ctrl` y llama `mujoco.mj_step(model, data, nstep=n_frames)` (`frame_skip` = pasos de física por paso de gym); `reset()` hace `mj_resetData` + `reset_model()` y devuelve `(obs, info)`. `dt = model.opt.timestep * frame_skip`. **El reward y el criterio de terminación/truncamiento son definidos por el env** (Gymnasium no impone reward estándar; los entornos incluidos lo definen por robot).
  Fuente: https://raw.githubusercontent.com/Farama-Foundation/Gymnasium/main/gymnasium/envs/mujoco/mujoco_env.py

- **Render**: `render()` delega en `MujocoRenderer` con modos `human`, `rgb_array`, `depth_array` y `rgbd_tuple` (RGBD añadido en v1.1.0). El backend OpenGL se elige con la variable de entorno **`MUJOCO_GL`**: `glfw` (default, ventana/GPU), `egl` (headless en GPU, Linux), `osmesa` (headless en CPU, Linux, deprecado). En el código fuente de los bindings, en **Windows solo se acepta `wgl`/GLFW**; `egl` y `osmesa` están disponibles únicamente en Linux.
  Fuentes: https://gymnasium.farama.org/environments/mujoco/ (sección "Rendering Backend") , https://github.com/google-deepmind/mujoco/blob/main/python/mujoco/rendering/classic/gl_context.py

### 4. Requisitos de instalación y rendimiento en Windows 11 / WSL2 (GLFW, EGL, headless para CI)

- **Instalación**: `pip install mujoco` y `pip install gymnasium` (o `pip install "gymnasium[mujoco]"`). Ambos publican **wheels precompilados para Windows x86_64** (`mujoco-*-win_amd64.whl` para cp310–cp314) y Linux; no se necesita compilar ni instalar el motor aparte.
  Fuentes: https://pypi.org/project/mujoco/ , https://github.com/google-deepmind/mujoco/issues/3011 (menciona `cp313-win_amd64` wheels en Windows 11)

- **Windows 11 (nativo)**: la física y el entrenamiento funcionan sin ningún contexto OpenGL (no hace falta render). El **render interactivo** usa GLFW (backend `wgl`). **No hay render headless en Windows**: ni `egl` ni `osmesa` están soportados por los bindings en Windows; `osmesa` además fue **removido del upstream de Mesa** (mesa 25.1, 2025) y el equipo de MuJoCo cerró la petición de soportarlo en Windows/macOS. Para captura de frames en Windows local hay que usar la ventana GLFW con GPU.
  Fuentes: https://github.com/google-deepmind/mujoco/issues/2164 , https://github.com/conda-forge/mesalib-feedstock/issues/109 , https://github.com/google-deepmind/mujoco/blob/main/python/mujoco/rendering/classic/gl_context.py

- **WSL2**: al correr en un kernel Linux, WSL2 soporta **EGL headless** (passthrough de GPU vía WSLg/D3D12) o `osmesa` para render CPU (deprecado). Es la vía más limpia para "Linux dentro de Windows" con paridad con el CI. Alternativa más simple: correr la física en Windows nativo y usar **Linux runners de GitHub Actions para los tests de render** (con `MUJOCO_GL=egl` en runners con GPU, o **saltando el render** en tests de física, que no necesitan OpenGL).
  Fuentes: https://github.com/google-deepmind/mujoco/issues/2164 , https://mujoco.readthedocs.io/en/stable/python.html (sección "Rendering")

- **Gotchas de plataforma**: en Python 3.14 no siempre hay wheels disponibles (issue #3011 reporta que 3.14 no tenía wheels para ciertas versiones y fallaba intentando build desde source); hubo un crash en bindings de Windows en 3.4.0 con modelos profundamente anidados (reportado en enero 2026, con workaround 3.3.7 o Python <=3.13). Recomendación práctica: **Python 3.11/3.12 (o 3.13)** para evitar fricción.
  Fuente: https://github.com/google-deepmind/mujoco/issues/3011

### 5. Benchmark mínimo: steps/s (FPS de simulación) en CPU para un escenario simple

- **Herramienta oficial**: `testspeed` (sample de MuJoCo) mide steps/s y realtime factor (RTF) en CPU; recomienda gobernador *performance* en Linux o plan de energía *High Performance* en Windows para mediciones estables. Los números de referencia reportados en fuentes primarias (mediciones publicadas por usuarios/equipo, no ejecutadas localmente):
  - **humanoid.xml (27 DoF, dt=5 ms)**: ~**29.722 steps/s** single-thread (~**148x realtime**) y ~**366.686 steps/s** en 16 threads, medido en AMD Ryzen 9 5950X con MuJoCo 2.3.6 (issue #986).
  - En un laptop (issue #897), humanoid.xml single-thread osciló entre **~66.000 y ~208.000 steps/s** según método de medición (~330x–1.040x realtime).
  - El paper de MPC de DeepMind (arxiv 2212.00541) afirma que un **humanoid de 27 DoF se simula ~4.000x más rápido que realtime en un solo thread de CPU**; el paper original de MuJoCo (IROS 2012) reportaba ~**151.000 evaluaciones de dinámica/s** para un modelo aislado de 34 DoF en CPUs de 2012.
  Fuentes: https://github.com/deepmind/mujoco/issues/986 , https://github.com/deepmind/mujoco/issues/897 , https://arxiv.org/abs/2212.00541 , https://www.roboti.us/lab/papers/TodorovIROS12.pdf , https://mujoco.readthedocs.io/en/stable/programming/samples.html (testspeed)

- **Estimación para el escenario de juguete** (robot diferencial ~4–10 DoF, pocas geometrías y contactos): es **notablemente más simple que el humanoid**, por lo que en un desktop moderno se espera del orden de **10^4–10^5 steps/s single-thread** (decenas de miles a >100.000 steps/s), es decir **cientos a >1000x realtime** a `dt=5 ms`. Ojo: el **throughput real de entrenamiento RL** por env es menor porque el bucle de Python (política + construcción de obs) domina una vez que el step es tan barato; típicamente **10^3–10^4 steps/s por env**, escalando casi linealmente con vectores de envs (`gymnasium.make_vec` / `AsyncVectorEnv`). El overhead de Python por step se reduce con `mj_step(nstep=...)`, `rollout.rollout` (rollouts por lotes multithread) y con el nuevo threadpool del motor (`mju_threadpool`, MuJoCo 3.10+).
  Fuentes: https://mujoco.readthedocs.io/en/stable/python.html (secciones `mj_step nstep`, `rollout`) , https://mujoco.readthedocs.io/en/stable/changelog.html (3.10.0: `mju_threadpool`)

### 6. Consideraciones de reproducibilidad y versionado

- **El comportamiento del simulador cambia ligeramente entre versiones de `mujoco`** (orden de operaciones de punto flotante); para reproducibilidad exacta hay que **fijar la versión de `mujoco` y la semilla**. La documentación de Gymnasium recomienda explícitamente fijar la versión del simulador si se necesita reproducibilidad exacta.
  Fuente: https://gymnasium.farama.org/environments/mujoco/ (sección "Exact reproducibility")

- **Cambios relevantes de 2026 en MuJoCo** para un escenario terrestre: 3.11.0 añadió `geom/surfacevel` (cintas transportadoras/pisos móviles, útil para terreno dinámico) y refactor de actuadores (preparación MIMO, `mjModel.actuator_ctrlspec`, breaking ABI); 3.10.0 añadió `mju_threadpool` (paralelización interna) y una API de logging; 3.9.0 rediseñó la semántica `margin`/`gap` (breaking para modelos con `gap>0`); 3.8.x añadió soporte Python 3.14 y `multiccd` por defecto. Si se adopta la última versión, conviene fijar una minor y revisar el changelog antes de actualizar.
  Fuente: https://mujoco.readthedocs.io/en/stable/changelog.html

## Recomendación

Para el escenario de juguete "robot diferencial terrestre controlado por `cmd_vel`" (2026):

1. **Pila**: Python 3.11/3.12, `mujoco==3.11.x` y `gymnasium==1.3.x` (`pip install mujoco gymnasium`). Son compatibles entre sí (entornos MuJoCo v5 de Gymnasium requieren `mujoco>=2.3.3` y están alineados con la línea 3.x actual).
2. **Modelo**: crear un **MJCF propio estilo TurtleBot** (chasis con `free joint`, dos ruedas motrices con `hinge` joints y actuadores `velocity` —o `motor` con damping—, y una rueda loca/caster). Este es el modelo más apto para `cmd_vel`: mapear `(v_x, ω_z) → (ω_L, ω_R)` con la cinemática diferencial `ω_L=(v−ω·d/2)/r`, `ω_R=(v+ω·d/2)/r`. Referencias: `model/car/car.xml` del repo de MuJoCo y el patrón del discussion #2392. Si más adelante se quiere un diferencial real con brazo, usar **TIAGo de Menagerie** (`scene_velocity.xml`). **No usar `mj_envs`** (muerto, absorbido por RoboHive, y sin robot diferencial).
3. **Env Gym**: subclase de `gymnasium.envs.mujoco.MujocoEnv`. Acción `Box(2)` con `(v_x, ω_z)` (o `(ω_L, ω_R)`), observación de estado (pose + velocidades + opcional odometría/encoders), reward y terminación definidos por nosotros; `frame_skip` para fijar `dt` (~10–50 ms por paso de control). Registrar con `gym.register` o instanciar directamente.
4. **Windows 11**: usar **Windows nativo para física/entrenamiento** (wheels precompilados, sin OpenGL necesario si no se renderiza) y el viewer GLFW solo cuando haya GPU/ventana. Para **CI headless**: correr tests de física en cualquier runner sin render, y los tests de render en **Linux runner** con `MUJOCO_GL=egl` (GPU) o `osmesa` (CPU, deprecado). En WSL2, EGL funciona con passthrough de GPU. Evitar Python 3.14 (wheels/estabilidad) hasta que se estabilice.
5. **Rendimiento esperado**: del orden de **10^4–10^5 steps/s** en CPU single-thread para el robot simple (cientos a >1000x realtime), y **~10^3–10^4 steps/s por env** en entrenamiento RL real; vectorizar con `gymnasium.make_vec(num_envs=N)` y, si hace falta, `mujoco.rollout` o `mju_threadpool` para paralelizar. Fijar la versión de `mujoco` + seeds si se quiere reproducibilidad exacta.
6. **No instalar nada ni correr código local en esta fase de research**: estos hallazgos se basan en fuentes primarias (docs y repos oficiales); los números de FPS provienen de mediciones publicadas por el equipo/usuarios de MuJoCo, no de una ejecución local.

## Fuentes

- https://mujoco.readthedocs.io/en/stable/changelog.html — changelog de MuJoCo (3.11.0, 3.10.0, 3.9.0, 3.8.x, etc.).
- https://github.com/google-deepmind/mujoco/releases — releases del motor.
- https://pypi.org/project/mujoco/ — paquete `mujoco` (bindings canónicos, wheels, Apache-2.0, Python >=3.10).
- https://mujoco.readthedocs.io/en/stable/python.html — bindings de Python: instalación, viewer, `MjModel/MjData`, `mj_step(nstep)`, `rollout`, rendering/GLContext, migración desde `mujoco-py`.
- https://gymnasium.farama.org/gymnasium_release_notes/index.html — release notes (v1.3.0, v1.2.x: migración de envs v2/v3 a gymnasium-robotics, Python 3.13, RGBD).
- https://github.com/Farama-Foundation/Gymnasium/releases/tag/v1.2.0 — release v1.2.0 de Gymnasium.
- https://gymnasium.farama.org/environments/mujoco/ — doc de entornos MuJoCo: versiones v2–v5, state space (qpos+qvel), rendering backend (`MUJOCO_GL`), reproducibilidad.
- https://raw.githubusercontent.com/Farama-Foundation/Gymnasium/main/gymnasium/envs/mujoco/mujoco_env.py — fuente de la clase base `MujocoEnv`.
- https://gymnasium.farama.org/tutorials/gymnasium_basics/load_quadruped_model/ — tutorial oficial para cargar un modelo propio en el marco MuJoCo de Gymnasium.
- https://github.com/google-deepmind/mujoco_menagerie — repositorio de modelos curados por Google DeepMind.
- https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/main/pal_tiago/README.md — TIAGo (base diferencial, actuadores de fuerza/velocidad/posición, `scene_velocity.xml`).
- https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/main/toddlerbot_2xc/README.md — ToddlerBot 2XC (requiere MuJoCo >=2.3.3).
- https://raw.githubusercontent.com/google-deepmind/mujoco_menagerie/main/robot_soccer_kit/README.md — robot soccer kit omnidireccional.
- https://github.com/google-deepmind/mj_envs — (404) `google-deepmind/mj_envs` ya no existe.
- https://github.com/vikashplus/robohive — RoboHive, sucesor del framework `mj_envs`.
- https://github.com/google-deepmind/mujoco/discussions/2392 — discusión oficial sobre robot diferencial 2-ruedas (motors, damping, tendones, caster).
- https://github.com/google-deepmind/mujoco/tree/main/model — modelos de referencia del repo (incluye `car/`).
- https://github.com/google-deepmind/mujoco/blob/main/python/mujoco/rendering/classic/gl_context.py — selección de backend GL por plataforma (wgl/GLFW en Windows; egl/osmesa solo Linux).
- https://github.com/google-deepmind/mujoco/issues/2164 — `MUJOCO_GL=osmesa` no soportado en Windows/macOS; osmesa removido del upstream de Mesa.
- https://github.com/conda-forge/mesalib-feedstock/issues/109 — remoción de OSMesa de Mesa 25.1.
- https://github.com/google-deepmind/mujoco/issues/3011 — wheels y crash en Windows (3.4.0, Python 3.14).
- https://github.com/deepmind/mujoco/issues/986 — benchmark `testspeed` humanoid en Ryzen 9 5950X (~29.7k steps/s single-thread, ~366k en 16 threads).
- https://github.com/deepmind/mujoco/issues/897 — comparativa de mediciones humanoid (~66k–208k steps/s) en C++ vs Python.
- https://arxiv.org/abs/2212.00541 — paper de MPC de DeepMind: humanoid 27-DoF ~4.000x más rápido que realtime en un thread.
- https://www.roboti.us/lab/papers/TodorovIROS12.pdf — paper original de MuJoCo (IROS 2012): ~151.000 evaluaciones de dinámica/s.
- https://mujoco.readthedocs.io/en/stable/programming/samples.html — sample `testspeed` (medición de steps/s, RTF, consejos de governor/plan de energía).
- https://github.com/ros-controls/mujoco_ros2_control — hardware interface de MuJoCo para ROS 2 (actuadores de velocidad/motor en ruedas).
