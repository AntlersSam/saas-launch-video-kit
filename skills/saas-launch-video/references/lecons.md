# Leçons apprises (à ne pas refaire)

Source : film de lancement de Lilie, octobre 2026. Premier tour rejeté, deuxième validé.

## Ce qui a fait rejeter le premier tour

1. **Fond sombre** alors que la marque est claire : copier le style d'une référence (fond noir, halos
   colorés) sans vérifier qu'il convient à la marque. → Copier la grammaire, pas l'habillage.
2. **Animations brusques** : départs d'expo-out très secs, coupes en plein mouvement, balayages
   flous entre écrans. → Courbes douces, durées minimales, chevauchements.
3. **Démo illisible** : écrans coupés ou trop petits, 1 à 2 s par écran, phrase pleine page qui
   cache l'écran. → Phrase en haut + écran entier dessous, 25 i immobiles minimum.
4. **Téléphone presque invisible** : gros plan coupé, puis balayage. → Téléphone entier au centre ≥ 3 s.

## Ce qui a bien marché

- **3 planches d'images clés validées avant d'animer** : l'utilisateur voit tout (y compris les
  transitions décrites) pour un coût de quelques milliers de tokens, contre des dizaines de
  milliers pour une animation refaite.
- **Un document de production des transitions** (`TRANSITIONS.md` : image de début/fin, ce qu'on
  voit, courbe) : les agents animateurs l'appliquent sans interpréter.
- **Éléments partagés** entre séquences (badge qui voyage, fenêtre qui reste en place, page qui
  devient carte) : c'est ce qui rend un film « fluide ».
- **Une planche de 8 images par transition** pour contrôler : une seule image de synthèse.
- **Corriger soi-même** les défauts simples (décaler de 6 i, allonger un zoom) plutôt que de relancer un agent.

## Pièges techniques

- Les animateurs ne doivent modifier que leurs fichiers ; le cadrage final d'un élément partagé
  entre deux lots est donné dans les deux briefs (mêmes coordonnées).
- Un mouvement posé en `x` peut sembler sans effet si un autre tween ou un `set` écrase le
  transform : regarder la planche, pas seulement le code.
- Un zoom produit de grandes vitesses sur les bords : le contrôle de vitesse sur le contenu ne
  convient pas, calculer à la main (échelle par image) ou allonger.
- Mettre le texte dans sa mise en page finale dès le départ : sinon le premier mot n'est pas centré.
- Un silence musical court (≈ 0,5 s) ne permet pas un clignotement 8 i / 8 i : 2 flashs brefs.
- Rendre d'abord en qualité normale ; la qualité « diffusion » (27 Mbit/s) seulement pour le film validé.

## Économie de tokens (le gros poste)

Un premier projet a consommé ~65 % d'un quota hebdomadaire : workflow de 12 agents, critiques à
4 lentilles, 6 contrôles, tours de correction automatiques, et un workflow qui a continué de
corriger une version abandonnée. Règles :

- Session principale : Opus en effort `medium` (`high` seulement pour un gros chantier).
- Agents animateurs : Sonnet `medium`, ≤ 3 en parallèle, brief précis (fichiers à lire listés,
  documents longs interdits), rapport ≤ 15 lignes.
- Pas de critique multi-lentilles ni de tours de correction automatiques.
- Pas de déclinaison (4:5, 9:16) avant validation du format principal.
- Arrêter immédiatement toute tâche de fond devenue inutile.
- À 40 % de contexte : sauvegarder l'état dans un fichier et repartir sur une session neuve.

## Points à faire valider par un humain avant diffusion

Libellés d'interface inventés pour la vidéo ; chiffres, scores, allégations de santé ou de
performance ; licence de la musique (pub payante) ; licence des polices ; conformité des
éventuels extraits de questionnaires ou d'outils sous licence ; date de disponibilité annoncée.
