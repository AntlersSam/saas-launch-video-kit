"""Mixage V1 du film de lancement Lilie (phase 7) : voix, musique montée, bruitages.

Usage (depuis la racine du projet) :
    python -I scripts/mix_v1.py

Entrées : film/audio/golden-ascent-montage.wav (musique calée à l'image), film/audio/voix/*.wav (14 répliques,
placées selon film/audio/voix.json), assets/sfx/*.mp3 (bruitages, repères recalés sur le rendu image).
Sorties : work/renders/lilie-v1-mix.wav (48 kHz, 24 bits, stéréo, 2 280 960 échantillons = 1188 images)
          work/renders/lilie-v1-mix.json (réglages, gains, mesures)

Règles appliquées (CLAUDE.md, plan de production, challenge-motion §5) :
  - voix devant : chaque réplique ramenée au même niveau, coupe-bas 80 Hz, compression douce 2:1 ;
  - musique ~8 dB sous la voix pendant la parole ; respirations entre répliques de 0,2 à 0,4 s, trop courtes pour
    remonter la musique sans pompage : elle reste donc sous la voix d'une réplique à l'autre, et se pose plus haut
    (+4 dB) sur le premier temps fort du reveal avant de glisser sous « Gagnez » (raised-cosine 0,3 s) ;
  - bruitages 11 à 15 dB sous la voix (pic de sonie sur 400 ms), textures plus bas, et jamais de crête plus forte
    que les crêtes de la musique autour d'eux (plafond -1 dB : les sons à transitoire marqué descendent plus bas) ;
    acte 1 : nappe seule (les 4 bruitages concrets pen_scratch, night_keys, paper_tabs, folder_slide n'existent
    pas encore) ; underline_stroke seulement là où le trait violet se trace à l'image (P8, i1044) ;
  - deux vrais silences (i250 → i264, i1015 → i1030) : rien d'autre que du zéro numérique ;
  - -14 LUFS intégré, crête vraie ≤ -1 dBTP (limiteur à suréchantillonnage x4, délai compensé).
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
FILM = ROOT / "film"
OUT_DIR = ROOT / "work" / "renders"
TMP = OUT_DIR / "_mix_tmp"

SR = 48000
FPS = 25
IMAGES = 1188
N = IMAGES * SR // FPS  # 2 280 960

CIBLE_LUFS = -14.0
LIMITE_DBTP = -1.0
MUSIQUE_SOUS_VOIX = 8.0       # dB
REVEAL_SURPLUS_DB = 4.0       # la musique entre un peu plus haut sur le premier temps fort, puis se pose
SILENCES_S = [(10.0, 10.6), (40.5984, 41.2515)]
AMB_DEBUT_S, AMB_FIN_S = 10.6, 45.96

# ── Bruitages : (nom, image de synchro, point de synchro dans le fichier en ms, niveau relatif à la voix, options)
# Repères relevés sur le rendu (work/renders/lilie-v1-image.mp4), pas sur le storyboard.
SFX = [
    # P2 : reveal, aimantation, cube
    ("drift_float",     265,    0, -15.0, {}),                      # objets qui se détachent du bureau (T1)
    ("pill_open",       267,   20, -12.0, {}),                      # pastille « Gagnez du temps » s'ouvre
    ("gravity_swell",   322,  720, -11.0, {}),                      # tout s'aimante vers le centre (pic vitesse ~i322)
    ("cube_turn",       345,    0, -12.0, {"fade_in": 15}),         # quart de tour du cube (i345 → i360)
    ("push_morph",      380,  100, -11.5, {"fade_in": 30}),         # T2 : la face devient l'écran (vitesse max ~i380)
    # P3 : questionnaire
    ("pill_open",       379,   20, -12.0, {}),                      # pastille « Avant la séance »
    ("screen_tap",      395,   10, -13.0, {"fade_in": 3}),          # toucher sur « Une petite quantité »
    ("ripple_shimmer",  395,    0, -14.0, {}),                      # onde légère du toucher
    ("ui_glide",        424,  410, -14.0, {}),                      # barre de progression qui avance (arrivée i424)
    ("ui_glide",        449,  410, -12.0, {}),                      # badge « Questionnaire reçu » sort en glissant
    ("camera_glide",    461,  420, -11.5, {"fade_out": (400, 560)}),  # T3 : la caméra recule et glisse (vitesse max ~i461)
    # P4 : consultation
    ("voice_flow",      497,   50, -15.0, {"tempo": 0.6}),          # texture sous les ondes (i497 → i580)
    ("pill_open",       502,   20, -12.0, {}),                      # pastille « Concentrez-vous sur l'échange »
    ("lines_fill",      510,    0, -13.0, {"fade_in": 5}),          # premier champ qui se remplit
    ("ui_glide",        532,  410, -13.0, {}),                      # étape « Obstétrique » (arrivée i532)
    ("ui_glide",        550,  410, -13.0, {}),                      # étape « Urinaire »
    ("ui_glide",        566,  410, -13.0, {}),                      # étape « Clinique »
    ("ui_glide",        582,  410, -13.0, {}),                      # étape « Synthèse »
    ("tilt_down",       617,    0, -11.0, {}),                      # T4 : bascule 3D (i616 → i656)
    # P5 : échelles
    ("token_settle",    670,   90, -12.0, {"fade_in": 5}),          # jeton Oxford posé (pose i673, arrivée visible ~i667)
    ("ripple_shimmer",  673,    0, -15.0, {}),                      # onde de contact
    ("token_settle",    678,   90, -12.0, {"fade_in": 5}),          # jeton ICIQ-UI SF
    ("ripple_shimmer",  681,    0, -15.0, {}),
    ("token_settle",    686,   90, -12.0, {"fade_in": 5}),          # jeton POP-Q
    ("ripple_shimmer",  689,    0, -15.0, {}),
    ("pill_open",       689,   20, -12.0, {}),                      # pastille « Un bilan complet, documenté »
    ("card_lift",       709,    0, -11.5, {"fade_in": 10}),         # T5 : la carte se lève (i709 → i745)
    # P6 : courrier
    ("paper_settle",    744,  370, -13.0, {"fade_in": 10}),         # la page se pose, jetons rangés
    ("pill_open",       747,   20, -12.0, {}),                      # pastille « Le courrier est prêt à relire »
    ("send_away",       786,    0, -11.5, {"fade_in": 30}),         # T6 : la carte descend rejoindre le parcours
    # P7 : suivi partagé
    ("camera_glide",    818,    0, -14.0, {"fade_out": (400, 560), "tempo": 0.5}),  # recul lent de la caméra
    ("ripple_shimmer",  902,    0, -14.0, {}),                      # Gynécologue relié(e)
    ("ripple_shimmer",  918,    0, -14.0, {}),                      # Sage-femme
    ("ripple_shimmer",  934,    0, -14.0, {}),                      # Kinésithérapeute
    ("pill_open",       980,   20, -12.0, {}),                      # pastille « Un suivi complet, à chaque étape »
    # P8 / T8
    ("underline_stroke", 1044,  0, -13.0, {"fade_in": 10}),         # le trait violet se trace (i1044 → i1058)
    ("gather_bloom",    1081,  180, -12.0, {"fade_in": 10}),        # T8 : la phrase devient le logo (carré → cube)
]
AMB_REL = -32.0  # ambiance d'air, très bas, de P2 à la fin de la voix (absente des silences et de l'acte 1)


# ── Utilitaires audio ───────────────────────────────────────────────────────────────────────────────────────
def decode(path, ch, filtres=None):
    cmd = ["ffmpeg", "-v", "error", "-i", str(path)]
    if filtres:
        cmd += ["-af", filtres]
    cmd += ["-f", "f32le", "-ac", str(ch), "-ar", str(SR), "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, ch).astype(np.float64)


def write_wav_f32(path, x):
    x = np.asarray(x, dtype=np.float32)
    if x.ndim == 1:
        x = x[:, None]
    ch = x.shape[1]
    data = x.tobytes()
    import struct
    hdr = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
    hdr += b"fmt " + struct.pack("<IHHIIHH", 16, 3, ch, SR, SR * ch * 4, ch * 4, 32)
    hdr += b"data" + struct.pack("<I", len(data))
    Path(path).write_bytes(hdr + data)


def ffmpeg_filtre(x, filtres, ch):
    TMP.mkdir(parents=True, exist_ok=True)
    src = TMP / "in.wav"
    write_wav_f32(src, x)
    return decode(src, ch, filtres)


def _biquad_ir(b, a, n):
    y = np.zeros(n)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(n):
        x0 = 1.0 if i == 0 else 0.0
        y0 = b[0] * x0 + b[1] * x1 + b[2] * x2 - a[1] * y1 - a[2] * y2
        y[i] = y0
        x2, x1, y2, y1 = x1, x0, y1, y0
    return y


_KIR = None


def k_ir():
    global _KIR
    if _KIR is None:
        n = 16384
        h1 = _biquad_ir([1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585], n)
        h2 = _biquad_ir([1.0, -2.0, 1.0], [1, -1.99004745483398, 0.99007225036621], n)
        _KIR = np.convolve(h1, h2)[:n]
    return _KIR


def kweight(x):
    h = k_ir()
    n = x.shape[0] + len(h) - 1
    nfft = 1 << int(np.ceil(np.log2(n)))
    H = np.fft.rfft(h, nfft)
    out = np.empty_like(x)
    for c in range(x.shape[1]):
        out[:, c] = np.fft.irfft(np.fft.rfft(x[:, c], nfft) * H, nfft)[: x.shape[0]]
    return out


def stereo(x):
    return x if x.ndim == 2 and x.shape[1] == 2 else np.repeat(x.reshape(-1, 1), 2, axis=1)


def blocs(x, masque=None):
    """Sonie de blocs de 400 ms (pas de 100 ms), LUFS. masque : booléens par échantillon (blocs gardés si tout dedans)."""
    z = kweight(stereo(x)) ** 2
    p = z.sum(axis=1)
    c = np.concatenate([[0.0], np.cumsum(p)])
    w, hop = int(0.4 * SR), int(0.1 * SR)
    starts = np.arange(0, len(p) - w + 1, hop)
    ms = (c[starts + w] - c[starts]) / w
    if masque is not None:
        cm = np.concatenate([[0], np.cumsum(masque.astype(np.int64))])
        keep = (cm[starts + w] - cm[starts]) == w
        ms = ms[keep]
    return ms


def lufs_de_blocs(ms):
    ms = ms[ms > 0]
    if not len(ms):
        return -np.inf
    L = -0.691 + 10 * np.log10(ms)
    ms = ms[L > -70]
    if not len(ms):
        return -np.inf
    rel = -0.691 + 10 * np.log10(ms.mean()) - 10
    ms = ms[-0.691 + 10 * np.log10(ms) > rel]
    return -0.691 + 10 * np.log10(ms.mean())


def integre(x, masque=None):
    return lufs_de_blocs(blocs(x, masque))


def momentane_max(x):
    ms = blocs(np.concatenate([x, np.zeros(int(0.4 * SR))]) if x.ndim == 1 else x)
    return -0.691 + 10 * np.log10(ms.max() + 1e-20)


def crete_vraie(x):
    """Crête vraie approchée : suréchantillonnage x4 par FFT, par tranches de 4 s."""
    x = stereo(x)
    best = 0.0
    tr = SR * 4
    for c in range(2):
        for d in range(0, len(x), tr):
            a = x[max(0, d - 256): d + tr + 256, c]
            n = len(a)
            A = np.fft.rfft(a)
            B = np.zeros(2 * n + 1, dtype=complex)
            B[: len(A)] = A
            up = np.fft.irfft(B, 4 * n) * 4
            best = max(best, np.abs(up).max())
    return 20 * np.log10(best + 1e-20)


def rc(n):
    """Rampe raised-cosine de 0 à 1 sur n échantillons."""
    return 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n))


def s(t):
    return int(round(t * SR))


# ── Mixage ────────────────────────────────────────────────────────────────────────────────────────────────
def main():
    timing = json.loads((FILM / "timing.json").read_text(encoding="utf-8"))
    voix = json.loads((FILM / "audio" / "voix.json").read_text(encoding="utf-8"))
    rapport = {"cible_lufs": CIBLE_LUFS, "limite_dbtp": LIMITE_DBTP}

    # Bornes de parole précises (secondes) depuis timing.json
    parole = {}
    for p in timing["plans"]:
        for v in p.get("voix", []):
            parole[v["id"]] = (v["debut_s"], v["fin_s"])

    # 1. Voix : même niveau pour chaque réplique, puis coupe-bas 80 Hz et compression douce 2:1
    CIBLE_LIGNE = -20.0
    v_stem = np.zeros(N)
    lignes = []
    for r in voix["repliques"]:
        x = decode(FILM / r["fichier"], 1)[:, 0]
        L = integre(x)
        g = CIBLE_LIGNE - L
        d = s(r["data_start"])
        seg = x * 10 ** (g / 20)
        v_stem[d: d + len(seg)] += seg[: N - d]
        lignes.append({"id": r["id"], "debut_s": r["data_start"], "lufs_source_mesure": round(L, 1), "gain_db": round(g, 1)})
    # aucune voix dans les silences (queue d'air de 1e : fondu de 30 ms à 10,00 s)
    for a, b in SILENCES_S:
        i0, i1 = s(a), s(b)
        f = s(0.03)
        v_stem[i0: i0 + f] *= rc(f)[::-1]
        v_stem[i0 + f: i1] = 0
    v_proc = ffmpeg_filtre(v_stem, "highpass=f=80:poles=2,acompressor=threshold=0.0631:ratio=2:attack=8:release=140:knee=2.5:detection=rms", 1)[:, 0]
    v_proc = np.pad(v_proc, (0, max(0, N - len(v_proc))))[:N]
    for a, b in SILENCES_S:
        v_proc[s(a) + s(0.03): s(b)] = 0
    VOIX = stereo(v_proc)
    masque_parole = np.zeros(N, dtype=bool)
    for a, b in parole.values():
        masque_parole[s(a): s(b)] = True
    L_V = integre(VOIX, masque_parole)
    rapport["voix"] = {"lignes": lignes, "lufs_voix_pendant_parole": round(L_V, 2)}

    # 2. Musique : une sonie par grande région, 8 dB sous la voix pendant la parole
    mus = decode(FILM / "audio" / "golden-ascent-montage.wav", 2)
    mus = np.pad(mus, ((0, max(0, N - len(mus))), (0, 0)))[:N]
    regions = {"acte1": (0.0, 10.0), "P2-P7": (10.6, 40.5984), "P8-P9": (41.2515, IMAGES / FPS)}
    gains = {}
    for nom, (a, b) in regions.items():
        m = masque_parole.copy()
        m[: s(a)] = False
        m[s(b):] = False
        Lm = integre(mus, m)
        Lv = integre(VOIX, m)
        gains[nom] = (Lv - MUSIQUE_SOUS_VOIX) - Lm
        rapport.setdefault("musique", {})[nom] = {"lufs_musique_brute_sous_parole": round(Lm, 2), "lufs_voix": round(Lv, 2), "gain_db": round(gains[nom], 2)}
    env = np.zeros(N)
    env[: s(10.3)] = gains["acte1"]
    env[s(10.3): s(41.0)] = gains["P2-P7"]
    env[s(41.0):] = gains["P8-P9"]
    # reveal : +4 dB sur le premier temps fort, glisse sous la voix entre 10,62 et 10,92 s (avant « Gagnez », 10,945 s)
    r0, r1 = s(10.62), s(10.92)
    env[s(10.3): r0] = gains["P2-P7"] + REVEAL_SURPLUS_DB
    env[r0: r1] = gains["P2-P7"] + REVEAL_SURPLUS_DB * (1 - rc(r1 - r0))
    MUS = mus * (10 ** (env / 20))[:, None]
    rapport["musique"]["reveal"] = f"+{REVEAL_SURPLUS_DB} dB de 10,60 à 10,62 s, glisse jusqu'au niveau sous voix à 10,92 s"

    # 3. Bruitages
    BRU = np.zeros((N, 2))
    poses = []
    cache = {}
    for nom, image, sync_ms, rel, opt in SFX:
        cle = (nom, json.dumps(opt, sort_keys=True))
        if cle not in cache:
            filtres = []
            if opt.get("tempo"):
                filtres.append(f"atempo={opt['tempo']}")
            x = decode(ROOT / "assets" / "sfx" / f"{nom}.mp3", 1, ",".join(filtres) if filtres else None)[:, 0].copy()
            fi = opt.get("fade_in", 5)
            k = max(1, s(fi / 1000))
            x[:k] *= rc(k)
            if "fade_out" in opt:
                a, b = opt["fade_out"]
                t = opt.get("tempo") or 1.0
                ia, ib = s(a / 1000 / t), s(b / 1000 / t)
                x[ia:ib] *= rc(ib - ia)[::-1]
                x[ib:] = 0
            k = s(0.01)
            x[-k:] *= rc(k)[::-1]
            cache[cle] = (x, momentane_max(x))
        x, Lm = cache[cle]
        g = (L_V + rel) - Lm
        sync = sync_ms / 1000 / (opt.get("tempo") or 1.0)
        debut = image / FPS - sync
        d = s(debut)
        # aucun bruitage plus fort que les crêtes de la musique autour de lui (−1 dB de marge)
        w0, w1 = max(0, d - s(0.25)), min(N, d + len(x) + s(0.25))
        pk_mus = 20 * np.log10(np.abs(MUS[w0:w1]).max() + 1e-12)
        pk_x = 20 * np.log10(np.abs(x).max() + 1e-12)
        plafond = (pk_mus - 1.0) - pk_x
        borne = plafond < g
        g = min(g, plafond)
        seg = x * 10 ** (g / 20)
        a0 = max(0, d)
        seg = seg[a0 - d:]
        BRU[a0: a0 + len(seg)] += seg[: N - a0, None]
        poses.append({"son": nom, "image": image, "debut_s": round(debut, 3), "fin_s": round(debut + len(x) / SR, 3),
                      "niveau_vise_vs_voix_db": rel, "niveau_obtenu_vs_voix_db": round(Lm + g - L_V, 1),
                      "borne_par_crete_musique": bool(borne), "crete_avant_gain_global_dbfs": round(pk_x + g, 1),
                      "crete_musique_autour_dbfs": round(pk_mus, 1)})
    # ambiance d'air (boucle de 3 s, fondus enchaînés de 0,5 s)
    amb = decode(ROOT / "assets" / "sfx" / "amb_air.mp3", 1)[:, 0]
    La = integre(amb)
    ga = (L_V + AMB_REL) - La
    lon = s(AMB_FIN_S - AMB_DEBUT_S)
    xf = s(0.5)
    bed = np.zeros(lon + len(amb))
    pos = 0
    while pos < lon:
        seg = amb.copy()
        seg[:xf] *= rc(xf)
        seg[-xf:] *= rc(xf)[::-1]
        bed[pos: pos + len(seg)] += seg
        pos += len(amb) - xf
    bed = bed[:lon] * 10 ** (ga / 20)
    bed[: s(0.5)] *= rc(s(0.5))
    bed[-s(0.8):] *= rc(s(0.8))[::-1]
    AMB = np.zeros(N)
    AMB[s(AMB_DEBUT_S): s(AMB_DEBUT_S) + lon] = bed
    a, b = SILENCES_S[1]
    i0, i1 = s(a - 0.12), s(b + 0.15)
    AMB[i0 - s(0.12): i0] *= rc(s(0.12))[::-1]
    AMB[i0: i1] = 0
    AMB[i1: i1 + s(0.3)] *= rc(s(0.3))
    BRU += stereo(AMB)
    rapport["bruitages"] = poses
    rapport["ambiance"] = {"debut_s": AMB_DEBUT_S, "fin_s": AMB_FIN_S, "niveau_vs_voix_db": AMB_REL, "coupee_pendant": [a, b]}

    # 4. Somme, sonie -14 LUFS, limiteur crête vraie (suréchantillonné x4, délai compensé)
    MIX = VOIX + MUS + BRU
    g = 0.0
    for it in range(3):
        L0 = integre(MIX * 10 ** (g / 20))
        g += CIBLE_LUFS - L0
        lim = ffmpeg_filtre(MIX * 10 ** (g / 20), "aresample=192000:resampler=soxr,alimiter=limit=0.84:attack=3:release=60:level=false:latency=true,aresample=48000:resampler=soxr", 2)
        lim = np.pad(lim, ((0, max(0, N - len(lim))), (0, 0)))[:N]
        L1 = integre(lim)
        print(f"  passe {it + 1} : gain {g:+.2f} dB, avant limiteur {L0 + (CIBLE_LUFS - L0):.2f}, après {L1:.2f} LUFS")
        if abs(L1 - CIBLE_LUFS) < 0.05:
            break
        g += CIBLE_LUFS - L1
    # vrais silences : zéro numérique strict
    # (après les micro-fondus du montage : 25 ms de nappe / voix en tête, 10 ms avant l'attaque qui suit)
    for a, b in SILENCES_S:
        lim[s(a) + s(0.04): s(b) - s(0.012)] = 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    src = TMP / "mix_f32.wav"
    write_wav_f32(src, lim)
    out = OUT_DIR / "lilie-v1-mix.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-c:a", "pcm_s24le", str(out)], check=True)
    rapport["gain_global_db"] = round(g, 2)
    rapport["mesures_internes"] = {"lufs_integre": round(integre(lim), 2), "crete_vraie_dbtp_approx": round(crete_vraie(lim), 2)}
    # stems pour le contrôle (non livrés)
    for nom, arr in (("voix", VOIX), ("musique", MUS), ("bruitages", BRU)):
        write_wav_f32(TMP / f"stem_{nom}.wav", arr * 10 ** (g / 20))
    (OUT_DIR / "lilie-v1-mix.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in rapport.items() if k not in ("bruitages",)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
