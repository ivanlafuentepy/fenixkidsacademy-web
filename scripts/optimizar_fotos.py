#!/usr/bin/env python3
# scripts/optimizar_fotos.py — redimensiona/comprime fotos nuevas y actualiza fotos/assets/photos.js
#
# Pensado para correr semanalmente sobre la misma carpeta de origen (o una carpeta nueva
# cada vez): las fotos ya procesadas se detectan por nombre+tamano en manifest.json y se
# saltan solas, asi que nunca se renumeran ni se pisan las de una corrida anterior.
# La fecha/hora sale del EXIF (DateTimeOriginal) de cada foto — se usa para agrupar por
# dia de entrenamiento en la pagina y ordenar cronologicamente dentro de cada dia.
import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Falta Pillow. Instalar con: pip install -r scripts/requirements.txt")

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pillow_heif = None

THUMB_WIDTH, FULL_WIDTH = 480, 1600
THUMB_QUALITY, FULL_QUALITY = 70, 78
EXTENSIONES = {".jpg", ".jpeg", ".png", ".heic"}
MANIFEST_NOMBRE = "manifest.json"
PHOTOS_JS_NOMBRE = "photos.js"

DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
            "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def cargar_manifest(salida: Path) -> dict:
    ruta = salida / MANIFEST_NOMBRE
    if ruta.exists():
        return json.loads(ruta.read_text(encoding="utf-8"))
    return {}


def guardar_manifest(salida: Path, manifest: dict):
    (salida / MANIFEST_NOMBRE).write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def extraer_fecha(origen: Path) -> str | None:
    """Devuelve la fecha/hora EXIF (DateTimeOriginal) en formato ISO, o None si no tiene."""
    try:
        exif = Image.open(origen).getexif()
        crudo = exif.get(306)  # DateTime
        if not crudo:
            crudo = exif.get_ifd(0x8769).get(36867)  # DateTimeOriginal
        if not crudo:
            return None
        dt = datetime.strptime(crudo, "%Y:%m:%d %H:%M:%S")
        return dt.isoformat()
    except Exception:
        return None


def fecha_de_carpeta(origen: Path) -> str | None:
    """Fecha del nombre de la carpeta contenedora ('YYYY-MM-DD Dia'), o None."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})\b", origen.parent.name)
    return m.group(1) if m else None


def fecha_foto(origen: Path) -> str | None:
    """Fecha efectiva de una foto. LA CARPETA MANDA: si Ivan puso la foto en una
    carpeta 'YYYY-MM-DD Dia', esa es la fecha aunque el EXIF diga otra cosa
    (WhatsApp borra o pisa el EXIF con la fecha del reenvio). El EXIF solo
    aporta la hora cuando coincide con el dia de la carpeta, y es el fallback
    para fotos fuera de carpetas de fecha."""
    exif = extraer_fecha(origen)
    carpeta = fecha_de_carpeta(origen)
    if carpeta:
        if exif and exif[:10] == carpeta:
            return exif  # mismo dia: el EXIF suma la hora (ordena dentro del dia)
        return carpeta
    return exif


def etiqueta_dia(fecha_iso: str) -> str:
    dt = datetime.fromisoformat(fecha_iso)
    return f"{DIAS_ES[dt.weekday()]} {dt.day} de {MESES_ES[dt.month - 1]} de {dt.year}"


def escribir_photos_js(salida: Path, manifest: dict):
    grupos = defaultdict(list)
    sin_fecha = []
    for info in manifest.values():
        fecha = info.get("fecha")
        if fecha:
            dia = fecha[:10]
            grupos[dia].append((fecha, info["salida"]))
        else:
            sin_fecha.append(info["salida"])

    bloques = []
    for dia in sorted(grupos, reverse=True):  # dia mas reciente primero
        fotos_dia = [nombre for _, nombre in sorted(grupos[dia])]  # hora ascendente dentro del dia
        bloques.append({"fecha": dia, "etiqueta": etiqueta_dia(grupos[dia][0][0]), "fotos": fotos_dia})
    if sin_fecha:
        bloques.append({"fecha": None, "etiqueta": "Sin fecha", "fotos": sin_fecha})

    partes = []
    for b in bloques:
        fotos_js = ",\n      ".join(f"'{n}'" for n in b["fotos"])
        partes.append(
            "  { etiqueta: '%s', fotos: [\n      %s\n    ] }" % (b["etiqueta"].replace("'", "\\'"), fotos_js)
        )
    contenido = "const photoGroups = [\n" + ",\n".join(partes) + "\n];\n"
    (salida / PHOTOS_JS_NOMBRE).write_text(contenido, encoding="utf-8")


def procesar(origen: Path, destino: Path, ancho: int, calidad: int):
    img = Image.open(origen)
    img = ImageOps.exif_transpose(img)  # corrige rotacion de fotos de celular
    if img.mode != "RGB":
        img = img.convert("RGB")
    if img.width > ancho:
        alto = int(img.height * ancho / img.width)
        img = img.resize((ancho, alto), Image.LANCZOS)
    img.save(destino, "JPEG", quality=calidad, optimize=True, progressive=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("carpeta_origen", type=Path, help="Carpeta con fotos (las ya procesadas antes se saltan solas)")
    ap.add_argument("--salida", type=Path, default=Path("fotos/assets"), help="Carpeta de salida (default: fotos/assets)")
    args = ap.parse_args()

    if not args.carpeta_origen.is_dir():
        sys.exit(f"No existe: {args.carpeta_origen}")

    heic_sin_soporte = []
    fuentes = []
    for p in sorted(args.carpeta_origen.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in EXTENSIONES:
            continue
        if p.suffix.lower() == ".heic" and pillow_heif is None:
            heic_sin_soporte.append(p.name)
            continue
        fuentes.append(p)

    if heic_sin_soporte:
        aviso = ", ".join(heic_sin_soporte[:5]) + ("..." if len(heic_sin_soporte) > 5 else "")
        print(f"Aviso: {len(heic_sin_soporte)} .HEIC no procesados (falta pillow-heif): {aviso}")

    thumb_dir, full_dir = args.salida / "thumb", args.salida / "full"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    full_dir.mkdir(parents=True, exist_ok=True)

    manifest = cargar_manifest(args.salida)
    siguiente = 1
    if manifest:
        siguiente = max(int(Path(info["salida"]).stem.split("-")[1]) for info in manifest.values()) + 1

    nuevas = 0
    backfill = 0
    for origen in fuentes:
        clave = f"{origen.name}:{origen.stat().st_size}"
        if clave in manifest:
            # la fecha se recalcula siempre: si Ivan movio la foto a otra carpeta
            # de dia, la carpeta manda y la correccion entra sola en la proxima corrida
            fecha_nueva = fecha_foto(origen)
            if manifest[clave].get("fecha") != fecha_nueva:
                manifest[clave]["fecha"] = fecha_nueva
                backfill += 1
            continue
        nombre = f"foto-{siguiente:04d}.jpg"
        procesar(origen, thumb_dir / nombre, THUMB_WIDTH, THUMB_QUALITY)
        procesar(origen, full_dir / nombre, FULL_WIDTH, FULL_QUALITY)
        manifest[clave] = {"origen": origen.name, "salida": nombre, "fecha": fecha_foto(origen)}
        print(f"  {origen.name} -> {nombre}")
        siguiente += 1
        nuevas += 1

    if nuevas == 0 and backfill == 0:
        print("No hay fotos nuevas para procesar (todas ya estaban en el manifest).")
        return

    guardar_manifest(args.salida, manifest)
    escribir_photos_js(args.salida, manifest)
    if nuevas:
        print(f"\n{nuevas} fotos nuevas procesadas. Total acumulado: {len(manifest)}.")
    if backfill:
        print(f"{backfill} fotos existentes con fecha corregida (carpeta/EXIF).")
    print(f"{args.salida}/{PHOTOS_JS_NOMBRE} actualizado — no hace falta tocar el HTML.")


if __name__ == "__main__":
    main()
