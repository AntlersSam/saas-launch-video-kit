"""Outil (b) : mesurer le mouvement image par image dans une région (vitesse px/i, zoom %/i, freinage, sauts de
luminance, netteté), et le comparer à la courbe prévue par le storyboard.

MODE D'EMPLOI (racine du projet, `python -I`) :
  # sur des images extraites par images.py (dossier de iNNNN.png) :
  python -I outils/controle/mouvement.py --images work/<mission>/images-t3 --zone 0,0,1920,1080
  # directement sur un rendu, fenêtre i462 → i481 :
  python -I outils/controle/mouvement.py --video work/renders/film-16x9.mp4 --de 462 --a 481 \
         --zone 1100,0,820,300
  # comparer à un geste du storyboard (courbe:début:durée:distance en px) :
  python -I outils/controle/mouvement.py --images … --zone … --attendu camera:445:36:1078
Options : --objet clair|sombre (pixels suivis : plus clairs / plus sombres que --seuil, 0-255, défaut clair 128) ;
          --format 16x9|4x5 (sinon déduit de la largeur des images) ; --json fichier (défaut <images>/mouvement.json).
Colonnes : lum = luminance moyenne de la zone (0-255) ; saut = écart avec l'image précédente (règle : ≤ 25) ;
  v = vitesse du centre de l'objet suivi (px/i, divisée par l'écart d'images si --pas > 1) ; vx, vy = translation
  de tout le contenu de la zone (corrélation de phase, utile pour un panoramique ou un défilement) ; zoom = variation
  de taille de la boîte de l'objet (%/i ; règle ≤ 8 %/i, ≤ 4,1 %/i pour un héros) ; net = netteté (chute = flou).
Résumé : pic de vitesse, images au-dessus de 45 px/i (38 en 4:5) qui demandent un flou, au-dessus de 90 (interdit),
  freinage = images entre le dernier pic et l'arrêt (règle : ≥ 12), sauts de luminance > 25, zoom maximal.
Réutilise les courbes exactes de scripts/lovable/realisation_v2_outils.py et le principe de scripts/motion.py.
"""
import argparse
import math
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import commun as c  # noqa: E402

LIMITES = {"16x9": {"nette": 45, "max": 90}, "4x5": {"nette": 38, "max": 90}}


def charger_images(dossier, zone):
    imgs = c.images_du_dossier(dossier)
    nums = sorted(imgs)
    import numpy as np
    from PIL import Image
    w, h = Image.open(imgs[nums[0]]).size
    return nums, np.stack([c.lire_gris(imgs[n], zone) for n in nums]), (w, h)


def charger_video(video, de, a, zone):
    import numpy as np
    info = c.ffprobe(video)
    W, H = info["largeur"], info["hauteur"]
    x, y, w, h = zone or (0, 0, W, H)
    vf = f"select='between(n\\,{de}\\,{a})',crop={w}:{h}:{x}:{y},format=gray"
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", vf, "-fps_mode", "passthrough",
                        "-f", "rawvideo", "-"], capture_output=True)
    if r.returncode:
        raise SystemExit("ffmpeg : " + r.stderr.decode(errors="replace")[-600:])
    f = np.frombuffer(r.stdout, dtype=np.uint8).astype(np.float32)
    n = f.size // (w * h)
    if n != a - de + 1:
        raise SystemExit(f"{n} images lues pour {a - de + 1} demandées")
    return list(range(de, a + 1)), f.reshape(n, h, w), (W, H)


def correlation_phase(a, b):
    """Translation (dx, dy) qui amène a sur b (px, sous-pixel par parabole)."""
    import numpy as np
    hy = np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    A = np.fft.fft2((a - a.mean()) * hy)
    B = np.fft.fft2((b - b.mean()) * hy)
    R = B * np.conj(A)
    R /= np.abs(R) + 1e-9
    r = np.fft.ifft2(R).real
    py, px = np.unravel_index(np.argmax(r), r.shape)

    def fin(c0, cm, cp):
        d = cm - 2 * c0 + cp
        return 0.0 if abs(d) < 1e-12 else 0.5 * (cm - cp) / d
    H, W = r.shape
    dy = py + fin(r[py, px], r[(py - 1) % H, px], r[(py + 1) % H, px])
    dx = px + fin(r[py, px], r[py, (px - 1) % W], r[py, (px + 1) % W])
    if dy > H / 2:
        dy -= H
    if dx > W / 2:
        dx -= W
    return float(dx), float(dy), float(r.max())


def mesurer(nums, f, zone, objet, seuil):
    import numpy as np
    ox, oy = (zone[0], zone[1]) if zone else (0, 0)
    H, W = f.shape[1:]
    yy, xx = np.mgrid[0:H, 0:W]
    lignes = []
    prec = None
    for k, n in enumerate(nums):
        g = f[k]
        m = g > seuil if objet == "clair" else g < seuil
        aire = int(m.sum())
        if aire:
            cx, cy = float(xx[m].mean()) + ox, float(yy[m].mean()) + oy
            ys, xs = np.where(m)
            boite = [int(xs.min()) + ox, int(ys.min()) + oy, int(xs.max()) + ox + 1, int(ys.max()) + oy + 1]
        else:
            cx = cy = None
            boite = None
        lap = float(np.abs(g[1:-1, 1:-1] * 4 - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]).mean())
        li = {"image": n, "lum": round(float(g.mean()), 2), "aire": aire, "cx": cx, "cy": cy, "boite": boite,
              "net": round(lap, 2)}
        if prec is not None:
            dn = n - prec["image"]
            p = f[k - 1]
            li["saut"] = round(abs(li["lum"] - prec["lum"]), 2)
            li["diff"] = round(float(np.abs(g - p).mean()), 2)
            dx, dy, pic = correlation_phase(p, g)
            li["vx"], li["vy"] = round(dx / dn, 2), round(dy / dn, 2)
            if cx is not None and prec["cx"] is not None:
                li["v"] = round(math.hypot(cx - prec["cx"], cy - prec["cy"]) / dn, 2)
            if boite and prec["boite"]:
                w0, h0 = prec["boite"][2] - prec["boite"][0], prec["boite"][3] - prec["boite"][1]
                w1, h1 = boite[2] - boite[0], boite[3] - boite[1]
                if w0 > 4 and h0 > 4:
                    li["zoom"] = round((math.sqrt((w1 * h1) / (w0 * h0)) ** (1 / dn) - 1) * 100, 2)
        lignes.append(li)
        prec = li
    return lignes


def attendu(spec, nums):
    import realisation_v2_outils as o
    courbe, debut, duree, dist = spec.split(":")
    debut, duree, dist = int(debut), int(duree), float(dist)
    if courbe not in o.COURBES:
        raise SystemExit(f"courbe inconnue {courbe} ({', '.join(o.COURBES)})")
    out = {}
    for i, n in enumerate(nums[1:], 1):
        dn = n - nums[i - 1]
        out[n] = abs(dist) * (o.prog(courbe, debut, duree, n) - o.prog(courbe, debut, duree, n - dn)) / dn
    return out, {"courbe": courbe, "debut": debut, "duree": duree, "distance": dist,
                 "freinage_theorique": o.deceleration(courbe, duree)}


def resume(lignes, fmt):
    lim = LIMITES[fmt]
    vit = [(li["image"], li.get("v")) for li in lignes if li.get("v") is not None]
    pan = [(li["image"], math.hypot(li["vx"], li["vy"])) for li in lignes if "vx" in li]
    r = {"format": fmt, "limites": lim}
    for nom, serie in (("objet", vit), ("contenu", pan)):
        if not serie:
            continue
        vmax = max(v for _, v in serie)
        ipic = max(serie, key=lambda t: t[1])[0]
        apres = [(n, v) for n, v in serie if n > ipic]
        arret = next((n for n, v in apres if v <= 0.5), None)  # arrêt : moins d'un demi-pixel par image
        r[nom] = {"vitesse_max": round(vmax, 2), "image_du_pic": ipic,
                  "freinage_images": (arret - ipic) if arret is not None else None,
                  "au_dessus_nette": [n for n, v in serie if v > lim["nette"]],
                  "au_dessus_max": [n for n, v in serie if v > lim["max"]]}
    zooms = [(li["image"], li["zoom"]) for li in lignes if "zoom" in li]
    if zooms:
        z = max(zooms, key=lambda t: abs(t[1]))
        r["zoom_max_pct_par_image"] = {"valeur": z[1], "image": z[0]}
    r["sauts_luminance_sup_25"] = [li["image"] for li in lignes if li.get("saut", 0) > 25]
    r["saut_max"] = max((li.get("saut", 0) for li in lignes), default=0)
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--images", help="dossier de iNNNN.png (sortie de images.py)")
    src.add_argument("--video", help="rendu MP4 à 25 i/s (avec --de et --a)")
    ap.add_argument("--de", type=int)
    ap.add_argument("--a", type=int)
    ap.add_argument("--zone", help="x,y,largeur,hauteur en px du cadre (défaut : cadre entier)")
    ap.add_argument("--objet", choices=["clair", "sombre"], default="clair")
    ap.add_argument("--seuil", type=float, default=128.0)
    ap.add_argument("--format", choices=["16x9", "4x5"])
    ap.add_argument("--attendu", help="courbe:début:durée:distance (ex. camera:445:36:1078)")
    ap.add_argument("--json", help="fichier JSON de sortie")
    a = ap.parse_args()
    z = c.zone(a.zone)
    if a.images:
        nums, f, (W, H) = charger_images(a.images, z)
        dest = c.chemin(a.json) if a.json else c.chemin(a.images) / "mouvement.json"
    else:
        if a.de is None or a.a is None:
            raise SystemExit("--video demande --de et --a")
        nums, f, (W, H) = charger_video(c.chemin(a.video), a.de, a.a, z)
        dest = c.chemin(a.json) if a.json else c.chemin(a.video).with_suffix(f".mouvement-{a.de}-{a.a}.json")
    fmt = a.format or ("4x5" if H > W else "16x9")
    lignes = mesurer(nums, f, z, a.objet, a.seuil)
    att, att_info = attendu(a.attendu, nums) if a.attendu else ({}, None)
    print(f"zone {z or 'cadre entier'} · objet {a.objet} (seuil {a.seuil:.0f}) · format {fmt}")
    print(" image   lum  saut      v   prévu     vx     vy   zoom%    net   centre")
    for li in lignes:
        n = li["image"]
        cen = f"({li['cx']:.0f}, {li['cy']:.0f})" if li["cx"] is not None else "—"

        def col(k, w, fmt_="{:.1f}"):
            return (fmt_.format(li[k]) if li.get(k) is not None else "—").rjust(w)
        prevu = f"{att[n]:.1f}".rjust(7) if n in att else "—".rjust(7)
        if n in att:
            li["prevu"] = round(att[n], 2)
        print(f"{n:6d} {li['lum']:5.1f} {col('saut', 5)} {col('v', 6)} {prevu} {col('vx', 6)} {col('vy', 6)} "
              f"{col('zoom', 6, '{:+.2f}')} {li['net']:6.1f}   {cen}")
    r = resume(lignes, fmt)
    print("Résumé :")
    for k in ("objet", "contenu"):
        if k in r:
            s = r[k]
            print(f"  {k:7s} pic {s['vitesse_max']} px/i à i{s['image_du_pic']} ; freinage {s['freinage_images']} i "
                  f"(≥ 12) ; > {r['limites']['nette']} px/i : {s['au_dessus_nette'] or 'aucune'} ; "
                  f"> 90 px/i : {s['au_dessus_max'] or 'aucune'}")
    if "zoom_max_pct_par_image" in r:
        print(f"  zoom max {r['zoom_max_pct_par_image']['valeur']:+.2f} %/i à i{r['zoom_max_pct_par_image']['image']} (≤ 8 ; héros ≤ 4,1)")
    print(f"  saut de luminance max {r['saut_max']} (≤ 25) ; images > 25 : {r['sauts_luminance_sup_25'] or 'aucune'}")
    if att_info:
        print(f"  prévu : {att_info['courbe']} {att_info['duree']} i dès i{att_info['debut']} sur {att_info['distance']:.0f} px "
              f"(freinage théorique {att_info['freinage_theorique']} i)")
    c.ecrire_json(dest, {"zone": z, "objet": a.objet, "seuil": a.seuil, "attendu": att_info, "resume": r, "images": lignes})
    print(f"→ {dest}")


if __name__ == "__main__":
    main()
