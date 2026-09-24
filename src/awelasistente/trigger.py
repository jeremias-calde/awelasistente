"""Abstracción del disparador: teclado en la Mac, botón GPIO en la Pi.

El resto del programa solo conoce dos métodos:
    esperar_presion()  -> bloquea hasta que ella aprieta
    esperar_soltar()   -> bloquea hasta que suelta
"""

import sys
import termios
import tty
from typing import Protocol


class Trigger(Protocol):
    def esperar_presion(self) -> None: ...
    def esperar_soltar(self) -> None: ...


class KeyboardTrigger:
    """Barra espaciadora como botón.

    Una terminal no avisa cuándo se suelta una tecla, solo cuándo se aprieta.
    Por eso acá funciona como interruptor: espacio para empezar, espacio para
    terminar. En la Pi, el botón real sí será "mantener apretado".
    """

    def _esperar_espacio(self) -> None:
        fd = sys.stdin.fileno()
        anterior = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)  # leer tecla por tecla, sin esperar Enter
            while sys.stdin.read(1) != " ":
                pass
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, anterior)

    def esperar_presion(self) -> None:
        self._esperar_espacio()

    def esperar_soltar(self) -> None:
        self._esperar_espacio()


def crear(config: dict) -> Trigger:
    tipo = config["trigger"]["tipo"]
    if tipo == "teclado":
        return KeyboardTrigger()
    raise ValueError(f"Trigger desconocido: {tipo!r}")
