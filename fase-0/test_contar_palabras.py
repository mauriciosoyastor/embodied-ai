from contar_palabras import contar_palabras


def test_cuenta_palabras_de_frase_simple():
    assert contar_palabras("hola mundo") == 2


def test_ignora_espacios_extra():
    assert contar_palabras("   hola    mundo   ") == 2


def test_texto_vacio_devuelve_cero():
    assert contar_palabras("") == 0


def test_palabras_con_signos_de_puntuacion():
    assert contar_palabras("hola, mundo! como estas?") == 4