# 08 — Fase 3: robótica terrestre ROS 2 (hitos)

Type: grilling
Status: open
Blocked by: 03

## Question

¿Qué proyectos mínimos (hitos) componen la Fase 3 — robótica terrestre y capas de seguridad en ROS 2 — para un principiante?

Contexto de la guía: contrato de capa ejecutiva con validadores pre-ejecución, interceptor de seguridad (geofencing dinámico, proximidad LIDAR/ultrasonido), nodo guardián ROSClaw en Gazebo que intercepta comandos que violan la envolvente de seguridad. Sin hardware físico: se aprende en simulación. Falta afinar:
- Hitos escalonados (p. ej. 1: hola mundo ROS 2 + publisher/subscriber; 2: robot TurtleBot en Gazebo con teleop; 3: nodo guardián que valida/intercepta comandos con contrato Pydantic).
- Qué de la envolvente de seguridad (safety envelope) es realista de aprender en simulación.
- Usar los findings del ticket 03 (distro actual, instalación en el entorno Linux elegido).
- Cómo se verifica "corre y se entiende" para cada hito.

Se resuelve con grilling y domain-modeling. El resultado alimenta el roadmap final.
