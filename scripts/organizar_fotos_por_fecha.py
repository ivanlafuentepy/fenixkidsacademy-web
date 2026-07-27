#!/usr/bin/env python3
# scripts/organizar_fotos_por_fecha.py — agrupa fotos sueltas de una carpeta en subcarpetas por dia (EXIF)
import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import optimizar_fotos as of


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("carpeta", type=Path, help="Carpeta con fotos sueltas para organizar (no recursivo)")
    args = ap.parse_args()

    if not args.carpeta.is_dir():
        sys.exit(f"No existe: {args.carpeta}")

    por_carpeta = {}
    movidas = 0
    for p in sorted(args.carpeta.iterdir()):
        if not p.is_file() or p.suffix.lower() not in of.EXTENSIONES:
            continue
        fecha = of.extraer_fecha(p)
        if fecha:
            dt = datetime.fromisoformat(fecha)
            nombre_carpeta = f"{dt.date()} {of.DIAS_ES[dt.weekday()]}"
        else:
            nombre_carpeta = "Sin fecha"

        destino_dir = args.carpeta / nombre_carpeta
        destino_dir.mkdir(exist_ok=True)
        destino = destino_dir / p.name
        if destino.exists():
            print(f"  Aviso: ya existe {destino}, no se mueve {p.name}")
            continue

        shutil.move(str(p), str(destino))
        por_carpeta[nombre_carpeta] = por_carpeta.get(nombre_carpeta, 0) + 1
        movidas += 1

    if movidas == 0:
        print("No habia fotos sueltas para organizar en la raiz de la carpeta.")
        return

    print(f"{movidas} fotos organizadas en {len(por_carpeta)} carpetas:")
    for carpeta, n in sorted(por_carpeta.items(), reverse=True):
        print(f"  {carpeta}: {n} fotos")


if __name__ == "__main__":
    main()
