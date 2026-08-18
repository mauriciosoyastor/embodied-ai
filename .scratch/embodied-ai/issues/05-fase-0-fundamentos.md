# 05 — Fase 0: fundamentos (qué aprender, hito)

Type: grilling
Status: resolved
Blocked by: 01

## Question

¿Qué contenido exacto, en qué orden, y con qué **hito** (proyecto mínimo que corre) cierra la Fase 0 para un principiante total?

Alcance decidido: Python básico + git/GitHub + Linux básico + Docker (nivel "media"). Falta afinar:
- Subtemas mínimos de Python (sintaxis, funciones, clases, paquetes, virtualenv).
- Subtemas mínimos de Linux y Docker (terminal, archivos, permisos, contenedores simples).
- Qué hito concreto (un script + un contenedor + un repo en GitHub) prueba que la fase está completa.
- En qué orden se aprenden y cuántas semanas aproximadas a 5-10 h/sem.
- Cómo juega la decisión del entorno Linux (ticket 01) aquí.

Se resuelve con grilling y domain-modeling. El resultado alimenta el roadmap final.

## Answer

Fase 0 resuelta:

- **Hito de cierre**: **tres mini-hitos** separados — 1) script Python que corre; 2) contenedor Docker que se levanta; 3) repo en GitHub. Refuerzo positivo frecuente y aíslan dónde se traba.
- **Orden de temas**: Python → git → Linux → Docker (primero el idioma, luego versionado, luego el SO, luego contenedores).
- **Modo de aprendizaje**: mezcla — mini-explicaciones y ejercicios guiados en el repo, complementadas con recursos gratis externos (freeCodeCamp, docs oficiales).
- **Entorno**: WSL2 (Ubuntu) según wayfinder 01; Python se aprende primero en Windows y se sigue en WSL2.