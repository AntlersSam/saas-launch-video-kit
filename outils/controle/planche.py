"""Outil (c) : planche contact numérotée (une vignette par image, numéro d'image du film et temps sous chacune).

MODE D'EMPLOI (racine du projet, `python -I`) :
  python -I outils/controle/planche.py --images work/<mission>/images-t3
  python -I outils/controle/planche.py --images work/<mission>/images-t3 --choix 444-481:3 \
         --zone 800,0,1120,600 --colonnes 5 --largeur 360 --titre "T3 16:9" --sortie work/<mission>/t3.jpg
Entrée : un dossier de iNNNN.png (sortie de images.py). Options : --choix (sous-ensemble « 462-480,500 »),
  --zone x,y,largeur,hauteur (recadrage en px du cadre, avant réduction), --colonnes (défaut 6),
  --largeur (px d'une vignette, défaut 320), --reperes 462,477 (vignettes encadrées : images de passage, temps forts),
  --titre, --sortie (défaut <images>/planche.jpg).
"""
import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun as c  # noqa: E402

FOND = (40, 40, 40)          # gris neutre : les cadres sombres du film restent lisibles
TEXTE = (235, 235, 235)
REPERE = (122, 41, 255)      # violet de la charte, pour encadrer les images de passage
POLICE = c.ROOT / "film" / "screens" / "fonts" / "Inter-Medium.ttf"


def main():
    from PIL import Image, ImageDraw, ImageFont
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", required=True, help="dossier de iNNNN.png")
    ap.add_argument("--choix", help="sous-ensemble d'images : 462-480,500,510-520:2")
    ap.add_argument("--zone", help="recadrage x,y,largeur,hauteur (px du cadre)")
    ap.add_argument("--colonnes", type=int, default=6)
    ap.add_argument("--largeur", type=int, default=320)
    ap.add_argument("--reperes", help="images à encadrer : 462,477")
    ap.add_argument("--titre", default="")
    ap.add_argument("--sortie")
    a = ap.parse_args()
    dispo = c.images_du_dossier(a.images)
    nums = [n for n in (c.liste_images(a.choix) if a.choix else sorted(dispo)) if n in dispo]
    if not nums:
        raise SystemExit("aucune image à mettre sur la planche")
    reperes = set(c.liste_images(a.reperes)) if a.reperes else set()
    z = c.zone(a.zone)
    vignettes = []
    for n in nums:
        im = Image.open(dispo[n]).convert("RGB")
        if z:
            im = im.crop((z[0], z[1], z[0] + z[2], z[1] + z[3]))
        h = round(im.height * a.largeur / im.width)
        vignettes.append((n, im.resize((a.largeur, h), Image.LANCZOS)))
    try:
        f = ImageFont.truetype(str(POLICE), max(14, a.largeur // 16))
        ft = ImageFont.truetype(str(POLICE), max(18, a.largeur // 12))
    except OSError:
        f = ft = ImageFont.load_default()
    vh = max(v.height for _, v in vignettes)
    lab = f.size + 12
    marge, ecart = 16, 10
    haut_titre = ft.size + 20 if a.titre else 0
    col = max(1, min(a.colonnes, len(vignettes)))
    lig = math.ceil(len(vignettes) / col)
    W = marge * 2 + col * a.largeur + (col - 1) * ecart
    H = marge * 2 + haut_titre + lig * (vh + lab) + (lig - 1) * ecart
    out = Image.new("RGB", (W, H), FOND)
    d = ImageDraw.Draw(out)
    if a.titre:
        d.text((marge, marge), a.titre, font=ft, fill=TEXTE)
    for k, (n, v) in enumerate(vignettes):
        x = marge + (k % col) * (a.largeur + ecart)
        y = marge + haut_titre + (k // col) * (vh + lab + ecart)
        out.paste(v, (x, y))
        if n in reperes:
            d.rectangle((x - 3, y - 3, x + v.width + 2, y + v.height + 2), outline=REPERE, width=3)
        d.text((x, y + v.height + 4), f"i{n} · {n / c.FPS:.2f} s".replace(".", ","), font=f, fill=TEXTE)
    dest = c.chemin(a.sortie) if a.sortie else c.chemin(a.images) / "planche.jpg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest, quality=90)
    print(f"planche de {len(vignettes)} images ({col} × {lig}) → {dest}")


if __name__ == "__main__":
    main()
