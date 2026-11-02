"""Download daily Mexico City air-quality (RAMA) and weather (REDMET) averages, 2015-01 to 2023-05.

Source: SIMAT / datos.cdmx.gob.mx, daily city-wide averages as prepared in
https://github.com/jamc88/Analisis-datos-atmosfericos (course material used in the original project).
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/jamc88/Analisis-datos-atmosfericos/refs/heads/main/datos"


def main() -> None:
    out = Path("data/raw")
    out.mkdir(parents=True, exist_ok=True)
    for name in ("rama_2023_05.csv", "redmet_2023_05.csv"):
        if not (out / name).exists():
            urllib.request.urlretrieve(f"{BASE}/{name}", out / name)
    print(f"Data ready in {out.resolve()}")


if __name__ == "__main__":
    main()
