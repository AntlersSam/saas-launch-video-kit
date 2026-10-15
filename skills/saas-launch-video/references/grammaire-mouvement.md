# Grammaire de mouvement (version « douce »)

Unités : images (i) à 25 i/s. Cadre de référence 1920 × 1080.

## Courbes (cubic-bezier)

| Nom | Valeur | Usage |
|---|---|---|
| rangement | 0.25, 1, 0.5, 1 (easeOutQuart) | entrées : tout ce qui arrive et se pose |
| camera | 0.65, 0, 0.35, 1 (easeInOutCubic) | recadrages, zooms, éléments qui voyagent |
| texte | 0.33, 1, 0.68, 1 (easeOutCubic) | apparition des mots |
| effacement | 0.12, 0, 0.39, 0 (easeInSine) | sorties |
| rotation / respiration | 0.37, 0, 0.63, 1 (easeInOutSine) | mouvements lents d'ambiance |
| derive | linéaire | dérive de fond presque invisible |

Interdits : `back`, `elastic`, `bounce`, rebonds, dépassement de cible. Éviter l'expo-out
très sec (« brusque ») pour les écrans ; le réserver aux petits éléments.

## Règles anti-brusque (à vérifier à chaque transition)

| Règle | Valeur |
|---|---|
| Entrée | ≥ 14 i |
| Caméra, zoom, élément partagé | ≥ 16 i (zoom ≥ 20 i) |
| Sortie | ≥ 8 i, flou 0 → 6 px |
| Mot | 10 i, décalage 3 i entre mots |
| Vitesse max | bloc ≥ 300 px : ≤ 30 px/i ; petit élément : ≤ 40 px/i |
| Lecture | un écran immobile ≥ 25 i ; une phrase complète à l'écran ≥ 1 s |
| Chevauchement | chaque passage entre séquences est un fondu/chevauchement, jamais une coupe |
| Interdit | coupe en plein mouvement, balayage flou, flou de mouvement codé |

## Catalogue d'animations de texte

- **Frappe** (problème) : lettres une à une calées sur la voix, curseur de couleur d'accent,
  clignotant ensuite ; la phrase est mise en page d'emblée (les lettres s'allument, rien ne bouge).
- **Surlignage** du mot-clé : rectangle d'accent qui s'étend de gauche à droite en 8 i, mot en blanc.
- **Montée** : chaque mot monte de 16 px, flou 8 → 0, opacité 0 → 1 ; mot-clé en couleur d'accent.
- **Mot géant** : flou 12 → 0 et échelle 1,08 → 1 en 14 i ; ensuite il rétrécit jusqu'à sa place
  dans la phrase (élément partagé : le mot ne disparaît jamais).
- **Changement de phrase** : l'ancienne s'efface (montée inversée), la nouvelle commence 4 i après.

## Transitions types

| Transition | Recette |
|---|---|
| Problème → problème suivant | la phrase s'efface ; les fragments d'illustration reculent (×0,92, flou, opacité ÷ 2) ; les nouveaux entrent par le bord le plus proche |
| Problème → solution | dissolution vers le fond, silence, un seul curseur clignote, le mot géant naît sur le premier temps fort |
| Mot géant → phrase | le mot rétrécit vers sa place, les autres mots montent |
| Logo → écran produit | le logo rétrécit et glisse sur le côté, l'écran monte (retarder l'écran de 6 i pour éviter le chevauchement) |
| Écran → écran | **la fenêtre reste en place** (élément partagé) ; seul son contenu change par fondu de 12 i |
| Petit objet → grand écran | caméra qui pousse (×1,7 en 20 i), geste (clic, curseur), recul |
| Page → carte | la page se condense en carte qui voyage jusqu'à sa place dans l'écran suivant |
| Démo → preuve | recul ×0,96 et dissolution vers le fond, silence musical, phrase mot à mot |
| Preuve → carton final | la phrase s'efface, le logo naît, la mention s'écrit, **image fixe** jusqu'à la fin, sans fondu au noir |

## Calage sur le son

- Placer l'affichage d'une phrase 3 à 7 i avant le mot prononcé ; ≥ 0,25 s de respiration entre répliques.
- Premier temps fort de la musique = naissance du mot géant ; silences musicaux = respirations.
- Fin du morceau = remontée du logo ; image fixe dès la fin de la musique.
- Peu de bruitages : 2 à 3 « swishs » discrets sur les grandes transitions, sinon rien.

## Mise en page

- Phrase en haut (sur-titre en capitales d'accent, puis phrase 76 px), écran centré dessous
  (zone y 265 → 1055). Exception : un téléphone en mise en page de côté (phrase à gauche).
- Écrans « larges » (tableaux de bord) à recomposer en 16:9 : ne pas réutiliser un cadrage vertical.
- Gros plan : cadrer le point d'intérêt (bouton, champ), pas l'écran entier ; recul ensuite.
