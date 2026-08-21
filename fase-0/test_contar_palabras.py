from contar_palabras import contar_caracteres, contar_palabras


def test_cuenta_palabras_de_frase_simple() -> None:
    assert contar_palabras("hola mundo") == 2


def test_ignora_espacios_extra() -> None:
    assert contar_palabras("   hola    mundo   ") == 2


def test_texto_vacio_devuelve_cero() -> None:
    assert contar_palabras("") == 0


def test_palabras_con_signos_de_puntuacion() -> None:
    assert contar_palabras("hola, mundo! como estas?") == 4


def test_cuenta_caracteres_sin_espacio() -> None:
    assert contar_caracteres("hola mundo") == 9


def test_texto_vacio_devuelve_cero_caracteres() -> None:
    assert contar_caracteres("") == 0


def test_ignora_espacios_en_caracteres() -> None:
    assert contar_caracteres("  abc  ") == 3
