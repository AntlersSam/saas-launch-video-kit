# Erreurs techniques rencontrées et corrigées (projet d'origine)

À lire avant la porte 6 (animation) et dès qu'un défaut apparaît.

| # | Symptôme | Cause | Correction |
|---|---|---|---|
| 1 | `lint` : `timeline_id_mismatch` (« Timeline registered as X but no element has data-composition-id=X ») | On a renommé le `data-composition-id` de la racine sans renommer la clé `window.__timelines["..."]` | Garder les deux identiques (chercher toutes les occurrences avec `grep`) |
| 2 | ffmpeg : `Unrecognized option 'vsync'` | ffmpeg 9 a supprimé `-vsync` | Utiliser `-fps_mode passthrough` |
| 3 | Python : `SyntaxWarning: invalid escape sequence '\,'` dans `select='eq(n\,12)'` | Antislash dans une chaîne normale | Chaîne brute `r"..."` ou antislash doublé |
| 4 | Commande shell qui échoue : `unexpected EOF while looking for matching '` | Gros bloc Python avec apostrophes collé dans une commande | Écrire le script dans un fichier (outil d'écriture) puis l'exécuter ; jamais de gros heredoc |
| 5 | `UnicodeEncodeError: 'charmap' codec can't encode` en affichant le JSON de `yt-dlp` (emoji) | Console Windows en cp1252 | `python -X utf8` (ou `PYTHONUTF8=1`) |
| 6 | Chrome headless ne produit aucune image | Ancien mode `--headless` | `--headless=new` obligatoire ; ajouter `--allow-file-access-from-files` (polices/images en `file://`) et `--virtual-time-budget=3000` |
| 7 | La timeline est plus courte que la composition | Aucune animation jusqu'à la fin de la fenêtre | Ancrer la durée : `tl.set({}, {}, dureeEnSecondes)` en fin de timeline |
| 8 | Une valeur de départ est appliquée trop tôt | `fromTo` sans `immediateRender: false` écrase l'état avant son début | `immediateRender: false` sur les tweens qui démarrent plus tard |
| 9 | Un élément « visible » apparaît pendant une autre séquence | `tl.set(visibility:"hidden")` rejoué en arrière réécrit `visible` en ligne | Valeur de départ `inherit` et changements en `fromTo inherit ↔ hidden` |
| 10 | Le moteur balaie toute la timeline à chaque image | Un accesseur `set` sur un objet piloté par un tween est pris pour un réglage de volume | Piloter un compteur par une fonction lire/écrire `f(v)` plutôt qu'un accesseur |
| 11 | `check` signale des erreurs de contraste sur des fragments gris volontairement très pâles et sur du texte en transition | Faux positifs du contrôle de contraste | Les relever dans le rapport, ne pas les « corriger » ; vérifier à l'œil sur la planche |
| 12 | Gros plan : `mouvement.py` donne ~500 px/i sur les bords | La corrélation de phase suit mal un zoom ou du texte | Calculer à la main (échelle par image ≤ 8 %/i) ou allonger le zoom (20 → 28 i) |
| 13 | Un mouvement `x:-380` semblait « sans effet » sur le logo | Diagnostic hâtif : il agissait mais trop tard, le téléphone arrivait par-dessus | Regarder la planche des 8 images avant de conclure ; avancer le logo de 4 i et retarder le téléphone de 6 i |
| 14 | Champ coupé en bas d'une fenêtre élargie | Fenêtre 16:9 plus basse que le calque 4:5 d'origine | Resserrer marges et intervalles ou réduire le nombre de champs |
| 15 | Premier mot d'une phrase décentré pendant la frappe | Texte mis en page lettre par lettre | Mettre la phrase complète en page dès le départ, allumer les lettres une à une |
| 16 | Clignotement 8 i / 8 i impossible | Silence musical de 14 images seulement | 2 flashs courts de 3-4 i |
| 17 | Cadrage différent d'une fenêtre partagée entre deux séquences | Chaque agent calculait son cadrage | Donner `left, top, scale` exacts dans les deux briefs |
| 18 | Un agent a généré ses compositions avec un script jeté dans un dossier temporaire | Script non conservé | Exiger que les générateurs vivent dans le projet, ou modifier les `.html` directement |
| 19 | Deux contrôles en parallèle échouent | `check` HyperFrames utilise un seul navigateur | Un seul `check` à la fois ; réessayer plus tard |
| 20 | Une tâche de fond continue de corriger une version abandonnée | Workflow de 12 agents non arrêté | Message d'arrêt à la session concernée + `TaskStop` ; vérifier qu'elle est inactive |
| 21 | Police absente au rendu | Police commerciale installée seulement sur un poste | `@font-face` avec `local()` + repli sur une police libre (Inter, OFL) fournie dans `fonts/` |
| 22 | Rendu très long | Qualité « diffusion » à chaque essai | Essais en `--quality looks`, diffusion (`delivery`, 27 Mbit/s) une seule fois |
| 23 | Sur-consommation de tokens | Trop d'agents, lectures de documents longs, tours de correction automatiques | Voir `lecons.md`, section « Économie de tokens » |
| 24 | Voix : « pelviennes » dit « pélevienne », « Hey Lilie » dit « et Lili » | Prononciation du modèle sur un mot rare ou un nom de marque | Écrire la prononciation (API entre barres, ou graphie phonétique « Hé Lili ») ; vérifier par transcription |
| 25 | Voix : réplique plus longue que sa fenêtre (+0,4 à +1,6 s) | Le registre posé ralentit le débit (3,4 à 3,9 syllabes/s) | Recaler les fenêtres d'affichage sur la voix réelle (ne pas régénérer) ; le débit se pilote par la balise et la ponctuation |
| 26 | Coût vocal x4 | 4 variations par réplique | 1 variation par réplique ; les extraits courts en une seule génération découpée aux silences |
