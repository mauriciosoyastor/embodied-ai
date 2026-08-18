# Spec — Roadmap de aprendizaje ejecutable en Embodied AI / AIoT

## Problem Statement

El aprendiz parte de **cero** en base técnica (sin Python, sin Linux, sin robótica, sin ML) y quiere dominar Embodied AI / AIoT siguiendo la *Guía Maestra* del proyecto. La guía asume un perfil de ingeniero senior y no incluye fundamentos ni una secuencia ejecutable, así que no hay un camino claro de "no sé nada" a "puedo construir un agente corpóreo". Además, aún no hay hardware comprado y la dedicación es de 5-10 h/semana, por lo que el camino debe ser viable con recursos modestos y verificable fase a fase.

## Solution

Un **roadmap de aprendizaje ejecutable** en español: un plan de qué construir y en qué orden, organizado en fases (Fase 0 de fundamentos + Fase 1 a 4 de la guía), donde cada fase cierra con un **hito** — un proyecto mínimo que corre y el aprendiz lo entiende. El plan se decide primero (esto es un mapa de decisiones); la ejecución del código queda fuera de alcance de este esfuerzo.

## User Stories

1. Como principiante total, quiero una Fase 0 de fundamentos (Python + git/GitHub + Linux básico + Docker), para llegar a la Fase 1 sin huecos.
2. Como principiante total, quiero un hito concreto al cierre de cada fase, para saber objetivamente que avancé.
3. Como aprendiz con 5-10 h/semana, quiero fases de tamaño realista, para no abandonar por sobrecarga.
4. Como aprendiz sin hardware, quiero aprender orquestación y percepción en software (webcam, LLM local, hardware mockeado), para no depender de comprar equipos para empezar.
5. Como aprendiz sin hardware, quiero simulación ligera (Gazebo / PX4 SITL) para las fases de robótica y vuelo, para practicar sin hardware físico.
6. Como aprendiz, quiero mantener el orden de la guía (orquestador → percepción → terrestre → aéreo), para que cada fase resuelva las dependencias de la siguiente.
7. Como aprendiz, quiero aprender Ollama local primero, para dominar las decisiones de optimización (salida con esquema estricto, presupuesto de VRAM) sin depender de la nube.
8. Como aprendiz, quiero que el roadmap mantenga las versiones de la pila actualizadas (Ollama, Pydantic AI, ROS 2, PX4), para no aprender sobre herramientas obsoletas.
9. Como aprendiz, quiero el contenido del roadmap en español, para aprender en mi idioma.
10. Como aprendiz, quiero un criterio claro de "hito completado" por fase, para saber cuándo pasar a la siguiente.
11. Como aprendiz, quiero decidir mi entorno Linux (WSL2 / VM / dual boot) como una decisión del plan, para no bloquear la Fase 0.
12. Como aprendiz, quiero que el roadmap diferencie lo necesario de lo opcional por fase, para priorizar mi tiempo.

## Implementation Decisions

- **Destino**: roadmap de aprendizaje ejecutable; el mapa decide, no ejecuta.
- **Fase 0 — Fundamentos (nivel "media")**: Python básico + git/GitHub + Linux básico + Docker. Previa a la guía.
- **Orden de fases**: Fase 0 → Fase 1 (orquestador cognitivo) → Fase 2 (percepción visual) → Fase 3 (robótica terrestre ROS 2) → Fase 4 (control aéreo PX4/MAVSDK).
- **Hito** = proyecto mínimo que corre y se entiende; es el criterio de finalización de cada fase.
- **Entorno Linux**: decisión abierta (WSL2 / VM / dual boot); se resuelve antes de definir la Fase 0.
- **Backend de razonamiento**: Ollama local primero (no nube); Pydantic AI como framework; salida con esquema estricto (grammar-constrained decoding / Pydantic).
- **Simulación**: ligera, solo como cierre de Fase 3 y Fase 4 (Gazebo / PX4 SITL), no como foco del roadmap.
- **Research por fase**: tickets de research para refrescar versiones actuales de Ollama+Pydantic AI (Fase 1), ROS 2+Gazebo (Fase 3) y PX4 SITL+MAVSDK (Fase 4) antes de afinar los hitos de esas fases.
- **Idioma del entregable**: español.
- **Dedicación**: 5-10 h/semana; la granularidad de los hitos se calibra a eso.
- **Dónde vive el plan**: este repo local markdown (`.scratch/embodied-ai/`); la guía maestra en la raíz de la carpeta del proyecto es la fuente.

## Testing Decisions

- **Qué hace a un buen test del roadmap**: cada fase prueba su validez de forma externa — el hito de cierre debe *correr* (produce salida/acción real) y el aprendiz debe *entenderlo* (puede explicarlo). No se testea implementación interna de la fase.
- **Módulos probados**: Fase 0 (un script Python + un contenedor Docker + un repo en GitHub); Fase 1 (orquestador local con LLM + salida con esquema estricto + máquina de estados con hardware mockeado); Fase 2 (pipeline de webcam con detección y baja latencia); Fase 3 (nodo de seguridad en Gazebo que intercepta comandos fuera de la envolvente); Fase 4 (drone simulado con offboard mode vía MAVSDK y heartbeat/failsafe).
- **Seam de verificación**: el hito de cada fase es el único punto donde se juzga el avance — un solo punto de control por fase, en la salida (corre + se entiende), no en la implementación.

## Out of Scope

- **Ejecutar/implementar el código de las fases**: este esfuerzo produce el plan y las decisiones; construir el roadmap lo ejecuta otro esfuerzo cuando el camino esté claro.
- **Comprar hardware** (Jetson, dron, robot terrestre, cámaras IP): se difiere hasta que el aprendizaje lo justifique.
- **Contenido en inglés**: el entregable es en español.
- **Optimización avanzada de producción** (latencia glass-to-glass < 200ms, tuning de DeepStream): se menciona como contexto de la guía pero no es un hito de aprendizaje inicial.

## Further Notes

- La *Guía Maestra* (archivo en la raíz de la carpeta del proyecto) es la fuente del contenido técnico; este roadmap la traduce a una secuencia ejecutable para un principiante.
- Los términos técnicos (orquestador cognitivo, MOG2, CLAHE, hysteresis, safety envelope, etc.) están definidos en `CONTEXT.md`.
- Los hallazgos de los tickets de research pueden ajustar decisiones de pila (versionar, elegir modelos) sin cambiar el destino del roadmap.