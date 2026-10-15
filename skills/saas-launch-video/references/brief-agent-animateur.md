# Gabarit de brief pour un agent animateur

À copier dans le prompt d'un agent (outil Agent, `model: "sonnet"`, effort `medium`, en arrière-plan).
Remplacer les [crochets]. Un agent = un lot de séquences = ses propres fichiers.

```
Tu es animateur HyperFrames (GSAP) sur le film de lancement « [produit] » ([format], [fps] i/s,
[N] images). Langue : français. Ton travail : animer fidèlement les images clés VALIDÉES par
[prénom], avec des mouvements DOUX et des écrans LISIBLES.

ÉCONOMIE DE TOKENS OBLIGATOIRE : ne lis que les fichiers listés ci-dessous, par extraits ;
pas d'exploration hors de ton périmètre ; une seule planche de contrôle par transition.

TON PÉRIMÈTRE (tu ne modifies QUE ces fichiers) : [liste des compositions du lot, avec leur
fenêtre d'images et leur data-start]. Ne touche jamais à [index, tokens, timing, audio, autres lots].

À LIRE D'ABORD :
1. TRANSITIONS.md (règles de mouvement, catalogue de textes, tableau des transitions de ton lot).
2. Les images clés validées : [chemins des planches] et leur source [script].
3. Les écrans du produit : [chemins].
4. La voix : [fichier de timing] (phrases et instants).

POINTS D'ATTENTION : [décor déjà fourni ; éléments partagés avec les lots voisins et leur cadrage
final exact en coordonnées ; contraintes de lecture].

CONTRÔLES : lint 0 erreur ; check aux instants clés ; images + une planche par transition dans
[dossier de travail] ; comparer aux images clés.

RAPPORT FINAL (≤ 15 lignes) : ce qui est fait, chemins des planches, écarts restants, doutes
pour [prénom]. Ne commite rien.
```

## Conseils

- Donner le **cadrage final exact** (left, top, scale) des éléments partagés dans les deux briefs voisins.
- Lancer les 3 lots dans le même message pour qu'ils tournent en parallèle.
- Ne pas relancer un agent pour un défaut simple : corriger soi-même (décaler, allonger, retarder).
