# Mapa — Roadmap de aprendizaje Embodied AI / AIoT

## Destination

Un roadmap de aprendizaje **ejecutable** — un plan, en español, de qué construir y en qué orden para aprender Embodied AI/AIoT desde cero, donde cada fase cierra con un **hito** (proyecto mínimo que corre y se entiende). El mapa **decide**, no ejecuta: cuando el camino esté claro, el roadmap se entrega como plan para construir.

## Notes

- **Dominio**: Embodied AI / AIoT (percepción visual, orquestación cognitiva, robótica terrestre, control aéreo).
- **Punto de partida**: el aprendiz parte de cero (sin Python, sin Linux, sin robótica, sin ML).
- **Dedicación**: 5-10 h/semana.
- **Fuente**: `Guía Maestra de Aprendizaje en Inteligencia Artificial Corpórea (Embodied AI) e AIoT.md` en la raíz de la carpeta.
- **Idioma**: todos los entregables del roadmap van en español.
- **Skills a consultar por sesión**: `/grilling` y `/domain-modeling` para resolver tickets HITL; `/research` para los AFK.
- **Orden de fases**: Fase 0 (fundamentos) → Fase 1 (orquestador) → Fase 2 (percepción) → Fase 3 (terrestre) → Fase 4 (aéreo). Cada fase usa simulación ligera (Gazebo / PX4 SITL) como cierre, no como foco.
- **Stack inicial fijado**: Ollama local primero (no nube); Pydantic AI; los datos de versiones actuales se refrescan vía tickets de research.

## Decisions so far

<!-- índice — una línea por ticket cerrado -->

- [01 — Elegir entorno Linux de trabajo](issues/01-entorno-linux.md) — **WSL2 (Ubuntu)** como entorno principal de aprendizaje (Fase 0-2); reevaluar Linux nativo antes de Fase 3. Descartado dual boot por ser PC de uso diario.
- [05 — Fase 0: fundamentos (qué aprender, hito)](issues/05-fase-0-fundamentos.md) — **Tres mini-hitos** (script Python / contenedor Docker / repo GitHub), orden **Python → git → Linux → Docker**, modo mixto (guías en repo + recursos externos).

## Not yet specified

- **Hardware a comprar**: cuándo y qué comprar (Jetson, dron, robot terrestre, cámaras) una vez que las fases de aprendizaje lo justifiquen. Depende del avance de las fases; no se puede afinar hoy.
- **Granularidad fina de los proyectos por fase**: qué scripts/modelos concretos forman cada hito. Se define dentro de los tickets grilling de cada fase.
- **Criterio de "se entiende"**: cómo se confirma que el aprendiz entiende el hito más allá de que corra. (Decidido: el hito es "corre y se entiende" — la verificación concreta queda por definir por fase.)

## Out of scope

- **Ejecutar/implementar el código de las fases**: este mapa produce decisiones y el plan, no la construcción. Cuando el camino esté claro, se entrega y otro esfuerzo ejecuta.
- **Comprar hardware ahora**: sin decisión de hardware hasta que el aprendizaje lo amerite (ver Not yet specified).
