#!/usr/bin/env python3
"""Descarga modelos YOLO11n ONNX y MediaPipe Hand Landmarker a backend/models/.

Idempotente: si el archivo ya existe y (opcionalmente) su hash coincide,
se omite la descarga salvo que se pase --force.
No commitear pesos ÔÇö ver .gitignore.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Modelos oficiales (Ultralytics + Google AI Edge + MiDaS)
# ---------------------------------------------------------------------------
YOLO_URL = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx"
POSE_URL = (
    "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n-pose.onnx"
)
HAND_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
DEPTH_URL = "https://huggingface.co/Heliosoph/midas-small-onnx/resolve/main/midas_v21_small_256.onnx"
YOLO_WORLD_URL = (
    "https://huggingface.co/Instemic/yolo-world-onnx/resolve/main/yolov8s-worldv2.onnx"
)
# Fallback PT para export local si HF no disponible (Ultralytics assets v8.2.0 24.7MB)
YOLO_WORLD_PT_URL = (
    "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s-worldv2.pt"
)
# Visi├│n viva 036 ÔÇö frontend/public/models/ (BlazeFace + mobilefacenet)
BLAZE_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
)

# Deuda t├®cnica (Opci├│n C, 2026-08-23): no existe fuente p├║blica verificada de
# mobilefacenet.onnx 128-d (onnx/models 404, HF gated/pytorch-only).
# El fallback stubEmbedding cubre tests/CI/demo; la fuente definitiva
# (insightface w600k_mbf.onnx es 512-d y exigir├¡a migrar el contrato
# embedding[128] del mapa 004) se decide en una sesi├│n enfocada de re-id browser.
MOBILEFACENET_URL = ""

# SHA256 esperados (None = solo loguea el hash, no falla si difiere).
# Para fijar verificaci├│n estricta, reemplazar None por el hexdigest real
# y el script fallar├í si el hash descargado no coincide.
EXPECTED_SHA256: dict[str, str | None] = {
    "yolo11n.onnx": None,
    "yolo11n-pose.onnx": None,
    "midas_small_256.onnx": None,
    "hand_landmarker.task": None,
    "yolo-world-s.onnx": "381ced485b23ed8f06de3e82bb2745e1420c181c64f0a176784c34a959d550a1",  # noqa: E501
}

MODELS: dict[str, dict[str, str]] = {
    "yolo11n.onnx": {"url": YOLO_URL},
    "yolo11n-pose.onnx": {"url": POSE_URL},
    "midas_small_256.onnx": {"url": DEPTH_URL},
    "hand_landmarker.task": {"url": HAND_URL},
    "yolo-world-s.onnx": {"url": YOLO_WORLD_URL},
}

# Modelos frontend visi├│n viva (036) ÔÇö destino frontend/public/models/
FRONTEND_MODELS_DIR = (
    pathlib.Path(__file__).parents[1] / "frontend" / "public" / "models"
)
FRONTEND_MODELS: dict[str, str] = {
    "blaze_face_short_range.tflite": BLAZE_URL,
    "mobilefacenet.onnx": MOBILEFACENET_URL,
}

DEFAULT_MODELS_DIR = pathlib.Path(__file__).parent / "models"
CHUNK_SIZE = 1024 * 1024  # 1 MiB


def sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _verify_hash(path: pathlib.Path, expected: str | None) -> bool:
    """Retorna True si no hay expected o si el hash coincide; loguea en ambos casos."""
    actual = sha256_of(path)
    name = path.name
    if expected is None:
        print(f"  SHA256({name}) = {actual} (sin hash esperado ÔÇö solo informativo)")
        return True
    if actual.lower() == expected.lower():
        print(f"  SHA256 OK {name}: {actual}")
        return True
    print(
        f"  SHA256 MISMATCH {name}: esperado {expected}, obtenido {actual}",
        file=sys.stderr,
    )
    return False


def download_one(
    filename: str,
    url: str,
    dest: pathlib.Path,
    force: bool,
    expected_sha256: str | None,
) -> bool:
    """Descarga si no existe o force=True. Retorna True si ya v├ílido/descargado."""
    if dest.exists() and not force:
        size = dest.stat().st_size
        if size == 0:
            print(f"[WARN] {filename} existe pero est├í vac├¡o ÔÇö re-descargando")
        else:
            print(f"[SKIP] {filename} ya existe ({size} bytes) en {dest}")
            if expected_sha256 is not None:
                if not _verify_hash(dest, expected_sha256):
                    print(f"[WARN] hash no coincide, re-descargando {filename}")
                else:
                    return True
            else:
                # sin hash esperado, verificamos que no est├® corrupto informativamente
                _verify_hash(dest, None)
                return True
            # si hash mismatch arriba, cae a descarga

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    print(f"[GET]  {filename} <- {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "embodied-ai/1.0"})
        with urllib.request.urlopen(req) as resp, tmp.open("wb") as out:
            total = resp.headers.get("Content-Length")
            if total is not None:
                print(f"  tama├▒o remoto: {int(total):,} bytes")
            while True:
                chunk = resp.read(CHUNK_SIZE)
                if not chunk:
                    break
                out.write(chunk)
    except (urllib.error.URLError, OSError) as exc:
        print(f"[ERROR] fallo al descargar {filename}: {exc}", file=sys.stderr)
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        return False

    # validaci├│n post-descarga
    if tmp.stat().st_size == 0:
        print(f"[ERROR] archivo descargado vac├¡o: {filename}", file=sys.stderr)
        tmp.unlink(missing_ok=True)
        return False

    if not _verify_hash(tmp, expected_sha256):
        # si hay hash esperado y no coincide, borrar y fallar
        if expected_sha256 is not None:
            tmp.unlink(missing_ok=True)
            return False

    tmp.replace(dest)
    print(f"[OK]   {filename} -> {dest} ({dest.stat().st_size:,} bytes)")
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Descarga modelos webcam (YOLO + MediaPipe + visi├│n viva)"
    )
    p.add_argument(
        "--models-dir",
        type=pathlib.Path,
        default=DEFAULT_MODELS_DIR,
        help=f"directorio destino (default: {DEFAULT_MODELS_DIR})",
    )
    p.add_argument("--force", action="store_true", help="re-descarga aunque ya exista")
    p.add_argument("--yolo-url", default=YOLO_URL, help="override URL yolo11n.onnx")
    p.add_argument(
        "--pose-url", default=POSE_URL, help="override URL yolo11n-pose.onnx"
    )
    p.add_argument(
        "--depth-url", default=DEPTH_URL, help="override URL midas_small_256.onnx"
    )
    p.add_argument(
        "--hand-url", default=HAND_URL, help="override URL hand_landmarker.task"
    )
    p.add_argument(
        "--blaze-url", default=BLAZE_URL, help="override URL blaze_face_short_range"
    )
    p.add_argument(
        "--face-url", default=MOBILEFACENET_URL, help="override URL mobilefacenet.onnx"
    )
    p.add_argument(
        "--world-url",
        default=YOLO_WORLD_URL,
        help="override URL yolo-world-s.onnx (Instemic 48.8MB)",
    )
    p.add_argument(
        "--skip-frontend",
        action="store_true",
        help="no descargar modelos frontend (blaze/mobilefacenet)",
    )
    p.add_argument(
        "--verify-hash",
        action="store_true",
        help="falla si el archivo existente no coincide con EXPECTED_SHA256",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    models_dir: pathlib.Path = args.models_dir
    models_dir.mkdir(parents=True, exist_ok=True)

    # overrides de URL si se pasan por CLI
    urls: dict[str, str] = {
        "yolo11n.onnx": args.yolo_url,
        "yolo11n-pose.onnx": args.pose_url,
        "midas_small_256.onnx": args.depth_url,
        "hand_landmarker.task": args.hand_url,
        "yolo-world-s.onnx": args.world_url,
    }

    ok = True
    for filename in (
        "yolo11n.onnx",
        "yolo11n-pose.onnx",
        "midas_small_256.onnx",
        "hand_landmarker.task",
        "yolo-world-s.onnx",
    ):
        url = urls[filename]
        dest = models_dir / filename
        expected = EXPECTED_SHA256.get(filename)
        # sin --verify-hash no exigimos hash estricto
        # download_one ya loguea; con --verify-hash el mismatch causa re-descarga
        if (
            not args.verify_hash
            and dest.exists()
            and not args.force
            and expected is not None
        ):
            # modo laxo: si el archivo existe no validamos estricto, solo skip
            # para no romper idempotencia cuando el hash remoto cambie
            pass
        success = download_one(filename, url, dest, args.force, expected)
        ok = ok and success

    # frontend visi├│n viva (036): blaze + mobilefacenet a public/models/
    # mobilefacenet sin fuente verificada (deuda Opci├│n C) ÔåÆ skip con aviso, no falla
    if not args.skip_frontend:
        FRONTEND_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        fe_urls: dict[str, str] = {
            "blaze_face_short_range.tflite": args.blaze_url,
            "mobilefacenet.onnx": args.face_url,
        }
        for filename in ("blaze_face_short_range.tflite", "mobilefacenet.onnx"):
            dest = FRONTEND_MODELS_DIR / filename
            if not fe_urls[filename]:
                if dest.exists():
                    print(f"[SKIP] {filename} presente ({dest.stat().st_size:,} bytes)")
                else:
                    print(
                        f"[DEUDA] {filename} sin fuente p├║blica verificada "
                        "(stub fallback activo ÔÇö ver MOBILEFACENET_URL)"
                    )
                continue
            success = download_one(filename, fe_urls[filename], dest, args.force, None)
            ok = ok and success

    if ok:
        print("\nTodos los modelos listos en", models_dir)
        if not args.skip_frontend:
            print("Frontend modelos en", FRONTEND_MODELS_DIR)
        return 0
    print("\nAlgunos modelos fallaron ÔÇö revisar logs", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
