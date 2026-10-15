# Voix off et son avec ElevenLabs (méthode du projet d'origine)

## Outils (connecteur ElevenLabs de Claude, version « restreinte »)

À activer dans Claude (Réglages → Connecteurs → ElevenLabs). Outils utilisés :

| Outil | Usage |
|---|---|
| `creative_list_voices` | Lister les voix, en choisir une adaptée (ne jamais inventer un `voice_id`) |
| `creative_design_voice` puis `creative_save_designed_voice` | Créer une voix à partir d'une description (texte + langue fournis par l'utilisateur) |
| `creative_create_flow` | Créer un « flow » (canevas) AVANT de générer : toutes les répliques y vivent |
| `creative_generate_speech` | Générer une réplique (retourne tout de suite ; attendre ensuite) |
| `creative_get_flow_run_status` | Attendre la fin (`poll_after_seconds`) puis récupérer les prises |
| `creative_transcribe_audio` | Transcrire une prise (contrôle du texte, instants de chaque mot) |
| `creative_create_asset_upload` / `creative_finalize_asset_upload` | Mettre un fichier local dans le flow (octets envoyés en PUT, jamais lus dans la conversation) |
| `creative_get_model_guide`, `creative_get_model_schema` | Lire les réglages d'un modèle avant de les passer |

Limites : pas de musique, d'image ni de vidéo dans cette version (connecteur complet : https://api.elevenlabs.io/v1/mcp).
Chaque génération consomme des **crédits** : ne jamais relancer une génération « pour réessayer » (elle est refacturée),
confirmer avec l'utilisateur avant une longue génération. Le connecteur n'affiche pas le solde : le tenir à la main.

## Réglages qui ont bien marché
- Modèle `eleven_v4`, une voix posée (« Anna »), balise de ton en tête de texte `[calm, measured]`.
- Pas de réglage de stabilité/vitesse exposé pour ce modèle : le débit se pilote par la balise et la ponctuation.
- **1 variation par réplique** (4 variations coûtent 4×). Un nœud par réplique du film.
- Texte envoyé = script mot pour mot, avec adaptations de prononciation (erreur n°24).
- Sorties : WAV 48 kHz mono 24 bits, silences de tête/queue ramenés à ~60 ms, fondu de 5 ms, **sans normaliser** le volume.

## Contrôle réplique par réplique (avant tout calage)
1. Transcrire chaque prise ; comparer au script (texte conforme).
2. Mesurer : durée de parole utile, syllabes/s, LUFS, crête vraie (dBTP ≤ −1), bruit de fond (≤ −60 dBFS), coupures.
3. Comparer à la fenêtre prévue ; si la voix dépasse, **recaler l'image sur la voix** (erreur n°25), ne pas régénérer.
4. Exemple complet : `outils/audio/vo_qc_lines.py` (spécifique au projet ; à adapter).

## Calage image / son
- Chaque phrase affichée 3 à 7 images avant le mot prononcé ; ≥ 0,25 s de respiration entre répliques.
- Placer les répliques selon un fichier `voix.json` (début/fin en images) ; le film lit les WAV tels quels.

## Musique
- Choisir un morceau dont les temps tombent sur les transitions (BPM → images par temps) ; vérifier la **licence
  publicitaire payante** avant diffusion (le morceau du projet d'origine est sous licence Artlist : non fourni).
- Monter le morceau pour qu'il tienne exactement la durée du film : intro « lavée » sans pulsation pendant le problème,
  premier temps fort sur la bascule, silences d'un temps avant les moments forts, arrêt du morceau sur le carton final.
  Outils d'exemple : `outils/audio/music_analyze.py` (tempo, temps), `outils/audio/music_montage.py` (montage et raccords).

## Mixage
- Voix devant : même niveau pour toutes les répliques, coupe-bas 80 Hz, compression douce 2:1, musique en retrait
  sous la voix, 2-3 bruitages discrets seulement. Cible ≈ −14 LUFS, crête vraie ≤ −1 dBTP.
- Exemple : `outils/audio/mix_v1.py` (voix + musique montée + bruitages → WAV 48 kHz 24 bits) ; puis le WAV est collé au rendu
  image avec `ffmpeg … -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -shortest`.
