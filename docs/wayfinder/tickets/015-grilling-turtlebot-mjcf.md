## Question

¿Qué modelo MJCF utilizar (assets builtin de `mujoco` como `car.xml` / modelado base diferencial simplificado o un MJCF custom de TurtleBot en `plataforma/sim/assets/`) y cómo formular la cinemática diferencial `(v_x, omega) → (omega_l, omega_r)` respetando la geometría del robot y los límites del `CmdVel`?

## Answer

- **Modelo MJCF**: Se define un MJCF minimalista en línea o string XML (`TURTLEBOT_MJCF`) con un cuerpo rodante cilíndrico libre (base móvil) y actuadores de velocidad en las articulaciones de rueda izquierda y derecha, evitando dependencia de archivos externos frágiles.
- **Cinemática Diferencial**:
  - Ancho de vía $L = 0.23\text{m}$, Radio de rueda $R = 0.033\text{m}$.
  - $\omega_L = \frac{v_x - \frac{\omega L}{2}}{R}$, $\omega_R = \frac{v_x + \frac{\omega L}{2}}{R}$.
  - Clamping estricto de velocidades acorde a los límites de `CmdVel`.
