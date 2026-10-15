# Kit « vidéo motion de lancement SaaS »

Un prompt et un skill pour faire avec Claude Code une vidéo motion de lancement de produit SaaS
(30 à 60 s, voix off, musique, vrais écrans du produit animés). Méthode issue d'un vrai projet
(film de lancement de Lilie, Hey Lilie, octobre 2026) : storyboard en planches validé **avant**
d'animer, mouvements doux, rendu HTML → MP4.

## Ce que vous obtenez

| Fichier | Rôle |
|---|---|
| `PROMPT-DEMARRAGE.md` | Le prompt à coller dans Claude Code pour démarrer. Il pose les bonnes questions puis déroule la méthode. |
| `skills/saas-launch-video/` | Le skill (méthode en 6 étapes + 3 références : grammaire de mouvement, leçons apprises, brief d'agent animateur). |
| `outils/planche.py` | Génère une planche de storyboard (images clés + texte + note) en PNG à partir d'un fichier JSON. |
| `outils/brand.exemple.json` | Charte à remplir (couleurs, polices, ton) : sert de source unique au storyboard et à l'animation. |

## Installation (10 minutes)

1. **Claude Code** installé (VS Code ou terminal).
2. **Chrome** et **ffmpeg** installés (Chrome fabrique les images, ffmpeg assemble le son et la vidéo).
3. **Node.js** installé ; le moteur de rendu se lance tout seul : `npx --yes hyperframes@0.8.91 --help`.
4. Copier le dossier `skills/saas-launch-video/` dans `~/.claude/skills/` (Windows :
   `C:\Users\<vous>\.claude\skills\`).
5. Recommandé : installer aussi les skills HyperFrames de Claude Code (`/plugin`, cherchez « hyperframes ») :
   ils décrivent le format des compositions animées (balises `data-*`, timeline GSAP).
6. Créer un dossier vide pour votre vidéo, l'ouvrir dans Claude Code, coller `PROMPT-DEMARRAGE.md`.

## Ce qu'il vous faut préparer

- Le **script** (texte de la voix) et la **voix** (enregistrée ou synthétique, un fichier par phrase).
- La **musique** : vérifiez la licence pour la publicité payante avant de diffuser.
- Les **écrans du produit** : idéalement redessinés en HTML/CSS depuis votre code (net, animable),
  sinon des captures propres.
- Votre **charte** (`outils/brand.exemple.json`).

## Coûts et économie (important)

La méthode est pensée pour dépenser peu : le gros du coût est l'animation, et on ne la lance
qu'après validation du storyboard. Réglages recommandés : session principale en effort
`medium`, agents animateurs en Sonnet `medium`, pas plus de 3 agents en parallèle, une seule
planche de contrôle par transition. Voir `references/lecons.md`.

## Limites

- Les polices commerciales, la musique et les voix ne sont **pas** fournies.
- Testé sur Windows 11 ; les commandes fonctionnent aussi sur macOS/Linux (chemins à adapter).
- Pas de garantie sur la version du moteur de rendu : le kit fixe `hyperframes@0.8.91`.
