# Asistente de voz para la abuela

## Contexto del problema

Mi abuela tiene una Alexa pero no logra acostumbrarse a llamarla por su nombre,
así que en la práctica no la usa. El objetivo es un asistente de voz que ella sí
pueda usar, enfocado sobre todo en poner música.

**El problema central no es la IA, es el trigger de activación.** Todo el diseño
gira en torno a eso.

## Decisiones ya tomadas

### Activación
- **v1: botón físico grande** (tipo arcade 60mm o el del ReSpeaker HAT). Apretar,
  hablar, soltar. Es gestual, no hay nada que recordar.
- **v2 (opcional): wake word custom** con openWakeWord, entrenado con la palabra
  que ella use naturalmente. Solo si el botón resulta insuficiente.
- Descartado: escucha permanente con VAD (falsos positivos con la TV, y un mic
  abierto todo el día en su casa).

### Arquitectura de cómputo
- **Sin depender del homelab personal** ni de servidor arrendado. La Pi es
  autónoma y usa APIs para lo pesado.
- **Local en la Pi:** wake word / botón, VAD, router de intents, TTS,
  reproducción de música.
- **Por API:** STT (Groq whisper-large-v3-turbo) y LLM (Claude Haiku o Gemini
  Flash).
- **Router de intents ANTES del LLM.** Comandos frecuentes (música, volumen,
  parar, hora, radio) se resuelven con matching de patrones local. Esto baja
  latencia, baja costo y — lo más importante — **mantiene funcionando lo esencial
  sin internet**.

### Por qué no otras opciones
- **n8n para el loop de voz:** no. Cada nodo suma latencia; el loop
  audio→texto→LLM→audio tiene que ser un proceso local directo. n8n queda solo
  para heartbeat y recordatorios, fuera del camino crítico.
- **Home Assistant:** un solo dispositivo y ~6 intents no justifican la capa de
  abstracción. Script propio es más liviano y más fácil de depurar en remoto.
  Reconsiderar solo si se termina con Pi 4 de 4GB.
- **Docker en la Pi:** no. ALSA y GPIO en contenedor duplican los problemas que
  igual hay que resolver en el host, y el driver del ReSpeaker es de kernel.
  systemd + venv con `uv` da arranque automático, restart y logs sin capas extra.
- **Arduino / ESP32:** Arduino es microcontrolador, no corre Linux. ESP32-S3 solo
  serviría como satélite de un servidor, que es justo lo que se quiere evitar.

## Hardware

Aún no comprado. Placa objetivo: **Raspberry Pi 3B+ usada** o **Pi 4 4GB** si el
precio es razonable.

| Pieza | Elección | Nota |
|---|---|---|
| Placa | Pi 3B+ (1GB) o Pi 4 (4GB) | Solo corre wake word + TTS + reproducción |
| Micrófono | ReSpeaker 2-Mics Pi HAT | Trae botón físico y LEDs RGB incluidos |
| Parlante | Activo por jack 3.5mm | Por cable, nunca Bluetooth |
| MicroSD | 32GB clase A1/A2 | Las genéricas se corrompen |
| Fuente | 5V 3A estable | La 3B+ se reinicia sola con fuente débil |
| Respaldo | Power bank con passthrough | Para cortes de luz |
| Caja | Pasiva, sin ventilador | Ver advertencia abajo |

**Advertencias de hardware:**
- El driver `seeed-voicecard` del ReSpeaker está medio abandonado y pelea con
  kernels nuevos. Hay forks de la comunidad.
- **Si es Pi 4: refrigeración pasiva obligatoria.** Un ventilador a 20cm del
  micrófono mete ruido constante y degrada la transcripción.
- El micrófono es el cuello de botella real del proyecto, no la placa.

### Qué cambia entre Pi 3B+ y Pi 4
La arquitectura es idéntica. Con Pi 4 (4GB) se gana: voces Piper de calidad
`medium` en vez de `low` (diferencia audible), y espacio para whisper.cpp `base`
como **fallback local de STT** cuando no hay internet. La versión de 2GB no
justifica el upgrade.

## Stack de software

**SO:** Raspberry Pi OS Lite 64-bit (sin escritorio).

**Local:**
- `gpiozero` — botón por GPIO
- `openwakeword` — palabra clave (fase 2)
- `silero-vad` — detección de fin de frase
- `piper-tts` — voz `es_MX-ald` o `es_ES-davefx`
- MPD + `python-mpd2` — música desde biblioteca local en pendrive
- ALSA directo, sin PulseAudio

**APIs:**
- Groq `whisper-large-v3-turbo` para STT (entiende bien habla de adulto mayor)
- Claude Haiku o Gemini Flash para preguntas abiertas

**Operación:**
- Servicio **systemd** con `Restart=always` y watchdog
- **Tailscale** — indispensable para arreglar cosas sin viajar
- **Sonido corto de confirmación** al activarse (tipo "bong" de Alexa). Es lo que
  le confirma a ella que fue escuchada; impacta mucho en si lo adopta o lo
  abandona.

**Prompt del LLM:** máximo dos frases, español chileno, **sin markdown ni
emojis** (Piper lee los asteriscos en voz alta).

## Estrategia de desarrollo: primero en la Mac

Se desarrolla en MacBook Air M3 antes de tener la Pi. La clave es **abstraer las
dos piezas dependientes de hardware** para que el port sea cambiar un config y no
reescribir:

- `trigger.py` → `KeyboardTrigger` (Mac, barra espaciadora) / `GPIOTrigger` (Pi)
- `tts.py` → `SayTTS` (Mac, fallback si Piper falla) / `PiperTTS`

Todo lo demás (STT, LLM, router de intents, MPD, audio vía `sounddevice`) es
idéntico en ambos lados.

### Estructura
```
abuela-asistente/
├── src/
│   ├── main.py          # loop principal
│   ├── trigger.py       # abstracción botón/teclado
│   ├── audio.py         # grabar + reproducir
│   ├── vad.py
│   ├── stt.py           # Groq
│   ├── intents.py       # router local, ANTES del LLM
│   ├── llm.py
│   ├── tts.py           # abstracción Piper/say
│   └── music.py         # MPD
├── config/
│   ├── mac.toml
│   └── pi.toml
├── deploy/
│   ├── asistente.service
│   └── update.sh
├── .env                 # en .gitignore
└── pyproject.toml
```

Gestor de entorno: `uv`. Repo privado en GitHub desde el primer commit.
`.gitignore`: `.env` y la biblioteca de mp3.

### Setup en la Mac
```
brew install python@3.12 portaudio mpd mpc ffmpeg
curl -LsSf https://astral.sh/uv/install.sh | sh
```

`portaudio` es dependencia nativa de `sounddevice`.

**Piper en macOS arm64** es la pieza más probable de fallar (builds de PyPI
inestables). Si falla: bajar el binario de los releases de GitHub, o usar `say`
detrás de la abstracción de TTS y seguir adelante. En la Pi anda sin drama.

### Lo que NO se puede validar en la Mac
- Rendimiento real (el M3 es 20-50x más rápido que una Pi 3)
- Calidad del mic a 3 metros
- Configuración de ALSA
- GPIO

Truco: contenedor `debian:bookworm-slim` arm64 en la Mac para verificar que los
paquetes tengan wheel para ARM Linux. No sirve para audio, sí para detectar
temprano qué no compila.

## Orden de construcción

Cada paso deja algo funcionando:

1. Loop mínimo: barra espaciadora → graba wav → lo reproduce (valida toda la
   cadena de audio)
2. Groq enchufado: imprime en consola lo transcrito
3. **Router de intents** — la parte que más conviene hacer en la Mac: puro texto
   y lógica, cero hardware. Definir las ~6 frases y sus variantes.
4. MPD + intent de música → **acá ya es útil para la abuela, sin LLM todavía**
5. LLM para preguntas abiertas
6. Wake word, solo si el botón resultó insuficiente

## Deploy

```
git clone <repo> ~/asistente && cd ~/asistente
uv sync
# crear .env a mano, una sola vez
sudo cp deploy/asistente.service /etc/systemd/system/
sudo systemctl enable --now asistente
```

Actualizaciones (vía Tailscale, desde la Mac):
```
ssh pi@asistente 'cd ~/asistente && git pull && uv sync && sudo systemctl restart asistente'
```

**Nunca editar archivos directo en la Pi.** Siempre commit → pull, para que el
repo refleje lo que realmente está corriendo.

## Pendientes / decisiones abiertas

- Definir los intents exactos. Falta observar cómo le habla ella a la Alexa
  actual para calcar sus frases reales en vez de inventarlas.
- Elegir placa según precio encontrado (3B+ usada vs Pi 4 4GB).
- Armar la biblioteca de música: ~60 canciones suyas descargadas. No depender de
  Spotify (requiere Premium y librespot se rompe seguido).

## Nota de privacidad

Va a haber un micrófono conectado a APIs en la casa de mi abuela. Ella tiene que
saber, en términos simples, que el aparato escucha y manda audio a internet.
Revisar y desactivar la retención de audio en el proveedor de STT (Groq y
Deepgram lo permiten).
