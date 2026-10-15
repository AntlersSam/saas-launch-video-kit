"""Planche de storyboard : JSON -> HTML -> PNG (Chrome headless).

Usage :  python -I outils/planche.py storyboard.json [sortie.png]

storyboard.json :
{
  "titre": "Planche 1 · Le problème · 0 à 15 s",
  "marque": {"fond": "#FFFFFF", "accent": "#7A29FF", "encre": "#0A0A0F"},   (voir brand.exemple.json)
  "images": [
    {"t": "0,0 s", "voix": "Des scores calculés à la main.",
     "html": "<div class='phrase'>Des scores<span class='cur'></span></div>",
     "note": "Le texte s'écrit lettre par lettre ; curseur d'accent."}
  ]
}

`html` = le contenu de l'image clé, dessiné dans un cadre 1920 x 1080 (réduit au tiers). Classes
utilisables : .phrase (phrase centrée), .k (mot en couleur d'accent), .hl (mot surligné),
.cur (curseur), .logo (grand logo texte). Pour un écran produit : <img src="file:///.../ecran.png">
ou un bloc HTML positionné en absolu. 3 colonnes par ligne.
"""
import json
import subprocess
import sys
from pathlib import Path

CHROMES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]

CSS = """
:root { --fond: %(fond)s; --accent: %(accent)s; --encre: %(encre)s; }
* { box-sizing: border-box; }
html, body { margin: 0; background: #F3F4F6; font-family: Inter, system-ui, sans-serif; color: var(--encre); }
.planche { width: 2070px; padding: 36px 35px 40px; }
h1 { font: 600 34px Inter, sans-serif; margin: 0 0 24px; }
.grille { display: grid; grid-template-columns: repeat(3, 640px); gap: 30px 25px; }
.cadre { width: 640px; height: 360px; overflow: hidden; border-radius: 10px; position: relative;
         box-shadow: 0 1px 3px rgba(0,0,0,.08), 0 0 0 1px rgba(0,0,0,.05); }
.image { position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; transform: scale(.3333); transform-origin: 0 0;
         background: var(--fond); overflow: hidden; }
.tc { display: flex; gap: 12px; margin-top: 12px; align-items: baseline; }
.tc .t { font: 600 18px Inter, sans-serif; color: var(--accent); white-space: nowrap; }
.tc .v { font: italic 400 18px Inter, sans-serif; }
.note { font: 400 16px/1.45 Inter, sans-serif; color: #374151; margin-top: 6px; }
.phrase { position: absolute; left: 0; right: 0; top: 50%%; transform: translateY(-50%%); text-align: center;
          font: 600 100px/1.12 Inter, sans-serif; letter-spacing: -0.025em; }
.k { color: var(--accent); }
.hl { background: var(--accent); color: #fff; border-radius: 10px; padding: 0 .12em; }
.cur { display: inline-block; width: .06em; height: .9em; background: var(--accent); vertical-align: -.08em; margin-left: .04em; }
.logo { position: absolute; left: 0; right: 0; top: 360px; text-align: center; font: 700 300px/1 Inter, sans-serif;
        letter-spacing: -0.04em; color: var(--accent); }
"""


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1])
    data = json.loads(src.read_text(encoding="utf-8"))
    sortie = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".png")
    marque = {"fond": "#FFFFFF", "accent": "#7A29FF", "encre": "#0A0A0F", **data.get("marque", {})}
    cases = []
    for im in data["images"]:
        voix = f"« {im['voix']} »" if im.get("voix") else ""
        cases.append(
            f'<div><div class="cadre"><div class="image">{im["html"]}</div></div>'
            f'<div class="tc"><span class="t">{im["t"]}</span><span class="v">{voix}</span></div>'
            f'<div class="note">{im.get("note", "")}</div></div>'
        )
    html = (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><style>{CSS % marque}</style></head>'
            f'<body><div class="planche"><h1>{data["titre"]}</h1><div class="grille">{"".join(cases)}</div></div></body></html>')
    page = sortie.with_suffix(".html")
    page.write_text(html, encoding="utf-8")
    chrome = next((c for c in CHROMES if Path(c).exists()), None)
    if not chrome:
        sys.exit("Chrome introuvable : installez Chrome ou ajoutez son chemin dans CHROMES.")
    rangs = -(-len(data["images"]) // 3)
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                    f"--window-size=2070,{110 + rangs * 520}", f"--screenshot={sortie}", "--virtual-time-budget=3000",
                    page.resolve().as_uri()], check=True, capture_output=True)
    print(sortie)


if __name__ == "__main__":
    main()
