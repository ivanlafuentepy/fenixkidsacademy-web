#!/usr/bin/env python3
# scripts/borrar_fotos.py — borra fotos ya publicadas (thumb+full+manifest) y regenera photos.js
#
# Recibe los nombres tal como aparecen en fotos/assets/ (ej: foto-0041.jpg). Pensado para
# usarse con el comando que genera fotos/admin.html al tildar fotos para borrar.
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import optimizar_fotos as of


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fotos", nargs="+", help="Nombres a borrar, ej: foto-0041.jpg foto-0042.jpg")
    ap.add_argument("--salida", type=Path, default=Path("fotos/assets"), help="Carpeta de salida (default: fotos/assets)")
    ap.add_argument("--tambien-borrar-original", type=Path, default=None,
                     help="Carpeta donde buscar (recursivo) y borrar tambien el archivo original")
    args = ap.parse_args()

    manifest = of.cargar_manifest(args.salida)
    objetivo = {Path(n).name for n in args.fotos}

    borradas = []
    for clave in list(manifest.keys()):
        info = manifest[clave]
        if info["salida"] not in objetivo:
            continue
        for carpeta in ("thumb", "full"):
            ruta = args.salida / carpeta / info["salida"]
            if ruta.exists():
                ruta.unlink()
        _, _, tam_str = clave.rpartition(":")
        borradas.append({**info, "origen_size": int(tam_str)})
        del manifest[clave]

    faltantes = objetivo - {b["salida"] for b in borradas}
    if faltantes:
        print(f"Aviso: no estaban en el manifest (¿ya borradas?): {', '.join(sorted(faltantes))}")

    if not borradas:
        print("Nada para borrar.")
        return

    of.guardar_manifest(args.salida, manifest)
    of.escribir_photos_js(args.salida, manifest)

    for b in borradas:
        print(f"  borrada: {b['salida']} (origen: {b['origen']})")

    if args.tambien_borrar_original:
        carpeta = args.tambien_borrar_original
        if not carpeta.is_dir():
            print(f"Aviso: no existe la carpeta {carpeta}, no se buscan originales.")
        else:
            for b in borradas:
                encontrado = next(
                    (p for p in carpeta.rglob(b["origen"]) if p.stat().st_size == b["origen_size"]),
                    None,
                )
                if encontrado:
                    encontrado.unlink()
                    print(f"  original borrado: {encontrado}")
                else:
                    print(f"  Aviso: no encontre el original de {b['origen']} en {carpeta}")

    print(f"\n{len(borradas)} fotos borradas. Total restante: {len(manifest)}.")
    print("Ahora: git add -A && git commit -m \"...\" && git push")


if __name__ == "__main__":
    main()
