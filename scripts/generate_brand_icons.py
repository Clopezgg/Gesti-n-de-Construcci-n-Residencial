"""Regenera los iconos PNG de NEXORA a partir de la fuente única de verdad.

`nexora_app/nexora/public/images/nexora.svg` es la fuente única del mark de marca
(el mismo activo que usa `add_to_apps_screen`, el favicon y este script). Los PNG
del manifiesto PWA (`nexora-192.png`/`nexora-512.png`, Bloque 125) se derivan de
ese SVG, nunca se editan a mano — correr este script tras cualquier cambio al SVG
es la única forma soportada de mantenerlos sincronizados.

Requiere `cairosvg` (`pip install cairosvg`) y la librería nativa `cairo`
(`brew install cairo` en macOS, `apt install libcairo2` en Debian/Ubuntu — ya
presente en los runners de GitHub Actions vía las dependencias de Playwright).

Uso: python3 scripts/generate_brand_icons.py
"""

from __future__ import annotations

import pathlib

import cairosvg

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "nexora_app/nexora/public/images/nexora.svg"
TARGETS = {
	REPO_ROOT / "nexora_app/nexora/public/images/nexora-192.png": 192,
	REPO_ROOT / "nexora_app/nexora/public/images/nexora-512.png": 512,
}


def main() -> None:
	if not SOURCE.is_file():
		raise SystemExit(f"No se encontró la fuente de marca: {SOURCE}")
	for target, size in TARGETS.items():
		cairosvg.svg2png(url=str(SOURCE), write_to=str(target), output_width=size, output_height=size)
		print(f"{target.relative_to(REPO_ROOT)} regenerado ({size}x{size})")


if __name__ == "__main__":
	main()
