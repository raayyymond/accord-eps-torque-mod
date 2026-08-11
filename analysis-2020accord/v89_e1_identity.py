#!/usr/bin/env python3
r"""V89 flight, routes 75/76 -- IDENTITY, done properly.

🛑 THE RAW AGREEMENT NUMBER IS NOT COMPARABLE ACROSS ROUTES, and `extract_r75_r76.identity_verdict`'s
   threshold rule (>=0.90 => V88) is WRONG for exactly that reason.  Agreement between two rare
   booleans is dominated by the "both false" cell.  On route 73 the two duties were both 0.273, so
   chance was 0.6028; on route 75 they are 0.060 and 0.102, so chance is 0.8503.  A raw 0.954 on
   route 75 is therefore WEAKER evidence of coupling than 0.9654 on route 73, not comparable to it.

FOUR STATISTICS, each parameter-free, run on routes 73 (V88 control), 75 and 76:

  S1  DUTY MATCH.  If the cave byte and the 427 packer read the SAME cell with matched thresholds
      (V88: |cmd| >= 256  <=>  wire >= 160), the two DUTIES must be equal.  Route 73 gave
      0.27330 vs 0.27334.  A duty mismatch is a same-cell falsifier that no correlation can explain.
  S2  COHEN'S KAPPA, agreement corrected for each route's own chance level.
  S3  b5 = (cell != 0).  gp-0x6b98 (V88's source) is the motor command and is essentially NEVER
      exactly zero -> 0.998 on routes 71 and 73.  A source whose b5 duty is ~0.5 is a DIFFERENT CELL.
  S4  THRESHOLD SWEEP.  Best agreement of b6 against (wire >= T) over ALL T.  If the cave reads the
      427's own cell, some T reproduces the rung near-perfectly and the peak is SHARP and at the
      predicted T.  If it reads a merely CORRELATED cell, no T does.

⊕ A residual association on V89 is EXPECTED, not a failure: gp-0x6ae2 = K1/1024 * |model| *
  sign(rate), and |model| is a function of the same applied torque the motor command tracks.  The
  question is never "is there any association" but "is it the identity relation".
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ROUTES = {"73": ("_cache_r73", "r73", "V88 (control -- cave and 427 read the SAME cell)"),
          "75": ("_cache_r75", "r75", "V89?"),
          "76": ("_cache_r76", "r76", "V89?")}
BIT_MAG, BIT_NONZERO, BIT_SIGN = 0x40, 0x20, 0x80
WIRE_T, NEAR_TOL = 160, 0.010


def pair_nearest(t_ref, t_src, tol):
    j = np.searchsorted(t_src, t_ref)
    jl, jr = np.clip(j - 1, 0, len(t_src) - 1), np.clip(j, 0, len(t_src) - 1)
    dl, dr = np.abs(t_ref - t_src[jl]), np.abs(t_ref - t_src[jr])
    return np.where(dl <= dr, jl, jr), np.minimum(dl, dr) <= tol


def run(route):
    cdir, stem, label = ROUTES[route]
    z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
    # 🛑 SAFE PAIRING: (raw14_t, raw14_b4).  Never (t, raw14_b4) -- the kit-wide off-by-one.
    t14 = np.asarray(z["raw14_t"], float)
    b4 = np.asarray(z["raw14_b4"], int) & 0xFF
    o = np.argsort(t14, kind="stable")
    t14, b4 = t14[o], b4[o]
    t427 = np.asarray(z["ab_t1ab"], float)
    wire = np.asarray(z["ab_mt"], int)
    o = np.argsort(t427, kind="stable")
    t427, wire = t427[o], wire[o]

    idx, ok = pair_nearest(t427, t14, NEAR_TOL)
    b6 = ((b4[idx] & BIT_MAG) != 0)[ok]
    b5 = ((b4[idx] & BIT_NONZERO) != 0)[ok]
    w = wire[ok]
    pred = w >= WIRE_T

    d_b6, d_w = float(b6.mean()), float(pred.mean())
    agree = float((b6 == pred).mean())
    chance = d_b6 * d_w + (1 - d_b6) * (1 - d_w)
    kappa = (agree - chance) / (1 - chance) if chance < 1 else np.nan
    # phi (Matthews) -- the same association on a scale a rare marginal cannot inflate
    a = float(np.sum(b6 & pred))
    b = float(np.sum(b6 & ~pred))
    c = float(np.sum(~b6 & pred))
    d = float(np.sum(~b6 & ~pred))
    den = np.sqrt((a + b) * (a + c) * (d + b) * (d + c))
    phi = (a * d - b * c) / den if den > 0 else np.nan

    # S4 -- best agreement over ALL thresholds
    Ts = np.arange(0, 1024, 2)
    ag = np.array([float((b6 == (w >= T)).mean()) for T in Ts])
    jb = int(np.argmax(ag))
    # duty-matched threshold: the T whose duty equals b6's duty (what a same-cell rung must satisfy)
    T_dm = int(np.percentile(w, 100 * (1 - d_b6)))

    # S3's own control: b5 on the WHOLE stream (not just paired frames)
    b5_all = float(((b4 & BIT_NONZERO) != 0).mean())
    b7_all = float(((b4 & BIT_SIGN) != 0).mean())
    wire_nz = float((wire != 0).mean())

    out = dict(route=route, label=label, n_paired=int(ok.sum()),
               S1_duty_b6=d_b6, S1_duty_wire_ge160=d_w, S1_duty_ratio=d_b6 / d_w if d_w else np.nan,
               S1_duty_absdiff=abs(d_b6 - d_w),
               agreement=agree, chance=chance, S2_kappa=float(kappa), S2_phi=float(phi),
               S3_b5_duty=b5_all, S3_b7_duty=b7_all, S3_wire_nonzero=wire_nz,
               S4_best_T=int(Ts[jb]), S4_best_agreement=float(ag[jb]),
               S4_agreement_at_160=float(ag[np.argmin(np.abs(Ts - 160))]),
               S4_T_duty_matched=T_dm,
               S4_agreement_at_duty_matched=float((b6 == (w >= T_dm)).mean()))
    print(f"\n  === route {route}  [{label}] ===   {out['n_paired']:,} paired frames")
    print(f"    S1 DUTY MATCH      b6 {d_b6:.5f}   wire>=160 {d_w:.5f}   "
          f"|diff| {out['S1_duty_absdiff']:.5f}   ratio {out['S1_duty_ratio']:.3f}")
    print(f"    S2 AGREEMENT       {agree:.4f}   chance {chance:.4f}   "
          f"KAPPA {kappa:.4f}   phi {phi:.4f}")
    print(f"    S3 b5 (cell != 0)  {b5_all:.4f}      b7 (cell < 0) {b7_all:.4f}     "
          f"427 wire != 0 {wire_nz:.4f}")
    print(f"    S4 best T {out['S4_best_T']:4d} -> {out['S4_best_agreement']:.4f}   "
          f"(at T=160 {out['S4_agreement_at_160']:.4f})   "
          f"duty-matched T {T_dm} -> {out['S4_agreement_at_duty_matched']:.4f}")
    return out


if __name__ == "__main__":
    res = {r: run(r) for r in ("73", "75", "76")}
    print("\n" + "=" * 100)
    print("  VERDICT LOGIC -- S1 is the falsifier, S3 is the corroborator, S2/S4 size the residual")
    print("=" * 100)
    ctl = res["73"]
    for r in ("75", "76"):
        x = res[r]
        same_cell = (x["S1_duty_absdiff"] < 0.01) and (x["S3_b5_duty"] > 0.95)
        print(f"  route {r}: duty |diff| {x['S1_duty_absdiff']:.5f} vs the V88 control's "
              f"{ctl['S1_duty_absdiff']:.5f}   |   b5 {x['S3_b5_duty']:.4f} vs {ctl['S3_b5_duty']:.4f}"
              f"   |   kappa {x['S2_kappa']:.4f} vs {ctl['S2_kappa']:.4f}")
        print(f"           => {'🛑 reads like V88' if same_cell else 'V89 FLEW -- a DIFFERENT cell'}")
    json.dump(res, open(ROOT / "_cache_r75" / "v89_e1_identity.json", "w"), indent=1, default=float)
