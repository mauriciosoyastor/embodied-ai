# GUIA — Docker (Fase 0, mini-hito 2)

Objetivo: empaquetar tu script en un contenedor y correrlo. Docker es el origen del aislamiento que después será la "Safety Envelope" de la IA corpórea.

## Qué aprender (mínimo viable)

1. **Qué es un contenedor**: una "caja" con tu programa y todo lo que necesita, que corre igual en cualquier máquina. No es una máquina virtual (comparte el sistema operativo).
2. **Imagen vs contenedor**: la imagen es la *receta*; el contenedor es la *caja que corre*.
3. **Dockerfile**: el archivo de texto que describe la receta.
   - `FROM` — imagen base (ej. python).
   - `WORKDIR` — carpeta de trabajo.
   - `COPY` — copiar archivos del proyecto a la imagen.
   - `CMD` — qué comando correr al arrancar.
4. **Comandos**:
   - `docker build -t mi-imagen .` — construir la imagen.
   - `docker run mi-imagen` — correr el contenedor.
   - `docker ps` / `docker images` — ver qué está corriendo/guardado.

## El ejemplo de este repo

El `Dockerfile` empaca `contar_palabras.py` y `main.py`, y al correrlo cuenta las palabras de `ejemplo.txt`.

```
docker build -t fase-0-ejemplo .
docker run --rm fase-0-ejemplo
```

## Recursos externos gratis

- Docker Docs: "Get started" (tutorial oficial, en inglés; la interfaz de Docker Desktop está en español).
- FreeCodeCamp: "Docker Tutorial for Beginners" (YouTube, subtítulos en español).
- Play with Docker (play-with-docker.com): practicar sin instalar nada.

## Checklist del mini-hito 2

- [ ] Escribo un Dockerfile propio para un script mío (no solo el ejemplo).
- [ ] `docker build` termina sin errores.
- [ ] `docker run` muestra la salida de mi script.
- [ ] Puedo explicar la diferencia entre imagen y contenedor.
