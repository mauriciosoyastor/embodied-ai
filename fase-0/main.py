"""Conteo de palabras en texto plano.

Uso:
    python main.py <archivo>
"""

import sys

from contar_palabras import contar_palabras

USO = "python main.py <archivo>"


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Uso: {USO}")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as archivo:
        texto = archivo.read()
    print(f"Cantidad de palabras: {contar_palabras(texto)}")


if __name__ == "__main__":
    main()
