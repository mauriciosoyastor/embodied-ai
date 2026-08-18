# 09 — Fase 4: control aéreo (hitos)

Type: grilling
Status: open
Blocked by: 04

## Question

¿Qué proyectos mínimos (hitos) componen la Fase 4 — control aéreo y actuadores autónomos — para un principiante?

Contexto de la guía: offboard mode vía MAVSDK, protocolo heartbeat (proof of life) estricto, failsafe de aterrizaje inmediato, stick override y deadman's switch. Sin hardware: se aprende con PX4 SITL. Falta afinar:
- Hitos escalonados (p. ej. 1: PX4 SITL corriendo + dron despega/aterriza; 2: control offboard vía MAVSDK desde Python; 3: heartbeat + failsafe que detiene la actuación si el latido se corta).
- Qué es realista de la lógica de seguridad (failsafe, heartbeat) en simulación.
- Usar los findings del ticket 04 (versiones actuales, instalación en el entorno elegido).
- Cómo se verifica "corre y se entiende" para cada hito.

Se resuelve con grilling y domain-modeling. El resultado alimenta el roadmap final.
