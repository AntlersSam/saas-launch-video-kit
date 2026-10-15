---
name: saas-launch-video
description: Réaliser une vidéo motion de lancement de produit SaaS (30 à 60 s, voix off, musique, vrais écrans animés), étape par étape et avec validation de l'utilisateur à chaque porte : design system d'abord, puis brief, puis planches de storyboard une par une, et seulement ensuite l'animation (HyperFrames + GSAP) et le rendu MP4. À utiliser pour toute vidéo de lancement, film produit, motion design SaaS, « launch video », storyboard vidéo, animer des écrans de produit, ou refaire une vidéo comme une référence (Lovable, Numtera…).
---

# Vidéo motion de lancement SaaS : méthode pas à pas

## Règle d'or : une porte à la fois

Le skill avance par **portes**. À chaque porte : produire le livrable, le montrer, poser UNE question
(avec une recommandation), puis **s'arrêter et attendre la réponse**. Ne jamais enchaîner deux portes
dans le même message, ne jamais animer avant la porte 5. Ne jamais inventer une charte, un libellé
d'interface ou une musique : les demander.

| Porte | Livrable | Question posée à l'utilisateur |
|---|---|---|
| 0 | Inventaire + **références** (vidéos qu'il aime) | « Quelles vidéos de référence ? » (proposer Lovable et Numtera, voir `ressources.md`) |
| 1 | Design system validé (`brand.json`) | « Cette charte est-elle bonne ? » |
| 2 | Brief de 10 lignes | « Le brief est-il juste ? » |
| 3 | Référence analysée + structure en actes | « Cette structure vous convient ? » |
| 4a/4b/4c | Planche 1, puis 2, puis 3 (une par message) | « Planche N : on garde, on change quoi ? » |
| 5 | `TRANSITIONS.md` + feu vert d'animation | « Je lance l'animation (coût estimé) ? » |
| 6 | Film 16:9 + planche des transitions | « Points à trancher (liste) ? » |
| 7 | Déclinaisons (4:5, 9:16) | « Quel format en plus ? » (session neuve) |

Références, à ouvrir seulement quand la porte l'exige (économie de contexte) :
`references/grammaire-mouvement.md` (portes 4 à 6), `references/brief-agent-animateur.md` (porte 5),
`references/lecons.md` (leçons et économie de tokens), `references/erreurs-corrigees.md` (26 erreurs
techniques déjà rencontrées et leur correction : à lire avant la porte 6 et en cas de défaut),
`references/voix-elevenlabs.md` (voix off ElevenLabs, musique, mixage : portes 0 et 6),
`references/ressources.md` (outils, skills HyperFrames, commandes).

## Porte 0. Inventaire et références

**Avant tout travail, demander des références** : « Quelles vidéos de lancement aimez-vous (lien YouTube, LinkedIn ou fichier) ? » Proposer d'emblée deux exemples (liens dans `references/ressources.md`) : la vidéo de lancement **Lovable** (mot géant, rythme court, interfaces grossies) et **Numtera** (structure problème → solution, texte en frappe, mot-clé surligné). L'utilisateur choisit une ou plusieurs références, ou en donne d'autres ; **ne pas continuer sans au moins une référence ou un « pas de référence » explicite**. Les analyser à la porte 3.

Puis, en une seule question groupée : script de la voix (phrase par phrase), voix (fichiers ? sinon voix de synthèse ElevenLabs, voir `voix-elevenlabs.md`),
musique (licence pub payante ?), écrans du produit (code, captures, rien), format et durée, vidéo de
référence. Ne rien produire d'autre.

## Porte 1. Design system (toujours AVANT les planches)

Demander la charte : couleurs (fond, accent, encre), polices (et leur licence), ton, logo, règles
(« une seule couleur d'accent », « fond blanc »…). Cas possibles :
- **Charte existante** : la lire (fichier, site, Figma), la résumer en `outils/brand.exemple.json`
  rempli, la faire valider.
- **Pas de charte** : proposer 2 pistes de style en 2 mini-planches (fond clair / fond sombre, accent,
  police libre type Inter), recommander une, faire choisir.
- **Charte de la vidéo de référence** : ne PAS la copier ; copier seulement la grammaire (rythme,
  animations de texte).
Verrouiller : une seule couleur d'accent, aucune couleur en dur (variables), fond choisi par
l'utilisateur (ne jamais supposer sombre ou clair).

## Porte 2. Brief

Résumer en 10 lignes : produit et public, promesse, structure (problème → solution → démo → preuve →
appel), ton, charte, contraintes légales (allégations, licences). Attendre le « ok ».

## Porte 3. Référence et structure

Si une vidéo de référence est donnée : `yt-dlp`, planche `ffmpeg` (1 image/s, 6×8), lire 2 planches ;
en tirer structure, rythme, animations de texte, rôle de la couleur. Proposer la structure par défaut
d'un film de 45 s : problème ≈ 10 s (4-5 phrases courtes) → bascule (silence + mot géant) → promesse
et logo ≈ 5 s → démo ≈ 22 s (3-4 écrans, un par bénéfice) → preuve ≈ 3 s → carton final fixe ≈ 5 s.
Caler chaque phrase sur la voix (affichage 3 à 7 images avant le mot). Valider.

## Porte 4. Storyboard : trois planches, UNE PAR UNE

Planche 1 (problème → promesse), puis planche 2 (démo, avec ses gestes : clic, zoom, remplissage),
puis planche 3 (suite et fin). Pour chacune : 8 à 12 images clés avec instant, phrase de la voix et note
de mouvement de 1-2 phrases, générées par `outils/planche.py` (JSON → PNG) ; la **regarder** (Read sur
le PNG), corriger, puis la présenter seule. Ne passer à la suivante qu'après le « on garde ».
Mise en page : UNE dominante (centrée recommandée) + une exception motivée. Écrans toujours entiers.
Si l'utilisateur demande une scène (« on clique sur un micro et on voit la séance s'enregistrer »),
elle a sa **propre planche**.

## Porte 5. Document de transitions, puis feu vert

Écrire `TRANSITIONS.md` (règles anti-brusque + tableau : transition, images début/fin, ce qu'on voit,
courbes). Annoncer le plan d'animation : 3 lots, un agent Sonnet `medium` par lot, durée et coût
approximatifs. **Attendre le feu vert** avant de lancer.

## Porte 6. Animation, contrôle, rendu

Voix et son : suivre `references/voix-elevenlabs.md` (générer et contrôler les répliques avant de caler l'image). Projet HyperFrames (skills `hyperframes-core`, `hyperframes-animation`, `hyperframes-cli`), un agent par
lot (`references/brief-agent-animateur.md`), ≤ 3 en parallèle. Puis : `lint` → 0 erreur ; rendu normal ;
**planche des transitions** (8 images par transition) ; corriger soi-même les défauts simples ;
ajouter le son (`ffmpeg … -map 0:v -map 1:a -c:v copy -c:a aac`) ; rendu « diffusion » seulement une fois
validé. Présenter le film avec la liste des points à trancher.

## Porte 7. Déclinaisons

Seulement après validation du format principal. Ce n'est pas une copie : les écrans larges se
recomposent. À faire dans une session neuve.

## Règles transverses

- Jamais de coupe sèche, de balayage flou, de rebond ; chaque écran lisible ≥ 1 s (voir la grammaire).
- Allégations de santé, de performance, de sécurité ; libellés d'interface inventés ; licences de
  musique, police, voix : à signaler et à faire valider par un humain avant diffusion.
- Parler français simple ; ne demander que les vrais choix, avec une recommandation.
- Économie de tokens : Opus `medium` en session principale, Sonnet `medium` pour les agents, pas de
  workflow multi-agents ni de critique multi-lentilles sans accord, arrêter toute tâche devenue inutile,
  sauvegarder l'état et repartir en session neuve à 40 % de contexte.
