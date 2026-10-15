---
name: saas-launch-video
description: Réaliser une vidéo motion de lancement de produit SaaS (30 à 60 s, voix off, musique, vrais écrans animés) avec storyboard en planches validé avant animation, mouvements doux et rendu HTML vers MP4 (HyperFrames + GSAP). À utiliser dès qu'on parle de vidéo de lancement, film produit, motion design SaaS, « launch video », storyboard vidéo, animer des écrans de produit, ou de refaire une vidéo comme une référence (Lovable, Numtera, etc.).
---

# Vidéo motion de lancement SaaS

Méthode en 6 étapes. **On ne passe à l'étape suivante qu'avec l'accord explicite de l'utilisateur**
aux étapes 1, 3 et 5. L'animation (étape 4) est l'étape coûteuse : elle ne démarre qu'après
validation du storyboard.

Références à lire au moment voulu (pas avant, pour économiser du contexte) :
- `references/grammaire-mouvement.md` : règles de mouvement, courbes, animations de texte, transitions.
- `references/brief-agent-animateur.md` : gabarit de brief pour les agents qui animent.
- `references/lecons.md` : erreurs déjà commises, à ne pas refaire.

## Étape 1. Brief (validation utilisateur)

Collecter en une seule question groupée ce qui manque : produit et public ; script de la voix
phrase par phrase ; format (16:9, 4:5, 9:16) et durée ; charte (voir `outils/brand.exemple.json`) ;
voix, musique et écrans fournis ou non ; vidéo de référence.
Rendre un **brief de 10 lignes** : structure (problème → solution → démo → preuve → appel),
ton, charte, contraintes légales (allégations, licences musique/police). Attendre le « ok ».

## Étape 2. Référence et structure

Si l'utilisateur donne une vidéo de référence : la télécharger (`yt-dlp`), sortir une planche
(`ffmpeg -vf "fps=1,scale=360:-1,tile=6x8"`) et lire 2 planches. En tirer : la structure
(combien de secondes de problème, de solution, de démo), le rythme (unité de temps médiane),
les animations de texte, le rôle de la couleur. **Ne pas copier la charte de la référence**
(couleurs, police) : copier la grammaire, pas l'habillage.

Structure par défaut d'un film de lancement de 45 s :
1. Problème (≈ 10 s) : 4 à 5 phrases courtes, une par douleur, texte au centre.
2. Bascule (≈ 1 s de silence) puis mot géant : la promesse.
3. Solution (≈ 5 s) : phrase de promesse, puis le logo.
4. Démo (≈ 22 s) : 3 à 4 écrans du produit, un par bénéfice.
5. Preuve (≈ 3 s) : une phrase forte.
6. Carton final fixe (≈ 5 s) : logo, statut (« bientôt disponible »), appel à l'action.

Caler chaque phrase sur la voix : placer l'affichage 3 à 7 images avant le mot prononcé.

## Étape 3. Storyboard en 3 planches (validation utilisateur)

Ne **jamais** animer avant. Faire 3 planches d'images clés (problème / démo-consultation / suite et
fin), 8 à 12 images par planche, chaque image avec : instant, phrase de la voix, une note de 1 à
2 phrases sur le mouvement. Générer avec `outils/planche.py` (JSON → PNG), regarder le résultat,
corriger, puis présenter à l'utilisateur. Insister sur les **transitions** : les décrire en tableau
(image de début/fin, ce qu'on voit, courbe) dans un fichier `TRANSITIONS.md` de production.

Mise en page : choisir UNE mise en page dominante (centrée recommandée), et une seule exception
motivée (ex. téléphone en deux colonnes). Écrans entiers visibles, jamais coupés.

## Étape 4. Animation (économie de tokens)

Créer le projet vidéo (composition racine + une sous-composition par séquence, voir les skills
HyperFrames : `hyperframes-core`, `hyperframes-animation`). Brancher voix, musique, polices
locales. Découper en 3 lots indépendants (ouverture / démo / fin), **un agent Sonnet par lot**
(effort `medium`), avec `references/brief-agent-animateur.md`. Chaque lot ne modifie que ses fichiers.
Les éléments partagés entre lots (fenêtre qui reste d'une séquence à l'autre) ont un cadrage final
commun écrit dans le brief.

## Étape 5. Contrôle et rendu (validation utilisateur)

1. `npx --yes hyperframes@0.8.91 lint <projet>` : 0 erreur.
2. Rendu court, puis **une planche des transitions** (8 images par transition) ; la regarder.
   Corriger soi-même les défauts simples (retarder, décaler, allonger) sans relancer d'agent.
3. Ajouter le son : `ffmpeg -i image.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -shortest film.mp4`.
4. Présenter le film **avec la liste des points à trancher** (libellés, rythme, vitesse de lecture).

## Étape 6. Déclinaisons

Seulement après validation du format principal : 4:5, 9:16, version sans voix. Ce n'est pas une
copie : les écrans larges doivent être recomposés. Faire cela dans une session neuve.

## Règles transverses

- Une seule couleur d'accent ; jamais de couleur écrite en dur dans les compositions (variables).
- Pas de coupe sèche, pas de flou de mouvement, pas de rebond : voir la grammaire.
- Allégations de santé, de performance ou de sécurité dans le script : demander une relecture
  humaine avant diffusion. Libellés d'interface inventés pour la vidéo : à signaler comme tels.
- Licences : musique (usage publicitaire payant ?), police commerciale, voix synthétique (conditions).
- Expliquer à l'utilisateur en français simple ; ne lui demander que ses vrais choix, avec une
  recommandation.
