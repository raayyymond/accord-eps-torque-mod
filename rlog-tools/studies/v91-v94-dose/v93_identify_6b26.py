#!/usr/bin/env python3
r"""IS `gp-0x6b26` A DAMPER OR AN INERTIA CANCELLER?  The one question that decides V93's direction.

===================================================================================================
WHY THIS IS THE CRUX
===================================================================================================
`FUN_00036c12` computes, with GAIN negative on every path (Y row −9830…−1966, fallbacks −8192/−3277):

    gp-0x6b26 = clamp( ((gp-0x6c2c · GAIN) >> 6) · 0x111 >> 18 , ±511 )      ⇒  gp-0x6b26 = −K·gp-0x6c2c

So the SIGN of the physical effect turns entirely on what `gp-0x6c2c` is:

    gp-0x6c2c = motor RATE          ⇒ gp-0x6b26 ∝ −rate   ⇒ VISCOUS DAMPING.
                                       Raising K ADDS damping — the right direction for a stutter.
    gp-0x6c2c = motor ACCELERATION  ⇒ gp-0x6b26 ∝ −accel  ⇒ INERTIA CANCELLATION.
                                       Raising K makes the wheel LIGHTER and LESS damped — and would
                                       make micro-stuttering WORSE, not better.

🛑 THE KIT'S OWN RECORD IS SPLIT ON THIS, WHICH IS EXACTLY WHY IT MUST BE MEASURED, NOT CITED:
   * `builds/v80_v107/build_v91_tva.py` calls the term *"genuinely DISSIPATIVE (it opposes motor rate)"* and names the
     whole lever "friction/damping-comp".
   * `memory/accord/signals/accord-gp6c2c-is-motor-rate-derivative.md` calls `gp-0x6c2c` a **motor-rate DERIVATIVE**.
   * `memory/accord-friction-polarity-more-assist.md` establishes that more modelled friction makes the
     wheel **LIGHTER**, and the `0xC646E` INERTIA note says raising that gain makes it lighter too.
   Those cannot all be true of a damping term. **A V93 that raises K on the strength of the wrong one
   would push the operator's symptom the WRONG WAY.**

===================================================================================================
THE DISCRIMINATOR — the same one used to identify gp-0x6bbe, and it is signature-based
===================================================================================================
Against wheel rate, over frequency:
    viscous (∝ rate)      ⇒ gain FLAT in f,      phase ≈    0°
    inertial (∝ accel)    ⇒ gain RISING  ∝ f,    phase ≈  +90°
    stiffness (∝ angle)   ⇒ gain FALLING ∝ 1/f,  phase ≈  −90°
A rising gain and a +90° phase are the SAME claim seen two ways; requiring both is what makes this
robust to the reconstruction skew.

DATA: route 78 (V91). 427 carries |gp-0x6b26| at 50 Hz (`wire·8/5`) and `0x14A` byte4 b7 carries its
SIGN at 100 Hz — the same two-message split as the boost lane, so the same ±2-sample skew sweep is
run as a control and reported.

Usage:  python studies/v91-v94-dose/v93_identify_6b26.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import decode_v90_probe as P          # noqa: E402
from v92_boost_lane_and_rez import trust  # noqa: E402

RNG = np.random.default_rng(93_6266)
CACHE = ROOT / "analysis-2020accord"
DEG2RAD = np.pi / 180.0
BANDS = [("2-4", 2.0, 4.0), ("4-6", 4.0, 6.0), ("6-9", 6.0, 9.0), ("9-12", 9.0, 12.0),
         ("12-16", 12.0, 16.0), ("16-18", 16.0, 18.0), ("18-22", 18.0, 22.0)]
CNT_PER_KMH = 64.0                # cal 0xC62EA = 320 counts ≈ 5 km/h  (kit memory)
LERP_X = [0, 1280, 5760]
LERP_Y = [-9830, -5734, -1966]
FALLBACK_2 = -8192                # cal 0xC640A, taken when gp-0x671a >= cal(0xC64FD)=5
FALLBACK_1 = -3277                # cal 0xC640C, taken when gp-0x671a>=0xFF or gp-0x67f4!=1
CLAMP = 511


def build(shift=0):
    z = np.load(CACHE / "_scratch/cache/r78" / "r78.npz", allow_pickle=True)
    t = np.asarray(z["t"], float)
    tab = np.asarray(z["ab_t1ab"], float)
    mag = np.asarray(z["ab_mt"], int) * (8.0 / 5.0)
    t14 = np.asarray(z["raw14_t"], float)
    neg = (np.asarray(z["raw14_b4"], int) & 0x80) != 0        # V90/V91 b7 = gp-0x6b26 < 0
    if shift:
        neg = np.roll(neg, shift)
    sgn = np.where(np.interp(tab, t14, neg.astype(float)) > 0.5, -1.0, 1.0)
    lat = np.interp(tab, t, (np.asarray(z["cc_lat"], float) > 0.5).astype(float)) > 0.5
    press = np.interp(tab, t, (np.asarray(z["cs_press"], float) > 0.5).astype(float)) > 0.5
    v = np.interp(tab, t, np.abs(np.asarray(z["cs_v"], float)))
    rate = np.interp(tab, t, np.asarray(z["rate_f"], float) * DEG2RAD)
    return dict(t=tab, mag=mag, signed=mag * sgn, lat=lat, v=v, rate=rate,
                mask=lat & (~press) & (v > 0.5), fs=1.0 / float(np.median(np.diff(tab))))


def main():
    OUT = {}
    B = build(0)
    fs = B["fs"]
    print("=" * 100)
    print(" IS gp-0x6b26 A DAMPER (∝ rate) OR AN INERTIA CANCELLER (∝ acceleration)?")
    print(" route 78 (V91), 427 = |gp-0x6b26|, sign from 0x14A byte4 b7")
    print("=" * 100)
    print(f"  fs {fs:.2f} Hz   masked samples {int(B['mask'].sum()):,}")

    per = {}
    for s in (-2, -1, 0, 1, 2):
        Bs = build(s)
        per[s] = (P._wins(Bs["mask"], Bs["t"], P.NW50, P.HOP50, (Bs["rate"], Bs["signed"])),
                  Bs["fs"])
    print(f"\n  {'band':8s} {'gain ct/(rad/s)':>16s} {'phase':>9s} {'coh²':>7s} {'shuf':>7s} "
          f"{'TRUST':>6s}   gain across skew −2…+2")
    rows = {}
    for nm, lo, hi in BANDS:
        W, f0 = per[0]
        if len(W) < 6:
            continue
        pairs = [(w[0], w[1]) for w in W]
        r = P._band_transfer(pairs, f0, P.NW50, [(nm, lo, hi)])[nm]
        idx = RNG.permutation(len(pairs))
        rs = P._band_transfer([(pairs[i][0], pairs[(idx[i] + 1) % len(pairs)][1])
                               for i in range(len(pairs))], f0, P.NW50, [(nm, lo, hi)])[nm]
        sweep = []
        for s in (-2, -1, 0, 1, 2):
            Ws, fss = per[s]
            rr = P._band_transfer([(w[0], w[1]) for w in Ws], fss, P.NW50, [(nm, lo, hi)])[nm]
            sweep.append(rr["gain"])
        ok = trust(r["coh2"], rs["coh2"])
        rows[nm] = dict(gain=r["gain"], phase_deg=r["phase_deg"], coh2=r["coh2"],
                        coh2_shuf=rs["coh2"], trustworthy=ok, gain_sweep=sweep, n=len(pairs))
        print(f"  {nm:8s} {r['gain']:16.1f} {r['phase_deg']:8.1f}° {r['coh2']:7.3f} "
              f"{rs['coh2']:7.3f} {'YES' if ok else '🛑 NO':>6s}   "
              + " ".join(f"{g:6.1f}" for g in sweep))
    OUT["vs_rate"] = rows

    g = [rows[b]["gain"] for b in ("2-4", "4-6", "6-9", "9-12", "12-16") if b in rows]
    ph = [rows[b]["phase_deg"] for b in ("4-6", "6-9", "9-12") if b in rows]
    if g:
        rise = g[-1] / g[0]
        print(f"\n  GAIN 2-4 Hz → 12-16 Hz: {g[0]:.1f} → {g[-1]:.1f} = {rise:.2f}×   "
              f"(viscous predicts ≈1.0×, inertial predicts ≈{14/3:.1f}× over this span)")
        print(f"  MEAN PHASE 4-12 Hz: {np.mean(ph):+.1f}°   "
              f"(viscous predicts ≈0°, inertial predicts ≈+90°)")
        verdict = ("VISCOUS — gp-0x6b26 is a DAMPER; raising K adds damping"
                   if rise < 2.0 and abs(np.mean(ph)) < 40 else
                   "INERTIAL — gp-0x6b26 tracks ACCELERATION; raising K makes the wheel LIGHTER"
                   if rise > 2.5 and np.mean(ph) > 50 else
                   "🛑 MIXED / UNRESOLVED — do not build a K change on this")
        print(f"\n  ⇒ VERDICT: {verdict}")
        OUT["verdict"] = verdict
        OUT["gain_rise_2_4_to_12_16"] = float(rise)
        OUT["mean_phase_4_12"] = float(np.mean(ph))

    # ---------------- the CLIP sizing for every candidate V93 gain change ----------------
    print("\n" + "=" * 100)
    print(" CLIP SIZING — what each candidate V93 edit does to |gp-0x6b26| against the ±511 rail")
    print("=" * 100)
    print("  Speed axis: cal 0xC62EA = 320 counts ≈ 5 km/h ⇒ 64 counts/km/h")
    print(f"  LERP X = {LERP_X} counts = {[x/CNT_PER_KMH for x in LERP_X]} km/h,  Y = {LERP_Y}")

    z77 = np.load(CACHE / "_scratch/cache/r77" / "r77.npz", allow_pickle=True)
    t77 = np.asarray(z77["t"], float)
    tab77 = np.asarray(z77["ab_t1ab"], float)
    m77 = np.asarray(z77["ab_mt"], int) * (8.0 / 5.0)
    v77 = np.interp(tab77, t77, np.abs(np.asarray(z77["cs_v"], float))) * 3.6
    lat77 = np.interp(tab77, t77,
                      (np.asarray(z77["cc_lat"], float) > 0.5).astype(float)) > 0.5
    mag = np.concatenate([m77, B["mag"]])
    vk = np.concatenate([v77, B["v"] * 3.6])
    eng = np.concatenate([lat77, B["lat"]])

    def lerp_gain(v_kmh):
        x = np.clip(v_kmh * CNT_PER_KMH, LERP_X[0], LERP_X[-1])
        return np.interp(x, LERP_X, LERP_Y)

    cands = [("V91/V92 as flown — mode-record Y ×1.5", lambda v: 1.5 * np.ones_like(v)),
             ("A · mode-record Y ×1.6 (arithmetic max)", lambda v: 1.6 * np.ones_like(v)),
             ("B · 0xC64FD 5→0  ⇒ flat −8192 at all speeds",
              lambda v: FALLBACK_2 / lerp_gain(v)),
             ("C · 0xC640A −8192→−4096 with 0xC64FD 5→0",
              lambda v: -4096.0 / lerp_gain(v))]
    print(f"\n  {'candidate':<46} {'max mult':>9} {'pred max':>9} {'% of rail':>10} "
          f"{'clip duty':>10}")
    sizing = {}
    e = eng & (mag > 0)
    for nm, fn in cands:
        mult = fn(vk[e])
        pred = mag[e] * mult
        clip = float(np.mean(pred >= CLAMP))
        sizing[nm] = dict(max_multiplier=float(mult.max()), pred_max=float(pred.max()),
                          pct_of_rail=float(100 * pred.max() / CLAMP), clip_duty=clip)
        flag = "  ✅" if clip == 0 and pred.max() < CLAMP else "  🛑 CLIPS ⇒ COULOMB RELAY (V80)"
        print(f"  {nm:<46} {mult.max():9.2f} {pred.max():9.1f} {100*pred.max()/CLAMP:9.1f} % "
              f"{clip:10.6f}{flag}")
    OUT["clip_sizing"] = sizing
    print("\n  🛑 Pooled r77 + r78 engaged 427 samples, open-loop extrapolation (conservative but")
    print("     still an extrapolation — a rougher drive can exceed it).")
    print("  🛑 A railed lane is sign(gp-0x6c2c)×511 — a Coulomb RELAY, the V80 mechanism exactly.")

    (CACHE / "_scratch/cache/r78" / "identify_6b26.json").write_text(json.dumps(OUT, indent=1,
                                                                       default=float))
    print("\n  wrote analysis-2020accord/_scratch/cache/r78/identify_6b26.json")


if __name__ == "__main__":
    main()
