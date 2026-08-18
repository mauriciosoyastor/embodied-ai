# 07 — Fase 2: percepción visual (hitos)

Type: grilling
Status: open
Blocked by: (ninguno)

## Question

¿Qué proyectos mínimos (hitos) componen la Fase 2 — percepción visual de baja latencia — para un principiante?

Contexto de la guía: WebRTC vs RTSP+WebSocket, Leaky Queue (N=1), tracking con KCF, MOG2 para validar movimiento, CLAHE para visión nocturna, inferencia con modelos YOLO. Sin hardware comprado todavía (una webcam alcanza). Falta afinar:
- Hitos escalonados (p. ej. 1: leer frames de webcam y dibujar detecciones; 2: pipeline de baja latencia con leaky queue; 3: MOG2/CLAHE; 4: tracking).
- Cuánto es necesario hoy vs. depende de comprar cámaras IP/Jetson.
- Qué bibliotecas concretas (OpenCV, etc.) y su curva para un principiante.
- Cómo se verifica "corre y se entiende" para cada hito.

Se resuelve con grilling y domain-modeling. El resultado alimenta el roadmap final.
