"""Contrôle réplique par réplique de la voix off v4.1 (Anna, eleven_v4) contre docs/script-final.md,
puis export des répliques retenues.

Usage : python -I scripts/vo_qc_lines.py
        python -I scripts/vo_qc_lines.py --decouper <fichier> <id1,id2,...> <t1,t2,...>
        (découpe une génération groupée en répliques avant le contrôle)

Entrées
- docs/script-final.md : texte et fenêtre cible de chaque réplique (film) ; répliques des extraits.
- work/vo-raw/v41/takes.json : prises brutes téléchargées (id de réplique -> liste de prises,
  avec generation_id ElevenLabs, texte envoyé, fichier mp3).

Contrôles (par prise)
- Texte : transcription locale faster-whisper large-v3, comparée mot à mot au script après
  normalisation (accents, casse, pluriels muets). « Lili » est accepté pour « Lilie ».
- Prononciation : faster-whisper small, plus « littéral » à l'oreille, pour « pelviennes »
  (large-v3 corrige « pélevienne » en « pelviennes », vérifié sur les 4 prises de la maquette)
  et pour « Hé/Hey » de « Hey Lilie ».
- Durée de parole utile (silences de début et de fin coupés) comparée à la fenêtre cible :
  tolérance de dépassement 0,3 s.
- Son : crête < -1 dBFS, bruit de fond, pas de coupure au début ni à la fin.

Sorties
- assets/vo/lignes/<id>.wav : prise retenue, silences de tête et de queue ramenés à ~60 ms
  d'air (détection à 5 ms près), 48 kHz mono 24 bits, volume NON normalisé.
- assets/vo/lignes.json : récapitulatif par réplique.
- work/vo-raw/v41/qc.json : détail de chaque prise testée.
"""
import difflib
import json
import re
import subprocess
import sys
import unicodedata
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "work" / "vo-raw" / "v41"
OUT_DIR = ROOT / "assets" / "vo" / "lignes"
OUT_JSON = ROOT / "assets" / "vo" / "lignes.json"
CACHE = RAW / "qc_cache.json"
SR = 48000
AIR = 0.060            # air conservé avant/après la parole
TOL = 0.30             # dépassement toléré sur la fenêtre cible (s)
FLOW_ID = "x9Q8az8MBLyRiCi3yVO0"
VOICE = "Anna P - Animatrice Podcast/ livre audio (cuo3D4C6LVenyV7b2Kpd)"

ORDER = ["1a", "1b", "1c", "1d", "1e", "P2", "P3", "P4a", "P4b", "P5", "P6", "P7", "P8", "P9",
         "A_ouv", "B_ouv", "B_corps", "C_ouv"]

# Syllabes prononcées (comptées à la main, e muets exclus) pour le débit.
SYLL = {"1a": 8, "1b": 7, "1c": 9, "1d": 6, "1e": 9, "P2": 18, "P3": 14, "P4a": 14, "P4b": 13,
        "P5": 15, "P6": 12, "P7": 27, "P8": 5, "P9": 6,
        "A_ouv": 11, "B_ouv": 13, "B_corps": 10, "C_ouv": 11}

# Fenêtres des extraits : storyboard v4 (« 0-3,0 problème », extrait B « 3,0-7,0 P4 (trame) »).
EXTRACT_WINDOWS = {"A_ouv": (0.0, 3.0), "B_ouv": (0.0, 3.0), "B_corps": (3.0, 7.0), "C_ouv": (0.0, 3.0)}
EXTRACT_IDS = {("A", "ouverture"): "A_ouv", ("B", "ouverture"): "B_ouv",
               ("B", "corps"): "B_corps", ("C", "ouverture"): "C_ouv"}


def fnum(s):
    return float(s.replace(",", "."))


def parse_script():
    txt = (ROOT / "docs" / "script-final.md").read_text(encoding="utf-8")
    lines, p4 = {}, 0
    for row in txt.splitlines():
        m = re.match(r"^\|\s*(1[a-e]|P\d)\s*\|\s*([\d,]+)\s*→\s*([\d,]+)\s*\|\s*([^|]*?)\s*\|", row)
        if m:
            pid, a, b, voice = m.groups()
            if not voice:
                continue
            if pid == "P4":
                pid = "P4a" if p4 == 0 else "P4b"
                p4 += 1
            lines[pid] = dict(texte=voice, fenetre=(fnum(a), fnum(b)))
            continue
        m = re.match(r"^\|\s*([ABC]) \((ouverture|corps)\)\s*\|\s*([^|]+?)\s*\|", row)
        if m:
            lid = EXTRACT_IDS[(m.group(1), m.group(2))]
            lines[lid] = dict(texte=m.group(3), fenetre=EXTRACT_WINDOWS[lid])
    return lines


# ---------- texte ----------
# « Hé Lili » est souvent transcrit en un mot (« élili », « HeyLili ») : même son /e lili/.
SPLIT = {"postpartum": "post partum", "preredige": "pre redige", "heylili": "he lili",
         "heylilie": "he lili", "helili": "he lili", "elili": "he lili", "etlili": "he lili",
         "sagefemme": "sage femme"}
SAME = {"lilie": "lili", "lily": "lili", "lilly": "lili", "hey": "he", "aux": "au"}


def tokens(s):
    s = s.lower().replace("œ", "oe")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    out = []
    for t in re.findall(r"[a-z]+", s):
        out += SPLIT.get(t, t).split()
    return out


def canon(t):
    t = SAME.get(t, t)
    if len(t) > 3 and t[-1] in "sx":
        t = t[:-1]
    if len(t) > 3 and t.endswith("e"):
        t = t[:-1]
    return t


# Variantes acceptées à l'écoute (même son) : « Hé » de « Hey Lilie » entendu « et ».
ALT = {"P9": {"he": {"he", "et", "e"}}}


def compare(lid, ref, hyp):
    R = [canon(t) for t in tokens(ref)]
    H = [canon(t) for t in tokens(hyp)]
    alt = ALT.get(lid, {})
    sm = difflib.SequenceMatcher(a=R, b=H, autojunk=False)
    missing, extra = [], []
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "equal":
            continue
        if op == "replace" and a2 - a1 == b2 - b1 and all(
                h in alt.get(r, ()) for r, h in zip(R[a1:a2], H[b1:b2])):
            continue
        if op in ("delete", "replace"):
            missing += R[a1:a2]
        if op in ("insert", "replace"):
            extra += H[b1:b2]
    return round(sm.ratio(), 3), missing, extra


def acoustic_checks(lid, small_txt):
    """Contrôles de prononciation sur la transcription « littérale » (small)."""
    probs = []
    T = tokens(small_txt)
    if lid == "P2":
        if not any(t.startswith("pelvien") for t in T):
            bad = [t for t in T if "vien" in t]
            probs.append(f"« pelviennes » entendu « {' '.join(bad) or '?'} »")
    if lid == "P9":
        # attendu : ... par (hé|hey|et) lili   (tokens() a déjà séparé « élili » en « he lili »)
        ok = len(T) >= 2 and SAME.get(T[-1], T[-1]) == "lili" and SAME.get(T[-2], T[-2]) in ("he", "et", "e")
        if not ok:
            probs.append(f"« Hey Lilie » entendu « {' '.join(T[-3:])} »")
    return probs


# ---------- audio ----------
def load(path):
    base = ["ffmpeg", "-v", "error", "-i", str(path)]
    tail = ["-ac", "1", "-f", "f32le", "-"]
    for af in (["-af", "aresample=48000:resampler=soxr:precision=28"], ["-ar", str(SR)]):
        r = subprocess.run(base + af + tail, capture_output=True)
        if r.returncode == 0 and r.stdout:
            return np.frombuffer(r.stdout, dtype="<f4").astype(np.float64)
    raise RuntimeError(f"décodage impossible : {path}")


HOP, WIN = 240, 960   # 5 ms / 20 ms


def frame_db(x):
    if len(x) < WIN:
        x = np.pad(x, (0, WIN - len(x)))
    n = 1 + (len(x) - WIN) // HOP
    idx = np.arange(n) * HOP
    c = np.concatenate([[0.0], np.cumsum(x * x)])
    e = (c[idx + WIN] - c[idx]) / WIN
    return 10 * np.log10(e + 1e-20)


def span(active):
    """Premier et dernier indice d'une zone active soutenue (>= 50 % d'activité sur 50 ms)."""
    n, k = len(active), 10
    dens = np.convolve(active.astype(float), np.ones(k) / k, mode="full")[k - 1:]
    starts = np.where(active & (dens >= 0.5))[0]
    if not len(starts):
        return None
    dens_b = np.convolve(active[::-1].astype(float), np.ones(k) / k, mode="full")[k - 1:][::-1]
    ends = np.where(active & (dens_b >= 0.5))[0]
    return starts[0], ends[-1]


def analyse(x):
    db = frame_db(x)
    t = (np.arange(len(db)) * HOP + WIN / 2) / SR       # centre de chaque trame
    peak_f = db.max()
    sp = span(db > max(peak_f - 35, -60))                 # parole
    lo = span(db > max(peak_f - 45, -62))                 # parole + traînes douces / souffle
    if sp is None:
        return None
    s0, s1 = t[sp[0]], t[sp[1]]
    l0, l1 = (t[lo[0]], t[lo[1]]) if lo else (s0, s1)
    l0, l1 = min(l0, s0), max(l1, s1)
    dur_file = len(x) / SR
    # bruit de fond : trames hors zone, à plus de 50 ms de la zone basse
    outside = (t < l0 - 0.05) | (t > l1 + 0.05)
    noise = float(np.median(db[outside])) if outside.sum() >= 6 else None
    # pauses internes (silences >= 80 ms dans la zone de parole)
    inside = db[sp[0]:sp[1] + 1] <= max(peak_f - 35, -60)
    gaps, cur = [], 0
    for v in list(inside) + [False]:
        if v:
            cur += 1
        else:
            if cur * HOP / SR >= 0.08:
                gaps.append(cur * HOP / SR)
            cur = 0
    pause_max = max(gaps) if gaps else 0.0
    edge = int(0.005 * SR)                                # niveau des 5 premières / dernières ms
    head5 = 20 * np.log10(np.abs(x[:edge]).max() + 1e-20)
    tail5 = 20 * np.log10(np.abs(x[-edge:]).max() + 1e-20)
    sample_peak = 20 * np.log10(np.abs(x).max() + 1e-20)
    clip = np.abs(x) >= 0.99
    clip_runs = int(np.sum(clip[1:-1] & clip[:-2] & clip[2:])) if len(x) > 3 else 0
    i0, i1 = int(s0 * SR), int(s1 * SR)
    rms_speech = 10 * np.log10(np.mean(x[i0:i1] ** 2) + 1e-20) if i1 > i0 else None
    return dict(debut_parole=s0, fin_parole=s1, debut_son=l0, fin_son=l1, duree_fichier_brut=dur_file,
                duree_utile=s1 - s0, tete_silence=l0 - WIN / 2 / SR, queue_silence=dur_file - l1 - WIN / 2 / SR,
                respiration_tete=max(0.0, s0 - l0), bruit_fond_dbfs=noise, pause_max=pause_max,
                silences_internes=sum(gaps), parole_nette=(s1 - s0) - sum(gaps),
                niveau_5ms_debut_dbfs=float(head5), niveau_5ms_fin_dbfs=float(tail5),
                crete_echantillon_dbfs=float(sample_peak), echantillons_satures=clip_runs,
                rms_parole_dbfs=rms_speech)


def write_wav24(path, y):
    y = np.clip(y, -1.0, 1.0 - 1 / 8388608)
    q = np.round(y * 8388607).astype("<i4")
    b = q.view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(3)
        w.setframerate(SR)
        w.writeframes(b)


def export(x, a, path):
    """Coupe à ~60 ms d'air ; si la prise brute en a moins, complète par du silence numérique."""
    s = int(round((a["debut_son"] - AIR) * SR))
    e = int(round((a["fin_son"] + AIR) * SR))
    pad0, pad1 = max(0, -s), max(0, e - len(x))
    y = x[max(0, s):min(len(x), e)].copy()
    f = int(0.005 * SR)                                   # fondu 5 ms anti-clic aux bords coupés
    ramp = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, f))
    if not pad0:
        y[:f] *= ramp
    if not pad1:
        y[-f:] *= ramp[::-1]
    y = np.concatenate([np.zeros(pad0), y, np.zeros(pad1)])
    write_wav24(path, y)
    return dict(debut_coupe_s=round(max(0, s) / SR, 3), fin_coupe_s=round(min(len(x), e) / SR, 3),
                silence_ajoute_tete_s=round(pad0 / SR, 3), silence_ajoute_queue_s=round(pad1 / SR, 3),
                duree_fichier_s=round(len(y) / SR, 3))


def ebur128(path):
    r = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", str(path), "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    summ = r.stderr[r.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s*(-?[\d.]+|-inf)\s*LUFS", summ)
    tp = re.search(r"True peak:\s*Peak:\s*(-?[\d.]+|-inf)\s*dBFS", summ, re.S)
    f = lambda m: (None if not m or m.group(1) == "-inf" else float(m.group(1)))
    return f(i), f(tp)


# ---------- transcription ----------
_models = {}


def transcribe(path, size):
    from faster_whisper import WhisperModel
    if size not in _models:
        _models[size] = WhisperModel(size, device="cpu", compute_type="int8", cpu_threads=16)
    segs, _ = _models[size].transcribe(str(path), language="fr", beam_size=5, temperature=0.0,
                                       condition_on_previous_text=False, vad_filter=False)
    return " ".join(s.text.strip() for s in segs).strip()


def npy(o):
    """Types numpy -> types JSON."""
    return o.item() if hasattr(o, "item") else str(o)


def decouper(src, ids, cuts):
    """Découpe une génération groupée (plusieurs répliques) en prises séparées.
    src : fichier dans work/vo-raw/v41 ; ids : répliques dans l'ordre ; cuts : temps de coupe (s),
    pris au milieu des silences entre paragraphes (repérés à l'énergie, vérifiés par horodatage des mots)."""
    takes = json.loads((RAW / "takes.json").read_text(encoding="utf-8"))
    parent = next(t for v in takes.values() for t in v if t["file"] == src)
    x = load(RAW / src)
    bounds = [0.0] + cuts + [len(x) / SR]
    for k, lid in enumerate(ids):
        a, b = bounds[k], bounds[k + 1]
        fn = f"{lid}__{parent['generation_id']}__seg{k + 1}.wav"
        write_wav24(RAW / fn, x[int(a * SR):int(b * SR)])
        entry = dict(parent, file=fn, segment_de=src, segment_s=[round(a, 3), round(b, 3)],
                     segment=f"{k + 1}/{len(ids)}")
        takes[lid] = [t for t in takes.get(lid, []) if t["file"] != fn] + [entry]
        print(lid, fn, f"{a:.3f}-{b:.3f} s")
    (RAW / "takes.json").write_text(json.dumps(takes, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    script = parse_script()
    takes = json.loads((RAW / "takes.json").read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    detail, result = {}, []
    for lid in ORDER:
        if lid not in takes:
            continue
        ref = script[lid]["texte"]
        w0, w1 = script[lid]["fenetre"]
        win = round(w1 - w0, 3)
        cands = []
        for tk in takes[lid]:
            f = RAW / tk["file"]
            c = cache.setdefault(tk["file"], {})
            if "large" not in c:
                c["large"] = transcribe(f, "large-v3")
            if "small" not in c:
                c["small"] = transcribe(f, "small")
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
            x = load(f)
            a = analyse(x)
            probs, notes = [], []
            ratio, missing, extra = compare(lid, ref, c["large"])
            if missing or extra:
                probs.append(f"texte : manquants {missing}, en trop {extra}")
            probs += acoustic_checks(lid, c["small"])
            if a is None:
                probs.append("aucune parole détectée")
            else:
                if a["crete_echantillon_dbfs"] >= -1.0 or a["echantillons_satures"]:
                    probs.append(f"saturation (crête {a['crete_echantillon_dbfs']:.1f} dBFS)")
                if a["bruit_fond_dbfs"] is not None and a["bruit_fond_dbfs"] > -60:
                    probs.append(f"bruit de fond {a['bruit_fond_dbfs']:.0f} dBFS")
                # coupure nette = son déjà fort dans les 5 premières/dernières ms du fichier brut
                if a["niveau_5ms_debut_dbfs"] > -45:
                    probs.append(f"coupure au début ({a['niveau_5ms_debut_dbfs']:.0f} dBFS dès le 1er échantillon)")
                elif a["tete_silence"] < 0.02:
                    notes.append(f"attaque sans silence avant (1res 5 ms à {a['niveau_5ms_debut_dbfs']:.0f} dBFS, "
                                 "pas de coupure nette) : air complété par du silence")
                if a["niveau_5ms_fin_dbfs"] > -45:
                    probs.append(f"coupure à la fin ({a['niveau_5ms_fin_dbfs']:.0f} dBFS sur les 5 dernières ms)")
                elif a["queue_silence"] < 0.02:
                    notes.append("fin sans silence après (pas de coupure nette) : air complété par du silence")
                if a["respiration_tete"] > 0.15:
                    notes.append(f"souffle/attaque douce en tête ({a['respiration_tete'] * 1000:.0f} ms) gardé")
                if a["pause_max"] > 0.7:
                    notes.append(f"pause interne de {a['pause_max']:.2f} s")
            # point au milieu de la réplique dans le script mais pas dans la transcription :
            # l'intonation finale est peut-être suspendue (à écouter)
            if ref.rstrip(" .").count(".") > c["large"].rstrip(" .").count("."):
                notes.append("point du script entendu comme une virgule : intonation peut-être suspendue, à écouter")
            over = float(round(a["duree_utile"] - win, 3)) if a else None
            if over is not None and over > TOL:
                notes.append(f"dépasse la fenêtre de {over:.2f} s (tolérance {TOL} s)")
            verdict = "ÉCHEC" if probs else ("À SURVEILLER" if (over is not None and over > TOL) else "OK")
            cands.append(dict(tk=tk, a=a, x=x, large=c["large"], small=c["small"], ratio=ratio,
                              probs=probs, notes=notes, over=over, verdict=verdict))
        rank = {"OK": 0, "À SURVEILLER": 1, "ÉCHEC": 2}
        cands.sort(key=lambda k: (rank[k["verdict"]], max(k["over"] or 0, 0), -k["ratio"]))
        best = cands[0]
        detail[lid] = [dict(generation_id=k["tk"]["generation_id"], fichier=k["tk"]["file"], verdict=k["verdict"],
                            problemes=k["probs"], remarques=k["notes"], transcription=k["large"],
                            transcription_acoustique=k["small"],
                            duree_utile_s=round(k["a"]["duree_utile"], 3) if k["a"] else None,
                            mesures={kk: (round(v, 3) if isinstance(v, float) else v) for kk, v in (k["a"] or {}).items()})
                       for k in cands]
        a = best["a"]
        out_wav = OUT_DIR / f"{lid}.wav"
        cut = export(best["x"], a, out_wav) if a else {}
        lufs, tp = ebur128(out_wav) if a else (None, None)
        dur = round(a["duree_utile"], 2) if a else None
        rec = dict(
            id=lid, texte=ref, texte_envoye=best["tk"]["prompt"],
            fichier=f"assets/vo/lignes/{lid}.wav",
            duree_utile_s=dur, duree_fichier_s=cut.get("duree_fichier_s"),
            fenetre_cible=dict(debut_s=w0, fin_s=w1, duree_s=win,
                               source=("storyboard v4, section extraits" if lid in EXTRACT_WINDOWS
                                       else "docs/script-final.md")),
            ecart_fenetre_s=best["over"],
            depassement_s=round(max(best["over"], 0), 2) if best["over"] is not None else None,
            dans_tolerance=(best["over"] is not None and best["over"] <= TOL),
            debit_syll_s=round(SYLL[lid] / a["duree_utile"], 2) if a else None,
            parole_nette_s=round(a["parole_nette"], 2) if a else None,
            silences_internes_s=round(a["silences_internes"], 2) if a else None,
            transcription=best["large"], transcription_acoustique=best["small"],
            verdict=best["verdict"], problemes=best["probs"], remarques=best["notes"],
            generation_id=best["tk"]["generation_id"], node_id=best["tk"]["node_id"],
            segment=({"de": best["tk"]["segment_de"], "s": best["tk"]["segment_s"], "rang": best["tk"]["segment"]}
                     if "segment_de" in best["tk"] else None),
            credits=best["tk"].get("credits"),
            niveau=dict(lufs_integre=lufs, crete_vraie_dbtp=tp,
                        crete_echantillon_dbfs=round(a["crete_echantillon_dbfs"], 1) if a else None,
                        rms_parole_dbfs=round(a["rms_parole_dbfs"], 1) if a and a["rms_parole_dbfs"] else None),
            controles=dict(saturation=not (a and a["crete_echantillon_dbfs"] < -1.0 and not a["echantillons_satures"]),
                           bruit_fond_dbfs=round(a["bruit_fond_dbfs"], 1) if a and a["bruit_fond_dbfs"] is not None else None,
                           silence_tete_brut_s=round(a["tete_silence"], 3) if a else None,
                           silence_queue_brut_s=round(a["queue_silence"], 3) if a else None,
                           pause_interne_max_s=round(a["pause_max"], 2) if a else None,
                           coupe=cut),
            prises_testees=len(cands))
        result.append(rec)
        print(f"{lid:7s} {best['verdict']:13s} utile {dur:5.2f} s / fenêtre {win:4.2f} s "
              f"(écart {best['over']:+.2f}) | {rec['debit_syll_s']:.2f} syl/s | I {lufs} LUFS, TP {tp} dBTP, "
              f"crête {rec['niveau']['crete_echantillon_dbfs']} dBFS | « {best['large']} » "
              f"/ small « {best['small']} » {('| ' + '; '.join(best['probs'] + best['notes'])) if best['probs'] or best['notes'] else ''}")
    meta = dict(voix=VOICE, modele="eleven_v4", flow_id=FLOW_ID, balise="[calm, measured]",
                format="WAV 48 kHz mono 24 bits, volume non normalisé, ~60 ms d'air en tête et en queue",
                tolerance_depassement_s=TOL, controle="scripts/vo_qc_lines.py (faster-whisper large-v3 + small)")
    OUT_JSON.write_text(json.dumps(dict(meta=meta, lignes=result), ensure_ascii=False, indent=1, default=npy),
                        encoding="utf-8")
    (RAW / "qc.json").write_text(json.dumps(detail, ensure_ascii=False, indent=1, default=npy), encoding="utf-8")


if __name__ == "__main__":
    # python -I scripts/vo_qc_lines.py --decouper <fichier> <id1,id2,...> <t1,t2,...>
    if len(sys.argv) > 1 and sys.argv[1] == "--decouper":
        decouper(sys.argv[2], sys.argv[3].split(","), [float(t) for t in sys.argv[4].split(",")])
    else:
        sys.exit(main())
