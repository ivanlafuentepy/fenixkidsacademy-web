#!/usr/bin/env python3
# scripts/organizar_fotos_por_fecha.py — agrupa fotos y videos sueltos de una carpeta en subcarpetas por dia
#
# Fotos: fecha via EXIF (DateTimeOriginal). Videos: fecha via metadata QuickTime/MP4 (ffprobe),
# preferiendo com.apple.quicktime.creationdate (ya trae offset local) sobre creation_time (UTC,
# a veces desactualizado en videos reencodeados/reenviados por WhatsApp).
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
import optimizar_fotos as of

EXTENSIONES_VIDEO = {".mov", ".mp4"}
TZ_LOCAL = ZoneInfo("America/Asuncion")


def extraer_fecha_video(path: Path) -> str | None:
    if shutil.which("ffprobe") is None:
        return None
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_entries", "format_tags", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        tags = json.loads(r.stdout).get("format", {}).get("tags", {})
    except Exception:
        return None

    creationdate = tags.get("com.apple.quicktime.creationdate")
    if creationdate:
        try:
            return datetime.fromisoformat(creationdate).astimezone(TZ_LOCAL).isoformat()
        except ValueError:
            pass

    creation_time = tags.get("creation_time")
    if creation_time:
        try:
            dt = datetime.fromisoformat(creation_time.replace("Z", "+00:00"))
            return dt.astimezone(TZ_LOCAL).isoformat()
        except ValueError:
            pass
    return None


def extraer_fecha(path: Path) -> str | None:
    if path.suffix.lower() in of.EXTENSIONES:
        return of.extraer_fecha(path)
    if path.suffix.lower() in EXTENSIONES_VIDEO:
        return extraer_fecha_video(path)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("carpeta", type=Path, help="Carpeta con fotos/videos sueltos para organizar (no recursivo)")
    ap.add_argument("--destino", type=Path, default=None,
                     help="Carpeta base donde crear/fusionar las subcarpetas por fecha (default: la misma carpeta)")
    ap.add_argument("--simular", action="store_true", help="Solo mostrar que se haria, sin mover nada")
    args = ap.parse_args()

    if not args.carpeta.is_dir():
        sys.exit(f"No existe: {args.carpeta}")

    destino_base = args.destino or args.carpeta
    extensiones = of.EXTENSIONES | EXTENSIONES_VIDEO

    por_carpeta = {}
    movidas = 0
    for p in sorted(args.carpeta.iterdir()):
        if not p.is_file() or p.suffix.lower() not in extensiones:
            continue
        fecha = extraer_fecha(p)
        if fecha:
            dt = datetime.fromisoformat(fecha)
            nombre_carpeta = f"{dt.date()} {of.DIAS_ES[dt.weekday()]}"
        else:
            nombre_carpeta = "Sin fecha"

        destino_dir = destino_base / nombre_carpeta
        destino = destino_dir / p.name
        if destino.exists():
            print(f"  Aviso: ya existe {destino}, no se mueve {p.name}")
            continue

        if args.simular:
            print(f"  {p.name} -> {nombre_carpeta}/")
        else:
            destino_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(destino))
        por_carpeta[nombre_carpeta] = por_carpeta.get(nombre_carpeta, 0) + 1
        movidas += 1

    if movidas == 0:
        print("No habia archivos sueltos para organizar en la raiz de la carpeta.")
        return

    verbo = "se organizarian" if args.simular else "organizados"
    print(f"\n{movidas} archivos {verbo} en {len(por_carpeta)} carpetas:")
    for carpeta, n in sorted(por_carpeta.items(), reverse=True):
        print(f"  {carpeta}: {n} archivos")


if __name__ == "__main__":
    main()
