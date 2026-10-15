# Ressources utilisées dans le projet d'origine

## Vidéos de référence à proposer à l'utilisateur (porte 0)
Proposer au moins ces deux exemples, demander les siennes, et **attendre ses liens** avant toute analyse :
- **Lovable** (post LinkedIn de Guillermo Flor, film de 50,8 s : mot géant, 17 coupes, interfaces grossies) :
  https://lnkd.in/p/etqPe48N (à ouvrir dans un navigateur connecté ; le téléchargement direct peut échouer).
- **Numtera** (ObiN Studio, 95 s : structure problème → solution, texte en frappe avec curseur, mot-clé surligné,
  voile coloré en bas) : https://www.youtube.com/watch?v=awUYikrGsKk
L'utilisateur peut en fournir d'autres (liens YouTube, LinkedIn, fichiers MP4). Pour chacune : porte 3.

## Skills HyperFrames (inclus, licence Apache-2.0, © HeyGen)
Dossier `skills/` : `hyperframes` (point d'entrée), `hyperframes-core` (contrat d'une composition : balises `data-*`,
pistes, sous-compositions, rendu déterministe), `hyperframes-animation` (GSAP, adaptateurs Lottie/Three/Anime/CSS,
motifs de texte), `hyperframes-audio`, `hyperframes-cli` (init, lint, check, preview, render, transcribe, tts…),
`hyperframes-creative` (palettes, typographie, narration, plan de scènes), `hyperframes-keyframes`, `motion-graphics`,
`general-video`, `product-launch-video`. Mises à jour : https://github.com/heygen-com/hyperframes (plugin Claude Code `hyperframes`).
Non inclus (lourds, optionnels) : `media-use`, `faceless-explainer`, `music-to-video`, `pr-to-video`, `slideshow`,
`talking-head-recut`, `remotion-to-hyperframes`, `figma`, `embedded-captions`, `hyperframes-studio`, `hyperframes-registry`.

## Outils de ce dépôt
- `outils/planche.py` : JSON → planche de storyboard (PNG) via Chrome headless.
- `outils/controle/` : `images.py` (extraire des images d'un rendu), `planche.py` (planche de contrôle), `mouvement.py`
  (vitesse px/i, zoom %/i, freinage, sauts de luminance ; limites sur les zooms et le texte, erreur n°12), `commun.py`.
  Issus d'un projet précis : lire leur `--help`, adapter chemins et formats.
- `outils/courbes.js` : table des courbes de mouvement (« rangement », « camera », « texte »…) enregistrées dans GSAP ;
  expose `window.LILIE` (`duree(images)`, `local(image, sequence)`) et lit `window.LILIE_TIMING` (fenêtres des séquences).
- `outils/audio/` : exemples de contrôle de voix, d'analyse et montage de musique, de mixage (voir `voix-elevenlabs.md`).
- `outils/brand.exemple.json` : modèle de design system.

## Outils externes
ElevenLabs (voix, via le connecteur Claude), Chrome (rendu d'images), ffmpeg (planches, mux audio), `yt-dlp`
(télécharger une référence), Node.js + `npx --yes hyperframes@0.8.91` (lint, check, preview, render), GSAP 3.14.2
(CDN jsdelivr), Python 3 + Pillow, bibliothèque musicale sous licence adaptée à la publicité (ex. Artlist).

## Commandes de référence
```bash
HF="npx --yes hyperframes@0.8.91"
$HF lint <projet>                                   # 0 erreur exigée
$HF check <projet> --at 12.4,18.9                   # un seul à la fois
$HF render <projet> --fps 25 --quality looks --output out.mp4
$HF render <projet> --fps 25 --quality delivery --video-bitrate 27M --output final.mp4
ffmpeg -i out.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -shortest film.mp4
yt-dlp --no-playlist -f "bv*[height<=1080]+ba/b" --merge-output-format mp4 -o ref.%(ext)s <url>
ffmpeg -i ref.mp4 -vf "fps=1,scale=360:-1,tile=6x8" -frames:v 2 planche-%d.jpg
```

## Polices et licences
Inter (SIL OFL 1.1) : libre. Police commerciale (ex. Neue Haas Grotesk) : non fournie, appelée via `local()` avec repli.
Musique : vérifier l'usage publicitaire payant. Voix synthétique : conditions du fournisseur (ElevenLabs).
