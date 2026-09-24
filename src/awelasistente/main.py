"""Loop principal. Paso 1: apretar -> grabar -> soltar -> reproducir lo grabado."""

import sys
from datetime import datetime
from pathlib import Path

from awelasistente import audio, config, trigger


def main() -> None:
    cfg = config.cargar(sys.argv[1] if len(sys.argv) > 1 else None)
    sr = cfg["audio"]["sample_rate"]
    carpeta = Path(cfg["audio"]["carpeta_grabaciones"])

    disparador = trigger.crear(cfg)
    grabadora = audio.Grabadora(sr, cfg["audio"]["canales"])

    print("Listo. Espacio para hablar, espacio para terminar. Ctrl+C para salir.")
    try:
        while True:
            disparador.esperar_presion()
            audio.bong(sr)
            grabadora.empezar()
            print("● grabando...")

            disparador.esperar_soltar()
            grabado = grabadora.terminar()
            segundos = len(grabado) / sr
            print(f"■ {segundos:.1f} s grabados")

            if segundos < 0.3:
                print("  (muy corto, lo ignoro)")
                continue

            ruta = carpeta / f"{datetime.now():%Y%m%d-%H%M%S}.wav"
            audio.guardar_wav(grabado, sr, ruta)
            print(f"  guardado en {ruta}, reproduciendo...")
            audio.reproducir(grabado, sr)
    except KeyboardInterrupt:
        print("\nChao.")


if __name__ == "__main__":
    main()
