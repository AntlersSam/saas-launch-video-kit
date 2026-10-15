import sys, glob, os, json, re, unicodedata
from faster_whisper import WhisperModel
ref = ("Gagnez du temps et structurez vos prises en charge pelviennes avec Lilie. Avant la séance, votre patiente répond au questionnaire. "
       "Pendant la consultation, concentrez-vous sur l'échange. Lilie écoute et structure le bilan, trame par trame. "
       "Chaque test s'appuie sur des échelles validées. Le courrier est rédigé pour le médecin. "
       "Douleurs, post-partum, chirurgie : gynécologue, sage-femme et kiné partagent un même dossier, à chaque étape. "
       "Un standard clinique. Lilie. Par Hey Lilie.")
def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z]+", s)
R = norm(ref)
model = WhisperModel("small", device="cpu", compute_type="int8")
out = {}
for f in sorted(glob.glob(os.path.join(sys.argv[1], "vo_*.mp3"))):
    segs, info = model.transcribe(f, language="fr", beam_size=5)
    txt = " ".join(s.text.strip() for s in segs)
    H = norm(txt)
    # alignement simple : mots du script absents / mots en trop
    import difflib
    sm = difflib.SequenceMatcher(a=R, b=H)
    missing, extra = [], []
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op in ("delete", "replace"): missing += R[a1:a2]
        if op in ("insert", "replace"): extra += H[b1:b2]
    name = os.path.basename(f)[:-4]
    out[name] = dict(text=txt, ratio=round(sm.ratio(), 3), missing=missing, extra=extra)
    print(f"{name}: ressemblance {sm.ratio():.3f} | manquants {missing} | en trop {extra}")
json.dump(out, open(os.path.join(sys.argv[1], "..", "vo-qc.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
