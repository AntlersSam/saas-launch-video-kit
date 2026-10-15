/* Film de lancement : table des courbes de mouvement (cubic-bezier exactes, enregistrées dans GSAP : "rangement", "camera", "texte"...). Voir skills/saas-launch-video/references/grammaire-mouvement.md. */
 *
 * Chaque mouvement prend une courbe de cette table, jamais la courbe par défaut d'un logiciel.
 * Les six courbes de la table du storyboard, puis trois courbes d'appoint citées dans les transitions.
 *
 * Utilisation dans une composition (GSAP chargé avant ce fichier, voir index.html) :
 *   tl.fromTo(el, { y: 12, opacity: 0 }, { y: 0, opacity: 1, duration: LILIE.duree(6), ease: "texte" }, LILIE.local(494, "p4"));
 *   ou ease: LILIE.courbes.texte (fonction exacte, identique au nom enregistré).
 *
 * Les noms enregistrés dans GSAP ("arrivee", "texte", "camera"…) appellent la cubic-bezier EXACTE du
 * storyboard. Les équivalents GSAP nommés (gsap_proche) sont donnés pour référence seulement : ils sont
 * proches mais pas identiques (expo.out, en particulier, démarre plus sec que la bezier).
 * Interdits : back, elastic, bounce, steps, et toute courbe qui dépasse sa cible.
 */
(function () {
  "use strict";

  // Résolution exacte d'une cubic-bezier CSS (même méthode que les navigateurs : Newton puis dichotomie).
  function cubicBezier(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const sx = (t) => ((ax * t + bx) * t + cx) * t;
    const sy = (t) => ((ay * t + by) * t + cy) * t;
    const dsx = (t) => (3 * ax * t + 2 * bx) * t + cx;
    function solveX(x) {
      let t = x;
      for (let i = 0; i < 8; i++) {
        const err = sx(t) - x;
        if (Math.abs(err) < 1e-7) return t;
        const d = dsx(t);
        if (Math.abs(d) < 1e-6) break;
        t -= err / d;
      }
      let lo = 0, hi = 1;
      t = x;
      for (let i = 0; i < 40; i++) {
        const v = sx(t);
        if (Math.abs(v - x) < 1e-7) return t;
        if (x > v) lo = t; else hi = t;
        t = (lo + hi) / 2;
      }
      return t;
    }
    return function (p) {
      if (p <= 0) return 0;
      if (p >= 1) return 1;
      return sy(solveX(p));
    };
  }

  const TABLE = {
    // --- Les six courbes du storyboard ---------------------------------------------------------
    arrivee:  { bezier: [0.16, 1, 0.3, 1],   gsap_proche: "expo.out",     nom: "Arrivée (expo-out)",
                usage: "tout ce qui entre et se pose : départ vif en 3 à 4 i, arrivée amortie en 14 à 16 i" },
    texte:    { bezier: [0.33, 1, 0.68, 1],  gsap_proche: "power2.out",   nom: "Texte (easeOutCubic)",
                usage: "chaque mot monte de 12 px à travers un masque en 6 i, 3 i de décalage ; pastilles, badges, noms d'échelles" },
    camera:   { bezier: [0.65, 0, 0.35, 1],  gsap_proche: "power2.inOut", nom: "Caméra et transitions (easeInOutCubic)",
                usage: "poussées, reculs, bascule 3D, condensations ; les 30 à 40 % du début sont presque immobiles" },
    gravite:  { bezier: [0.32, 0, 0.67, 0],  gsap_proche: "power2.in",    nom: "Gravité et sorties (easeInCubic)",
                usage: "aimantation des dossiers (T1), recul du réseau (T7) ; ne s'arrête jamais à l'écran" },
    rotation: { bezier: [0.37, 0, 0.63, 1],  gsap_proche: "sine.inOut",   nom: "Rotations lentes (easeInOutSine)",
                usage: "pivots du cube, ondes de la consultation, retour au repos de la caméra" },
    derive:   { bezier: null,                gsap_proche: "none",         nom: "Dérive (linéaire)",
                usage: "seule courbe linéaire : dérive de fond presque invisible (2 px ou 0,5 % d'échelle en 2 s), sauf les 1,6 s finales" },
    // --- Courbes d'appoint citées dans les transitions T1 à T8 ---------------------------------
    rangement:  { bezier: [0.25, 1, 0.5, 1],  gsap_proche: "power3.out", nom: "Rangement (easeOutQuart)",
                  usage: "le cube prend du volume, badge et jetons qui se rangent" },
    effacement: { bezier: [0.12, 0, 0.39, 0], gsap_proche: "sine.in",    nom: "Effacement (easeInSine)",
                  usage: "mots qui s'effacent, flou de l'interface, recul du réseau, travelling avant de l'acte 1" },
    apaisement: { bezier: [0.61, 1, 0.88, 1], gsap_proche: "sine.out",   nom: "Apaisement (easeOutSine)",
                  usage: "ondes qui s'éteignent, caméra qui se repose" },
  };

  const courbes = {};
  const css = {};
  for (const [id, c] of Object.entries(TABLE)) {
    courbes[id] = c.bezier ? cubicBezier(...c.bezier) : (p) => p;
    css[id] = c.bezier ? `cubic-bezier(${c.bezier.join(", ")})` : "linear";
  }

  const FPS = 25;

  // Début (image) d'une séquence sur la timeline maîtresse, lu dans timing.js (généré avec timing.json).
  function debutSequence(seq) {
    const T = typeof window !== "undefined" ? window.LILIE_TIMING : null;
    if (!T) throw new Error("LILIE.local : charger timing.js avant courbes.js");
    const q = T.sequences.find((x) => x.id === seq);
    if (!q) throw new Error("LILIE.local : séquence inconnue " + seq);
    return q.fenetre_debut;
  }

  const LILIE = {
    FPS,
    table: TABLE,
    courbes,                      // fonctions exactes, utilisables comme ease GSAP
    css,                          // chaînes cubic-bezier(...) pour les transitions CSS
    duree: (images) => images / FPS,                            // durée en s d'un nombre d'images
    t: (image) => image / FPS,                                  // temps maître (s) d'une image
    local: (image, seq) => (image - debutSequence(seq)) / FPS,  // temps local (s) dans une sous-composition
  };

  if (typeof window !== "undefined") {
    window.LILIE = LILIE;
    if (window.gsap && typeof window.gsap.registerEase === "function") {
      for (const [id, fn] of Object.entries(courbes)) window.gsap.registerEase(id, fn);
    }
  }
  if (typeof module !== "undefined" && module.exports) module.exports = LILIE;
})();
