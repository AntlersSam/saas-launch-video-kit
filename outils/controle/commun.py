"""Boîte à outils commune des missions Lovable (outils/controle/) : fonctions partagées.

Ce module ne s'exécute pas seul. Les outils l'importent après avoir ajouté leur dossier au chemin
(`python -I` retire le dossier du script de sys.path) :
    sys.path.insert(0, str(Path(__file__).resolve().parent)); import commun as c

Contenu : chemins du projet, FPS = 25, lecture d'une liste d'images (« 462-480,500,510-520:2 »), noms de fichiers
d'image (`i0462.png`), lecture d'un dossier d'images en niveaux de gris (numpy), sonde ffprobe, commande npx.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FPS = 25
HF_VERSION = "hyperframes@0.8.91"
NOM_IMAGE = re.compile(r"^i(\d{4,5})\.png$")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def chemin(p):
    """Chemin absolu ; un chemin relatif est pris depuis la racine du projet (comme les commandes du brief)."""
    p = Path(p)
    return p if p.is_absolute() else (ROOT / p)


def nom_image(n):
    return f"i{n:04d}.png"


def liste_images(spec=None, de=None, a=None, pas=1):
    """« 462-480,500,510-520:2 » ou --de/--a/--pas → liste triée d'images (entiers, sans doublon)."""
    res = set()
    if spec:
        for part in str(spec).split(","):
            part = part.strip()
            if not part:
                continue
            m = re.fullmatch(r"(\d+)(?:-(\d+))?(?::(\d+))?", part)
            if not m:
                raise SystemExit(f"liste d'images illisible : « {part} » (ex. 462-480,500,510-520:2)")
            d, f, p = int(m.group(1)), int(m.group(2) or m.group(1)), int(m.group(3) or 1)
            res.update(range(d, f + 1, p))
    if de is not None:
        res.update(range(de, (a if a is not None else de) + 1, max(1, pas)))
    if not res:
        raise SystemExit("aucune image demandée (--images ou --de/--a)")
    return sorted(res)


def images_du_dossier(dossier):
    """{numéro d'image: chemin} pour les fichiers iNNNN.png d'un dossier."""
    d = chemin(dossier)
    out = {}
    for f in sorted(d.iterdir()):
        m = NOM_IMAGE.match(f.name)
        if m:
            out[int(m.group(1))] = f
    if not out:
        raise SystemExit(f"aucune image iNNNN.png dans {d}")
    return out


def lire_gris(f, zone=None):
    """Image en luminance 0-255 (float32, Rec. 709 sur sRGB non linéarisé, comme ffmpeg format=gray), zone x,y,w,h."""
    import numpy as np
    from PIL import Image
    im = Image.open(f).convert("RGB")
    if zone:
        x, y, w, h = zone
        im = im.crop((x, y, x + w, y + h))
    a = np.asarray(im, dtype=np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def zone(spec):
    if not spec:
        return None
    v = [int(round(float(t))) for t in spec.replace(" ", "").split(",")]
    if len(v) != 4 or v[2] <= 0 or v[3] <= 0:
        raise SystemExit("--zone attend x,y,largeur,hauteur (px du cadre)")
    return tuple(v)


def ffprobe(video):
    exe = shutil.which("ffprobe")
    if not exe:
        raise SystemExit("ffprobe introuvable dans le PATH")
    r = subprocess.run([exe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate,nb_frames", "-of", "json", str(video)],
                       capture_output=True, text=True)
    s = json.loads(r.stdout)["streams"][0]
    num, den = (int(x) for x in s["r_frame_rate"].split("/"))
    return {"largeur": s["width"], "hauteur": s["height"], "fps": num / den,
            "images": int(s.get("nb_frames") or 0)}


def npx():
    exe = shutil.which("npx") or shutil.which("npx.cmd")
    if not exe:
        raise SystemExit("npx introuvable dans le PATH")
    return exe


def hyperframes(*args, capture=True, timeout=900):
    """Lance `npx --yes hyperframes@0.8.91 <args>` ; renvoie (code, sortie)."""
    r = subprocess.run([npx(), "--yes", HF_VERSION, *map(str, args)], capture_output=capture, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def ecrire_json(f, data):
    f = chemin(f)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return f
