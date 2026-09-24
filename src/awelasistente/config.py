"""Carga el archivo de configuración TOML (mac.toml o pi.toml)."""

import os
import tomllib
from pathlib import Path

CONFIG_POR_DEFECTO = "config/mac.toml"


def cargar(ruta: str | None = None) -> dict:
    """Lee la config. Orden: argumento > variable AWELA_CONFIG > mac.toml."""
    ruta = ruta or os.environ.get("AWELA_CONFIG", CONFIG_POR_DEFECTO)
    with Path(ruta).open("rb") as f:
        return tomllib.load(f)
