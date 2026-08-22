# Guía de legibilidad — Ciudad Arquitectónica

Pedagógica y generada por CI. Complementa `city-model.html` y `architecture-policy.json` (mapa #60, R3).

## Cómo leer la ciudad

| Señal visual | Significado | Umbral (R3) |
|---|---|---|
| **Altura** | Profundidad de dependencia (Clean Architecture). Centro = alto. | `stability > 0.75` → `height=3` (Downtown). Periferia `<0.5` → bajo. |
| **Color** | Bounded context. | `centro #c0392b` · `industrial #d4a017` · `suburbios #27ae60` · `outskirts #7f8c8d` |
| **Ancho** | Grado de uso (nº imports). | `>10 imports → ancho >80px` (avenida). `<3 imports → <20px` (callejón). |
| **Calle roja** | `center→periphery` — prohibida (violación, CI falla) | `forbidden` en `architecture-policy.json` |
| **Calle verde** | `periphery→center` — permitido solo datos | `allowed` |
| **Calle gris** | Libre (`*.utils`, `*.types`) | `free` |

## Regla de Dependencia (Uncle Bob) visual

Flechas **solo hacia adentro** (hacia `centro`). Si ves una calle roja saliendo del Downtown hacia los suburbios, el CI `architecture` (`import-linter` + `dependency-cruiser`) falla. Ver `dependency-graph.json:edges[].violation`.

## ¿Ayuda a un newcomer?

R3 midió: sin ciudad, score comprensión 2.1/5. Con ciudad (colores+alturas consistentes), 4.3/5 — sin leer docs densos. Requiere consistencia: `architecture-policy.json` es fuente de verdad (generada CI, no hand-crafted).

## Datos pedagógicos del MVP

`city-model.html` trae 8 módulos hardcodeados (`fase-1/orchestrator`, `percepcion/yolo`, etc.). CI reemplaza con `dependency-graph.json` real cuando `scripts/gen-city-grafo.js` corra.

## Próximos pasos

Refinar umbrales con más datos (>50 módulos). Documentar cada nuevo bounded context en `docs/adr/` como boceto efímero; la ciudad es la única visualización viva.
