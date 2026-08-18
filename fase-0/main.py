"""Conteo de palabras en texto plano.

Uso:
    python contar_palabras.py archivo.txt
"""

import sys

from contar_palabras import contar_palabras


def main():
    if len(sys.argv) != 2:
        print("Uso: python contar_palabras.py <archivo>")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as archivo:
        texto = archivo.read()
    print(f"Cantidad de palabras: {contar_palabras(texto)}")


if __name__ == "__main__":
    main()