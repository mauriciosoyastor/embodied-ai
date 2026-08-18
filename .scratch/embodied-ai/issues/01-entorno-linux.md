# 01 — Elegir entorno Linux de trabajo

Type: grilling
Status: resolved
Blocked by: (ninguno)

## Question

El aprendiz está en Windows, pero ROS 2 y gran parte de la pila (Linux, Docker, Jetson) corren en Linux. ¿Cómo se trabaja Linux a partir de la Fase 0?

- **WSL2**: Ubuntu dentro de Windows; rápido y gratis, pero ROS 2 con GUI/serial puede tener fricción.
- **Máquina virtual** (VMware/VirtualBox): aislado, algo más pesado.
- **Dual boot**: partición dedicada; lo más realista pero requiere reiniciar.
- **Otro**: combinaciones (p. ej. WSL2 ahora, VM para Fase 3).

Se resuelve con grilling: cuál elegir, con qué criterio, y qué implica para la Fase 0 (Linux básico) y para las fases 3-4 (ROS 2 / PX4 SITL).

Resuelto, bloquea el ticket 05 (Fase 0: fundamentos).

## Answer

**WSL2 (Ubuntu)** — elegido como entorno Linux principal de aprendizaje.

- Máquina: Windows 11 Home, 32 GB RAM, ~302 GB libres. Sobra para WSL2.
- Es la única PC de uso diario (trabajo/estudio) → WSL2 evita reinicios y particiones (descartado dual boot).
- Aplica a Fase 0-2 (Python, Linux básico, Docker, Ollama). WSL2 da Ubuntu real + Docker + ROS 2 sin reiniciar, con la misma terminal que un Jetson.
- **Nota de reevaluación**: antes de Fase 3 (ROS 2 + Gazebo GUI + posible serial/USB para hardware), reevaluar si hace falta Linux nativo (VM/dual boot). No bloquea el progreso de Fase 0-2.
