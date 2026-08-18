# GUIA — Linux (Fase 0, parte 3)

Objetivo: moverte por la terminal de Linux con confianza. En este proyecto, Linux se usa a través de **WSL2** (Ubuntu dentro de Windows), que ya decidimos como entorno.

## Qué aprender (mínimo viable)

1. **Navegar**: `pwd` (dónde estás), `ls` (listar), `cd` (cambiar de carpeta), `mkdir` (crear carpeta).
2. **Archivos**: `touch`, `rm`, `mv`, `cp`, `cat` (ver archivos).
3. **Permisos y usuarios**: `sudo`, `chmod`, `chown` (lo mínimo para entender "permiso denegado").
4. **Paquetes**: `apt update`, `apt install` (instalar programas).
5. **Procesos**: `ps`, `kill`, y entender qué es un proceso.
6. **Estructura del sistema**: `/home`, `/etc`, `/usr`, `/var` — por qué Linux no tiene "c:".
7. **Pipes y redirección**: `|`, `>`, `>>` (la base del "pipeline" de la Fase 2).

## Cómo arrancar WSL2 (Windows 11)

En PowerShell (como administrador):
```
wsl --install -d Ubuntu
```
Después abrí "Ubuntu" desde el menú inicio. Tu carpeta de Windows está en `/mnt/c/`.

Nota: esta guía es la parte más importante para el resto del roadmap — ROS 2, PX4 y el Jetson son Linux. Tomate tu tiempo.

## Recursos externos gratis

- The Linux Command Line (linuxcommand.org): libro gratuito en inglés.
- FreeCodeCamp: "Linux Command Line" (YouTube, subtítulos en español).
- Ubuntu Docs: "Command line for beginners".

## Checklist del mini-hito (integra con mini-hito 3)

- [ ] Instalé WSL2 con Ubuntu y abro la terminal.
- [ ] Navego entre carpetas y creo un archivo desde la terminal.
- [ ] Instalo un paquete con `apt install`.
- [ ] Uso `|` para conectar dos comandos (ej. `ls | grep .py`).
