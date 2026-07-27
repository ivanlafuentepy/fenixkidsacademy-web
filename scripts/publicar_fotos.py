#!/usr/bin/env python3
# scripts/publicar_fotos.py — pipeline completo de fotos Fenix con un doble click
#
# Lo dispara el acceso directo "FOTOS FENIX.bat" del Escritorio de Ivan (o el
# skill /fotosfenix de Claude Code). Hace el ciclo entero:
#   1. Ordena la bandeja FENIX FOTOS/FOTOS por fecha (fotos Y videos)
#   2. Publica las fotos nuevas en fenixkidsacademy.com/fotos/ (optimizar + git push)
#   3. Taggea caras para los links familiares (solo si el batch inicial ya fue aplicado)
#   4. Le avisa a Ivan por WhatsApp con el link
#
# Todo es incremental y re-ejecutable: si no hay nada nuevo, no comitea ni avisa.
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# El CLOUDFLARE_API_TOKEN viejo del entorno de Windows pisa el login OAuth de
# wrangler y da "Authentication error" — se saca antes de cualquier subprocess.
os.environ.pop("CLOUDFLARE_API_TOKEN", None)

NPX = shutil.which("npx") or "npx"

INBOX = Path(r"C:\Users\IVAN LAFUENTE\Desktop\FENIX FOTOS\FOTOS")
BASE_FOTOS = Path(r"C:\Users\IVAN LAFUENTE\Desktop\FENIX FOTOS")
REPO_WEB = Path(r"C:\Users\IVAN LAFUENTE\Projects\fenixkidsacademy-web")
REPO_AGENT = Path(r"C:\Users\IVAN LAFUENTE\Projects\fenix-kids-agent")
RAILWAY_URL = "https://fenix-kids-agent-production.up.railway.app"
TELEFONO_IVAN = "595982790407"
LINK_PAGINA = "https://fenixkidsacademy.com/fotos/"

EXT_MEDIA = {".jpg", ".jpeg", ".png", ".heic", ".mov", ".mp4"}


def correr(cmd: list, cwd: Path) -> str:
    """Corre un comando mostrando el output en vivo y lo devuelve como texto."""
    print(f"\n$ {' '.join(str(c) for c in cmd)}")
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    salida = (proc.stdout or "") + (proc.stderr or "")
    print(salida.strip())
    if proc.returncode != 0:
        raise RuntimeError(f"Fallo (exit {proc.returncode}): {' '.join(str(c) for c in cmd)}")
    return salida


def leer_admin_key() -> str:
    """ADMIN_API_KEY del .env del agente (para /test-envio). No se imprime."""
    env = REPO_AGENT / ".env"
    if env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            if linea.startswith("ADMIN_API_KEY="):
                return linea.split("=", 1)[1].strip()
    return ""


def avisar_whatsapp(mensaje: str) -> bool:
    """WhatsApp SOLO a Ivan, via Railway (nunca directo a Meta)."""
    key = leer_admin_key()
    if not key:
        print("AVISO: no encontre ADMIN_API_KEY — no se envia el WhatsApp.")
        return False
    url = f"{RAILWAY_URL}/test-envio/{TELEFONO_IVAN}?msg={urllib.parse.quote(mensaje)}"
    req = urllib.request.Request(url, headers={"X-ADMIN-KEY": key})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            ok = b'"enviado":true' in r.read().replace(b" ", b"")
            print(f"WhatsApp a Ivan: {'enviado' if ok else 'FALLO'}")
            return ok
    except Exception as e:
        print(f"AVISO: no pude enviar el WhatsApp: {e}")
        return False


def main():
    print("=" * 50)
    print("  FOTOS FENIX — publicacion semanal")
    print("=" * 50)

    # Paso 1 — bandeja de entrada
    en_bandeja = [p for p in INBOX.iterdir() if p.is_file() and p.suffix.lower() in EXT_MEDIA] if INBOX.is_dir() else []
    print(f"\nBandeja: {len(en_bandeja)} archivos nuevos en {INBOX}")
    if en_bandeja:
        correr([sys.executable, "scripts/organizar_fotos_por_fecha.py", str(INBOX),
                "--destino", str(BASE_FOTOS)], cwd=REPO_WEB)

    # Paso 2 — optimizar y detectar si hay fotos nuevas
    salida = correr([sys.executable, "scripts/optimizar_fotos.py", str(BASE_FOTOS)], cwd=REPO_WEB)
    m = re.search(r"(\d+) fotos nuevas procesadas", salida)
    nuevas = int(m.group(1)) if m else 0
    if not nuevas:
        print("\nNo hay fotos nuevas para publicar. Nada que hacer.")
        return

    # Paso 2b — subir las fotos nuevas a R2 (las imagenes NO van a git, solo el CDN)
    archivos_nuevos = re.findall(r"-> (foto-\d+\.jpg)", salida)
    print(f"\nSubiendo {len(archivos_nuevos)} fotos nuevas a R2 (thumb + full)...")
    for n in archivos_nuevos:
        for carpeta in ("thumb", "full"):
            # --remote es OBLIGATORIO: sin eso wrangler escribe en un storage local
            # de simulacion y las fotos nunca llegan al bucket real
            correr([NPX, "wrangler", "r2", "object", "put", f"fenix-fotos/{carpeta}/{n}",
                    "--file", str(REPO_WEB / "fotos/assets" / carpeta / n),
                    "--content-type", "image/jpeg",
                    "--cache-control", "public, max-age=31536000, immutable",
                    "--remote"], cwd=REPO_WEB)

    # Paso 3 — commit + push (deploy automatico de Cloudflare Pages; solo texto,
    # thumb/ y full/ estan en .gitignore)
    correr(["git", "add", "fotos/assets"], cwd=REPO_WEB)
    correr(["git", "commit", "-m", f"feat(fotos): sumar {nuevas} fotos nuevas"], cwd=REPO_WEB)
    correr(["git", "push"], cwd=REPO_WEB)
    print("\nPush hecho — Cloudflare Pages deploya solo (~1 min).")

    # Paso 4 — tagueo de caras para los links familiares (incremental, con guard)
    try:
        correr([sys.executable, "scripts/taggear_fotos_web.py", "--aplicar", "--solo-incremental"],
               cwd=REPO_AGENT)
    except RuntimeError as e:
        print(f"AVISO: tagueo de caras no corrido ({e}). Las fotos publicas salieron igual.")

    # Paso 5 — verificar que la web ya sirva el total nuevo (edge cache puede demorar)
    total_web = 0
    for _ in range(12):
        try:
            with urllib.request.urlopen(f"{LINK_PAGINA}assets/photos.js?nc={int(time.time())}", timeout=15) as r:
                total_web = r.read().decode("utf-8", errors="replace").count("'foto-")
        except Exception:
            pass
        if total_web:
            break
        time.sleep(10)
    print(f"\nFotos en la web: {total_web}")

    # Paso 6 — WhatsApp a Ivan
    avisar_whatsapp(f"📸 Fotos Fenix actualizadas: {nuevas} fotos nuevas subidas. "
                    f"Ya se ven aca: {LINK_PAGINA}")

    print("\nLISTO.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
