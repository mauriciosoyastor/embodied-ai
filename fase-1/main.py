"""CLI para consultar Gemini.

Uso:
    python main.py "tu prompt"
"""

import sys

from gemini_client import responder

USO = 'python main.py "tu prompt"'


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Uso: {USO}")
        sys.exit(1)
    print(responder(sys.argv[1]))


if __name__ == "__main__":
    main()
