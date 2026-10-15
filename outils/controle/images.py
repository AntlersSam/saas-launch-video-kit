"""Outil (a) : extraire des images EXACTES à 25 i/s d'une fenêtre du film, depuis un rendu ou depuis le projet.

MODE D'EMPLOI (racine du projet, `python -I`) :
  # depuis un rendu MP4 (image n = n-ième image du fichier, comptée depuis 0) :
  python -I outils/controle/images.py --video work/renders/film-16x9.mp4 --de 462 --a 481 \
         --sortie work/<mission>/images-t3
  # depuis le projet, sans rendu (captures HyperFrames recalées sur la grille 25 i/s) :
  python -I outils/controle/images.py --projet film --images 444,449,455,462,470,477 \
         --sortie work/<mission>/r2-16x9
  python -I outils/controle/images.py --projet work/lovable-4x5-<mission> --de 462 --a 481 --pas 2 \
         --sortie work/<mission>/t3-4x5
Sortie : un fichier par image, `iNNNN.png` (numéro d'image du FILM), plus `images.json` (liste, source, temps).
Les outils `mouvement.py` et `planche.py` lisent ce dossier.

Pourquoi le mode --projet copie le projet : `hyperframes snapshot` cale ses captures sur une grille à 30 i/s
(runtime 0.8.91, `quantizeTimeToFrame` avec la cadence par défaut 30 : la capture demandée à 0,04 s montre
l'image de 0,0333 s). L'outil fait une copie jetable du projet (dans le dossier de sortie, jamais dans
film/) et y ajoute, en tête du <head> de index.html, la consigne de cadence que le moteur de rendu pose
lui-même (`--fps 25`) : les captures tombent alors exactement sur n / 25 s (vérifié : objet à 1000 px/s →
40, 80, 120, 160 px aux images 1 à 4, au lieu de 33, 67, 100, 133). Plusieurs agents peuvent lancer l'outil en
même temps s'ils ont des dossiers de sortie différents (la copie porte le numéro du processus).
Limites : les captures HyperFrames ne font ni flou de mouvement ni compression ; pour juger le rendu final
(débit, bandes), extraire depuis le MP4.
"""
import argparse
import re
import shutil
import subprocess
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as c  # noqa: E402

EXCLUS = {"renders", "snapshots", ".hyperframes", "node_modules", ".git"}
CONSIGNE_25 = ('<script>/* outils/images.py : captures sur la grille 25 i/s (sonde jetable, jamais dans film) */'
               'window["__HF_EXPORT_" + "RENDER_SEEK_CONFIG"] = { fps: 25, fpsSource: "render-options", owner: "runtime" };'
               '</script>')


def plages(images):
    """[1,2,3,7,8] → [(1,3),(7,8)]"""
    out = []
    for n in images:
        if out and n == out[-1][1] + 1:
            out[-1] = (out[-1][0], n)
        else:
            out.append((n, n))
    return out


def depuis_video(video, images, sortie):
    info = c.ffprobe(video)
    if abs(info["fps"] - c.FPS) > 1e-6:
        print(f"ATTENTION : {video.name} est à {info['fps']:.3f} i/s, pas à 25 : les numéros d'image ne sont pas ceux du film")
    if info["images"] and images[-1] >= info["images"]:
        raise SystemExit(f"image {images[-1]} demandée, la vidéo n'en a que {info['images']} (0 à {info['images'] - 1})")
    expr = "+".join(f"between(n\\,{a}\\,{b})" for a, b in plages(images))
    tmp = sortie / f".brut-{os.getpid()}"
    tmp.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", f"select='{expr}'", "-fps_mode", "passthrough",
           str(tmp / "x%06d.png")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("ffmpeg : " + r.stderr[-800:])
    brutes = sorted(tmp.glob("x*.png"))
    if len(brutes) != len(images):
        raise SystemExit(f"ffmpeg a sorti {len(brutes)} images pour {len(images)} demandées")
    for n, f in zip(images, brutes):
        f.replace(sortie / c.nom_image(n))
    shutil.rmtree(tmp, ignore_errors=True)
    return {"source": "video", "video": str(video), "video_info": info}


def copier_projet(src, dst):
    def ignore(d, noms):
        return [n for n in noms if n in EXCLUS or n.startswith(".brut-") or n.startswith(".sonde-")]
    shutil.copytree(src, dst, ignore=ignore)
    idx = dst / "index.html"
    html = idx.read_text(encoding="utf-8")
    m = re.search(r"<head[^>]*>", html, re.I)
    if not m:
        raise SystemExit(f"{idx} : pas de <head>")
    idx.write_text(html[:m.end()] + "\n    " + CONSIGNE_25 + html[m.end():], encoding="utf-8")


def depuis_projet(projet, images, sortie, timeout, garder):
    if not (projet / "index.html").exists():
        raise SystemExit(f"{projet} n'est pas un projet HyperFrames (pas de index.html)")
    sonde = sortie / f".sonde-{os.getpid()}"
    brut = sortie / f".brut-{os.getpid()}"
    shutil.rmtree(sonde, ignore_errors=True)
    copier_projet(projet, sonde)
    temps = [f"{n / c.FPS:.6f}".rstrip("0").rstrip(".") for n in images]
    code, sortie_txt = c.hyperframes("snapshot", sonde, "--at", ",".join(temps), "--no-end", "-o", brut,
                                     "--timeout", timeout, "--describe", "false")
    fichiers = {}
    for f in brut.glob("frame-*.png") if brut.exists() else []:
        m = re.match(r"frame-(\d+)-at-", f.name)
        if m:
            fichiers[int(m.group(1))] = f
    if code or len(fichiers) != len(images):
        print(sortie_txt[-2000:])
        raise SystemExit(f"snapshot : {len(fichiers)} captures pour {len(images)} demandées (code {code})")
    for k, n in enumerate(images):
        fichiers[k].replace(sortie / c.nom_image(n))
    shutil.rmtree(brut, ignore_errors=True)
    if not garder:
        shutil.rmtree(sonde, ignore_errors=True)
    avert = [li.strip() for li in sortie_txt.splitlines() if "⚠" in li or "rror" in li]
    return {"source": "projet", "projet": str(projet), "temps_s": temps, "avertissements": avert,
            "sonde": str(sonde) if garder else None}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", help="rendu MP4 à 25 i/s")
    src.add_argument("--projet", help="dossier du projet HyperFrames (film ou une copie 4:5)")
    ap.add_argument("--images", help="liste d'images du film : 462-480,500,510-520:2")
    ap.add_argument("--de", type=int, help="première image (incluse)")
    ap.add_argument("--a", type=int, help="dernière image (incluse)")
    ap.add_argument("--pas", type=int, default=1, help="une image sur N entre --de et --a (défaut 1)")
    ap.add_argument("--sortie", required=True, help="dossier de sortie (ex. work/<mission>/images)")
    ap.add_argument("--timeout", default="15000", help="ms d'attente du runtime pour snapshot (défaut 15000)")
    ap.add_argument("--garder-sonde", action="store_true", help="garder la copie jetable du projet (débogage)")
    a = ap.parse_args()
    images = c.liste_images(a.images, a.de, a.a, a.pas)
    if images[-1] > 1187 and a.projet:
        raise SystemExit("le film a 1188 images (0 à 1187)")
    sortie = c.chemin(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    if a.video:
        meta = depuis_video(c.chemin(a.video), images, sortie)
    else:
        meta = depuis_projet(c.chemin(a.projet), images, sortie, a.timeout, a.garder_sonde)
    meta["images"] = images
    c.ecrire_json(sortie / "images.json", meta)
    print(f"{len(images)} images exactes à 25 i/s (i{images[0]} → i{images[-1]}) dans {sortie}")
    for w in meta.get("avertissements", []):
        print("  " + w)


if __name__ == "__main__":
    main()
