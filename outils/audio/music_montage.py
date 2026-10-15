"""Montage de « Golden Ascent » (Artlist) pour le film de lancement Lilie : 47,52 s exactement (1188 images).

v2 (14/10, recalage sur la voix réelle d'Anna) : la partie principale B est prolongée de 3 temps EN CONTINU
(temps k 59 à 61 du morceau, ajoutés au plan P7) ; aucun nouveau raccord. Le film passe de 45,6 à 47,52 s.

Usage (depuis la racine du projet) :
    python -I scripts/music_montage.py [--variante-intro lavee|brute] [--sans-filtre-final]

Entrée  : work/music/golden-ascent.mp3 (décodé en 48 kHz par ffmpeg, rééchantillonnage soxr)
Sorties : work/music/golden-ascent-montage.wav        (48 kHz, 24 bits, stéréo, 2 280 960 échantillons)
          work/music/golden-ascent-montage-apercu.mp3 (aperçu 192 kb/s)
          film/audio/golden-ascent-montage.wav        (copie lue par HyperFrames, hors git comme tout .wav)
          film/audio/montage-musique.json             (segments, raccords, temps en images de film)

Mesures (scripts/music_analyze.py + exploration, voir docs/montage-musique.md) :
  - tempo constant 92,00 battements/min, période 0,65216 s ; temps k du morceau à 0,056 + k × 0,65216 s ;
    premiers temps de mesure aux k multiples de 4 (changement d'accord) ;
  - intro (k 0 à 15, 0 à 10,43 s) : grosse caisse grave sur chaque temps (−4 dBFS) : pulsation marquée ;
  - partie principale A dès k = 16 (10,49 s, entrée de la basse, accord de ré) jusqu'à k = 95 ;
  - fin : dernière mesure k = 192 (125,27 s), arrêt net après k = 194 (126,7 s), queue de réverbération.

Montage (temps du film) :
  A  0,000 → 10,000 s  acte 1 : intro « lavée » (réverbération longue, sans attaques) et filtre qui se ferme
     10,000 → 10,600 s  silence
  B  10,600 → 40,600 s  source k 16 → avant k 62 (10,49 → 40,49 s) : premier temps fort au reveal (image 265)
     dernier temps : filtre passe-bas qui se referme (storyboard T7), coupure juste avant le temps k 62
     40,600 → 41,252 s  silence d'un temps (le temps k 62 est muet)
  C  41,252 → 47,520 s  source k 188 → fin (122,66 → 128,93 s) : dernière mesure, arrêt du morceau, queue
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import argparse
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import scipy.signal as ss
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "work" / "music" / "golden-ascent.mp3"
OUT_WAV = ROOT / "work" / "music" / "golden-ascent-montage.wav"
OUT_MP3 = ROOT / "work" / "music" / "golden-ascent-montage-apercu.mp3"
FILM_AUDIO = ROOT / "film" / "audio"

SR = 48000
FPS = 25
IMAGES_FILM = 1188      # 47,52 s (v2 : voix réelle, +3 temps en P7 ; v1 : 1140 images, 45,6 s)
FILM_S = IMAGES_FILM / FPS
N_FILM = int(round(FILM_S * SR))  # 2 280 960

PERIOD = 0.65216        # s, 92,002 battements/min (recherche sur grille des attaques)
PHASE = 0.056           # s, temps k = 0 du morceau
REVEAL_S = 10.6         # image 265 : premier temps fort
ACTE1_END_S = 10.0      # coupure de l'acte 1
K_REVEAL = 16           # premier temps de la partie principale (entrée de la basse)
TEMPS_AJOUTES = 3       # v2 : temps ajoutés à la partie B, pris en continu (k 59, 60, 61)
K_CUT = 59 + TEMPS_AJOUTES  # = 62 : temps rendu muet (3e temps de la mesure k 60) : silence avant P8
K_RESUME = 188          # premier temps de l'avant-dernière mesure du morceau
N_RESUME = K_CUT - K_REVEAL + 1  # = 47 : rang du temps de reprise sur la grille du film
TRIM_DB = -1.5          # marge pour l'export 24 bits (le master Artlist crête à +0,6 dBFS)
FADE_IN = 0.010         # micro-fondu d'entrée (s), fini 1 ms avant l'attaque
FADE_OUT = 0.020        # micro-fondu de sortie (s)


def decode() -> np.ndarray:
    tmp = ROOT / "work" / "music" / "_golden-ascent-48k.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(SRC),
                    "-af", "aresample=48000:resampler=soxr:precision=28", "-c:a", "pcm_f32le", str(tmp)],
                   check=True)
    x, sr = sf.read(tmp, dtype="float64", always_2d=True)
    tmp.unlink()
    assert sr == SR
    return x


def t_grid(k: int) -> float:
    return PHASE + k * PERIOD


def attack(x: np.ndarray, k: int) -> float:
    """Instant d'attaque du temps k : plus forte montée de l'enveloppe aiguë (> 2 kHz, fenêtre 1 ms)
    dans ±12 ms autour de la grille."""
    m = x.mean(axis=1)
    sos = ss.butter(2, 2000, "highpass", fs=SR, output="sos")
    t0 = t_grid(k)
    a, b = int((t0 - 0.05) * SR), int((t0 + 0.05) * SR)
    h = ss.sosfilt(sos, m[a:b])
    w = int(0.001 * SR)
    e = 10 * np.log10(np.convolve(h ** 2, np.ones(w) / w, mode="same") + 1e-12)
    step = int(0.0005 * SR)
    idx = np.arange(int(0.038 * SR), int(0.062 * SR), step)
    rise = e[idx + step] - e[idx - step]
    i = idx[int(np.argmax(rise))]
    return (a + i) / SR


def stft_lowpass(seg: np.ndarray, fc_of_t, t_offset: float) -> np.ndarray:
    """Passe-bas variable dans le temps (Butterworth d'ordre 2 en module), appliqué par STFT.
    fc_of_t(t) renvoie la fréquence de coupure (Hz) au temps t (s, temps du segment + t_offset);
    None = pas de filtrage."""
    nper, nover = 4096, 3072
    out = np.zeros_like(seg)
    for c in range(seg.shape[1]):
        f, tt, Z = ss.stft(seg[:, c], fs=SR, window="hann", nperseg=nper, noverlap=nover, boundary="even")
        for j, t in enumerate(tt):
            fc = fc_of_t(t + t_offset)
            if fc is not None:
                Z[:, j] *= 1.0 / np.sqrt(1.0 + (f / fc) ** 4)
        _, y = ss.istft(Z, fs=SR, window="hann", nperseg=nper, noverlap=nover, boundary=True)
        out[:, c] = y[: seg.shape[0]]
    return out


def ramp(n: int, up: bool) -> np.ndarray:
    r = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, n))  # demi-cosinus
    return r if up else r[::-1]


def acte1(x: np.ndarray, variante: str) -> np.ndarray:
    """Nappe de l'acte 1 (film 0 → 10,0 s) tirée de l'intro (même tonalité, accord tendu A/G#/A#).
    lavee : réverbération longue 100 % mouillée → plus aucune attaque (la grosse caisse disparaît
            dans la nappe) ; brute : intro filtrée seulement (pulsation encore audible)."""
    n = int(ACTE1_END_S * SR)
    src = x[:n].copy()
    src = ss.sosfilt(ss.butter(4, 110, "highpass", fs=SR, output="sos"), src, axis=0)  # retire le grave de la grosse caisse
    if variante == "lavee":
        rng = np.random.default_rng(20261014)
        L = int(5.0 * SR)
        t = np.arange(L) / SR
        rt60 = 3.5
        env = np.exp(-6.9078 * t / rt60)
        env[: int(0.03 * SR)] *= np.linspace(0, 1, int(0.03 * SR))  # attaque douce de la réverbération
        wet = np.zeros_like(src)
        for c in range(2):
            noise = rng.standard_normal(L)
            noise = ss.sosfilt(ss.butter(1, 4500, "lowpass", fs=SR, output="sos"), noise)
            ir = noise * env
            ir /= np.sqrt((ir ** 2).sum())
            wet[:, c] = ss.fftconvolve(src[:, c], ir)[:n]
        y = wet
    else:
        y = src
    # Le filtre se ferme : 6 kHz → 500 Hz, de plus en plus vite (la tension monte)
    def fc(tt):
        u = min(max(tt / ACTE1_END_S, 0.0), 1.0) ** 1.4
        return 6000.0 * (500.0 / 6000.0) ** u
    y = stft_lowpass(y, fc, 0.0)
    return y


def rms_db(y: np.ndarray) -> float:
    return 10 * np.log10((y ** 2).mean() + 1e-12)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variante-intro", choices=["lavee", "brute"], default="lavee")
    ap.add_argument("--sans-filtre-final", action="store_true")
    ap.add_argument("--suffixe", default="")
    args = ap.parse_args()

    x = decode()
    a16, a59, a188 = attack(x, K_REVEAL), attack(x, K_CUT), attack(x, K_RESUME)
    n_main = K_CUT - K_REVEAL                     # 46 temps joués
    tau_cut = REVEAL_S + (a59 - a16)              # instant (film) où tomberait le temps muet
    tau_resume = REVEAL_S + N_RESUME * PERIOD     # reprise sur la grille continue du film
    off_b = REVEAL_S - a16
    off_c = tau_resume - a188

    out = np.zeros((N_FILM, 2))

    # --- A : acte 1 -----------------------------------------------------------------
    yA = acte1(x, args.variante_intro)
    # niveau : nappe 9 dB sous la partie principale au départ, 7 dB sous à la fin (elle se resserre)
    ref_main = rms_db(x[int(a16 * SR): int(a59 * SR)])
    nA = yA.shape[0]
    third = slice(int(1.0 * SR), int(4.0 * SR))
    if args.variante_intro == "lavee":
        g0 = 10 ** ((ref_main - 9.0 - rms_db(yA[third])) / 20)
        gain = g0 * 10 ** (np.linspace(0, 2.0, nA) / 20)
    else:  # intro brute : niveau d'origine du morceau (ses crêtes de grosse caisse interdisent de remonter)
        gain = np.ones(nA)
    yA = yA * gain[:, None]
    yA[: int(0.010 * SR)] *= ramp(int(0.010 * SR), True)[:, None]
    nf = int(0.025 * SR)
    yA[-nf:] *= ramp(nf, False)[:, None]          # coupure à 10,000 s (micro-fondu 25 ms)
    out[:nA] += yA

    # --- B : partie principale ------------------------------------------------------------
    s0 = a16 - FADE_IN - 0.001
    s1 = a59 - 0.003
    segB = x[int(round(s0 * SR)): int(round(s1 * SR))].copy()
    nfi, nfo = int(FADE_IN * SR), int(FADE_OUT * SR)
    segB[:nfi] *= ramp(nfi, True)[:, None]
    segB[-nfo:] *= ramp(nfo, False)[:, None]
    if not args.sans_filtre_final:
        # « la musique se referme » (storyboard i945 à i970) : passe-bas 18 kHz → 1,2 kHz sur le dernier
        # temps et demi avant la coupure, en easeIn (lent puis plus franc)
        t_film0 = s0 + off_b
        fs_start, fs_end = tau_cut - 1.5 * PERIOD, tau_cut
        def fcB(tt):
            if tt < fs_start:
                return None
            u = min((tt - fs_start) / (fs_end - fs_start), 1.0) ** 2
            return 18000.0 * (1200.0 / 18000.0) ** u
        k0 = int((fs_start - 0.3 - t_film0) * SR)
        tail = stft_lowpass(segB[k0:], fcB, t_film0 + k0 / SR)
        segB[k0 + int(0.1 * SR):] = tail[int(0.1 * SR):]
    iB = int(round((s0 + off_b) * SR))
    out[iB: iB + segB.shape[0]] += segB

    # --- C : fin du morceau ---------------------------------------------------------------
    c0 = a188 - FADE_IN - 0.001
    iC = int(round((c0 + off_c) * SR))
    segC = x[int(round(c0 * SR)): int(round(c0 * SR)) + (N_FILM - iC)].copy()
    segC[:nfi] *= ramp(nfi, True)[:, None]
    out[iC: iC + segC.shape[0]] += segC
    # aucune enveloppe de fin : la queue de réverbération du morceau s'éteint d'elle-même

    out *= 10 ** (TRIM_DB / 20)
    assert out.shape[0] == N_FILM
    peak = np.abs(out).max()
    assert peak < 1.0, peak

    # --- Arrêt du morceau : l'enveloppe (20 ms) passe 20 dB sous le niveau de la dernière mesure --
    m = x.mean(axis=1)
    w = int(0.020 * SR)
    ref = rms_db(m[int(t_grid(192) * SR): int(t_grid(194) * SR)][:, None])
    seg = m[int(t_grid(194) * SR): int((t_grid(194) + 1.0) * SR)]
    env = 10 * np.log10(np.convolve(seg ** 2, np.ones(w) / w, mode="same") + 1e-12)
    stop_src = t_grid(194) + np.where(env > ref - 20)[0][-1] / SR

    suffix = args.suffixe
    wav = OUT_WAV.with_name(OUT_WAV.stem + suffix + ".wav")
    mp3 = OUT_MP3.with_name(OUT_MP3.stem.replace("-apercu", suffix + "-apercu") + ".mp3")
    sf.write(wav, out, SR, subtype="PCM_24")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav),
                    "-c:a", "libmp3lame", "-b:a", "192k", str(mp3)], check=True)

    # --- Grille des temps du film -------------------------------------------------------
    def frame(t):
        return int(round(t * FPS))
    beats = []
    for n in range(0, n_main):
        k = K_REVEAL + n
        t = REVEAL_S + (t_grid(k) - t_grid(K_REVEAL))
        beats.append({"n": n, "t": round(t, 4), "image": frame(t), "premier_temps": n % 4 == 0,
                      "source_k": k, "source_t": round(t_grid(k), 4), "joue": True})
    beats.append({"n": n_main, "t": round(tau_cut, 4), "image": frame(tau_cut), "premier_temps": False,
                  "source_k": K_CUT, "source_t": round(t_grid(K_CUT), 4), "joue": False,
                  "note": "temps muet : la musique se coupe juste avant (silence d'un temps)"})
    for j, k in enumerate(range(K_RESUME, 195)):
        t = tau_resume + (t_grid(k) - t_grid(K_RESUME))
        beats.append({"n": N_RESUME + j, "t": round(t, 4), "image": frame(t), "premier_temps": (k % 4 == 0),
                      "source_k": k, "source_t": round(t_grid(k), 4), "joue": True})
    stop_film = stop_src + off_c

    meta = {
        "fichier": "work/music/golden-ascent-montage.wav (copie : film/audio/golden-ascent-montage.wav)",
        "source": "work/music/golden-ascent.mp3 (Artlist, « Golden Ascent », Alex MakeMusic, 130,3 s)",
        "variante_intro": args.variante_intro, "filtre_final": not args.sans_filtre_final,
        "duree_s": FILM_S, "images": IMAGES_FILM, "fps": FPS, "sr": SR, "trim_db": TRIM_DB,
        "tempo_bpm": round(60 / PERIOD, 3), "periode_s": PERIOD, "images_par_temps": round(PERIOD * FPS, 3),
        "attaques_source_s": {"k16": round(a16, 4), f"k{K_CUT}": round(a59, 4), "k188": round(a188, 4)},
        "segments": [
            {"id": "A", "role": "acte 1 : nappe sans pulsation (intro lavée), filtre qui se ferme",
             "film_s": [0.0, ACTE1_END_S], "source_s": [0.0, ACTE1_END_S], "traitement": args.variante_intro},
            {"id": "silence-1", "film_s": [ACTE1_END_S, REVEAL_S]},
            {"id": "B", "role": "partie principale : premier temps fort au reveal",
             "film_s": [round(s0 + off_b, 4), round(s1 + off_b, 4)], "source_s": [round(s0, 4), round(s1, 4)],
             "source_temps_k": [K_REVEAL, K_CUT - 1]},
            {"id": "silence-2", "film_s": [round(s1 + off_b, 4), round(c0 + off_c, 4)],
             "note": f"un temps de silence (temps k {K_CUT} muet)"},
            {"id": "C", "role": "fin du morceau : dernière mesure, arrêt, queue de réverbération",
             "film_s": [round(c0 + off_c, 4), FILM_S], "source_s": [round(c0, 4), round(c0 + (N_FILM - iC) / SR, 4)],
             "source_temps_k": [K_RESUME, 194], "arret_morceau_film_s": round(stop_film, 3),
             "arret_morceau_image": frame(stop_film)},
        ],
        "raccords": [
            {"film_s": ACTE1_END_S, "type": "coupure de la nappe (micro-fondu 25 ms)"},
            {"film_s": REVEAL_S, "image": 265, "type": "entrée sur le premier temps k 16 (micro-fondu 10 ms avant l'attaque)"},
            {"film_s": round(tau_cut, 4), "image": frame(tau_cut), "type": f"coupure juste avant le temps k {K_CUT} (micro-fondu 20 ms), après un passe-bas qui se referme"},
            {"film_s": round(tau_resume, 4), "image": frame(tau_resume), "type": "entrée sur le premier temps k 188 (micro-fondu 10 ms avant l'attaque)"},
        ],
        "temps": beats,
    }
    FILM_AUDIO.mkdir(parents=True, exist_ok=True)
    if not suffix:
        shutil.copyfile(wav, FILM_AUDIO / "golden-ascent-montage.wav")
        with open(FILM_AUDIO / "montage-musique.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: meta[k] for k in ("tempo_bpm", "attaques_source_s", "segments", "raccords")},
                     ensure_ascii=False, indent=1))
    print("crête échantillon %.2f dBFS" % (20 * np.log10(peak)))


if __name__ == "__main__":
    main()
