"""Grabar desde el micrófono, guardar WAV y reproducir. Igual en Mac y Pi."""

import wave
from pathlib import Path

import numpy as np
import sounddevice as sd


class Grabadora:
    """Graba mientras está abierta; al cerrarla devuelve el audio acumulado."""

    def __init__(self, sample_rate: int, canales: int):
        self.sample_rate = sample_rate
        self.canales = canales
        self._bloques: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None

    def _callback(self, datos, frames, tiempo, estado):
        # Corre en otro hilo cada ~pocos ms con un bloque nuevo de audio.
        if estado:
            print(f"[audio] {estado}")
        self._bloques.append(datos.copy())

    def empezar(self) -> None:
        self._bloques = []
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.canales,
            dtype="int16",
            callback=self._callback,
        )
        self._stream.start()

    def terminar(self) -> np.ndarray:
        self._stream.stop()
        self._stream.close()
        self._stream = None
        if not self._bloques:
            return np.zeros((0, self.canales), dtype="int16")
        return np.concatenate(self._bloques)


def guardar_wav(audio: np.ndarray, sample_rate: int, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(ruta), "wb") as f:
        f.setnchannels(audio.shape[1])
        f.setsampwidth(2)  # int16 = 2 bytes por muestra
        f.setframerate(sample_rate)
        f.writeframes(audio.tobytes())


def reproducir(audio: np.ndarray, sample_rate: int) -> None:
    sd.play(audio, sample_rate)
    sd.wait()


def bong(sample_rate: int) -> None:
    """Sonido corto de confirmación: le dice a ella 'te estoy escuchando'.

    Dos tonos ascendentes con desvanecido, para que no suene como pitido de
    alarma. Se genera en código; más adelante se puede cambiar por un .wav.
    """
    duracion = 0.12
    t = np.linspace(0, duracion, int(sample_rate * duracion), endpoint=False)
    envolvente = np.exp(-t * 18)  # decae suave, tipo campanita
    tono1 = np.sin(2 * np.pi * 660 * t) * envolvente
    tono2 = np.sin(2 * np.pi * 880 * t) * envolvente
    señal = np.concatenate([tono1, tono2]) * 0.4
    reproducir((señal * 32767).astype("int16"), sample_rate)
