"""Mesure de « Golden Ascent » : tempo, temps, premiers temps de mesure, sections, niveaux.

Usage : python -I scripts/music_analyze.py <fichier.wav 48 kHz> <sortie.json>
Sortie : JSON avec le tempo (régression sur les temps détectés), la liste des temps,
la phase des premiers temps (mesure à 4 temps), un profil par mesure (RMS, flux d'attaque,
graves, brillance) et des marqueurs de section (nouveauté spectrale).
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import json
import sys

import librosa
import numpy as np
import soundfile as sf

SR = 48000
HOP = 240  # 5 ms : précision des attaques


def main(src: str, out: str) -> None:
    y, sr = sf.read(src, dtype="float32", always_2d=True)
    assert sr == SR, sr
    mono = y.mean(axis=1)
    dur = len(mono) / SR

    # --- Attaques et temps -------------------------------------------------
    onset = librosa.onset.onset_strength(y=mono, sr=SR, hop_length=HOP, aggregate=np.median)
    t_on = librosa.frames_to_time(np.arange(len(onset)), sr=SR, hop_length=HOP)
    tempo0, beats = librosa.beat.beat_track(onset_envelope=onset, sr=SR, hop_length=HOP,
                                            start_bpm=92, tightness=400, units="time")
    beats = np.asarray(beats)
    # Affinage de chaque temps : pic d'attaque le plus proche (±40 ms)
    refined = []
    for b in beats:
        m = (t_on > b - 0.04) & (t_on < b + 0.04)
        if m.any():
            idx = np.where(m)[0]
            refined.append(float(t_on[idx[np.argmax(onset[idx])]]))
        else:
            refined.append(float(b))
    refined = np.array(refined)

    # Régression linéaire temps = t0 + n * période, sur la zone pulsée (après l'intro)
    n = np.arange(len(refined))
    sel = refined > 10.5
    A = np.vstack([n[sel], np.ones(sel.sum())]).T
    period, t0 = np.linalg.lstsq(A, refined[sel], rcond=None)[0]
    resid = refined[sel] - (t0 + period * n[sel])
    bpm = 60.0 / period

    # --- Bandes pour la phase des premiers temps ------------------------------
    S = np.abs(librosa.stft(mono, n_fft=4096, hop_length=HOP)) ** 2
    freqs = librosa.fft_frequencies(sr=SR, n_fft=4096)
    low = S[(freqs >= 30) & (freqs < 160)].sum(axis=0)
    low_flux = np.maximum(0, np.diff(np.log1p(low * 1e4), prepend=0))
    chroma = librosa.feature.chroma_stft(S=S, sr=SR, hop_length=HOP)

    def at(series, t, w=0.05):
        i0 = int(max(0, (t - w) * SR / HOP)); i1 = int((t + w) * SR / HOP) + 1
        i1 = min(i1, len(series))
        return float(series[i0:i1].max()) if i1 > i0 else 0.0

    # Grille idéale sur tout le morceau (temps réguliers), y compris l'intro
    k_first = int(np.floor((0 - t0) / period))
    grid = [t0 + k * period for k in range(k_first, int((dur - t0) / period) + 1)]
    grid = [g for g in grid if 0 <= g < dur]
    on_at = np.array([at(onset, g) for g in grid])
    low_at = np.array([at(low_flux, g) for g in grid])
    # Changement harmonique : distance de chroma entre la mesure avant et après le temps
    def chroma_change(g, w=0.3):
        a = int((g - w) * SR / HOP); b = int(g * SR / HOP); c = int((g + w) * SR / HOP)
        if a < 0 or c > chroma.shape[1]:
            return 0.0
        u = chroma[:, a:b].mean(axis=1); v = chroma[:, b:c].mean(axis=1)
        return float(1 - np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-9))
    ch_at = np.array([chroma_change(g) for g in grid])

    def z(x):
        return (x - x.mean()) / (x.std() + 1e-9)
    score = z(on_at) + z(low_at) + z(ch_at)
    phase_scores = []
    for p in range(4):
        idx = np.arange(p, len(grid), 4)
        phase_scores.append(float(score[idx].mean()))
    best = int(np.argmax(phase_scores))
    downbeats = [grid[i] for i in range(best, len(grid), 4)]

    # --- Profil par mesure ----------------------------------------------------
    rms = librosa.feature.rms(y=mono, frame_length=2048, hop_length=HOP)[0]
    cent = librosa.feature.spectral_centroid(S=S, sr=SR)[0]
    bars = []
    for i, d in enumerate(downbeats):
        e = downbeats[i + 1] if i + 1 < len(downbeats) else min(dur, d + 4 * period)
        a = int(d * SR / HOP); b = int(e * SR / HOP)
        r = rms[a:b]
        seg_on = onset[a:b]
        bars.append({
            "n": i, "start": round(d, 4), "end": round(e, 4),
            "rms_db": round(float(20 * np.log10(np.sqrt((r ** 2).mean()) + 1e-9)), 2),
            "peak_db": round(float(20 * np.log10(np.abs(mono[int(d*SR):int(e*SR)]).max() + 1e-9)), 2),
            "onset_mean": round(float(seg_on.mean()), 3),
            "onset_beat_contrast": round(float(np.mean([at(onset, d + j * period) for j in range(4)]) / (seg_on.mean() + 1e-9)), 2),
            "low_db": round(float(10 * np.log10(low[a:b].mean() + 1e-12)), 2),
            "centroid_hz": int(cent[a:b].mean()),
        })

    # --- Nouveauté (frontières de section) -----------------------------------
    mfcc = librosa.feature.mfcc(y=mono, sr=SR, n_mfcc=20, hop_length=HOP * 10)
    bar_feats = []
    for bdict in bars:
        a = int(bdict["start"] * SR / (HOP * 10)); b = max(a + 1, int(bdict["end"] * SR / (HOP * 10)))
        bar_feats.append(mfcc[:, a:b].mean(axis=1))
    F = np.array(bar_feats)
    F = (F - F.mean(0)) / (F.std(0) + 1e-9)
    nov = [0.0] + [float(np.linalg.norm(F[i] - F[i - 1])) for i in range(1, len(F))]
    for bdict, v in zip(bars, nov):
        bdict["novelty"] = round(v, 2)

    # --- Fin du morceau : décroissance ------------------------------------------
    env_db = 20 * np.log10(rms + 1e-9)
    t_rms = librosa.frames_to_time(np.arange(len(rms)), sr=SR, hop_length=HOP)
    tail = []
    for thr in (-30, -40, -50, -60):
        above = np.where(env_db > thr)[0]
        tail.append({"seuil_db": thr, "dernier_instant_au_dessus": round(float(t_rms[above[-1]]), 3) if len(above) else None})

    res = {
        "fichier": src, "duree_s": round(dur, 4), "sr": SR,
        "tempo_librosa": float(np.atleast_1d(tempo0)[0]),
        "tempo_regression_bpm": round(float(bpm), 4), "periode_s": round(float(period), 6),
        "t0_grille_s": round(float(t0), 5),
        "residu_temps_ms": {"moyen_abs": round(float(np.abs(resid).mean() * 1000), 2),
                             "max_abs": round(float(np.abs(resid).max() * 1000), 2)},
        "phase_scores": [round(s, 3) for s in phase_scores], "phase_premier_temps": best,
        "temps_detectes": [round(float(b), 4) for b in refined],
        "premiers_temps": [round(float(d), 4) for d in downbeats],
        "mesures": bars, "fin": tail,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(f"tempo librosa {res['tempo_librosa']:.2f} | régression {bpm:.3f} bpm, période {period:.5f} s, t0 {t0:.4f}")
    print(f"résidus : moyen {res['residu_temps_ms']['moyen_abs']} ms, max {res['residu_temps_ms']['max_abs']} ms")
    print("phases", res["phase_scores"], "-> premier temps phase", best)
    print("premiers temps (10 premiers) :", res["premiers_temps"][:10])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
