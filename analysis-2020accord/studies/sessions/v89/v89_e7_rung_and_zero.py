#!/usr/bin/env python3
r"""V89 flight -- SETTLE THE RUNG ASSIGNMENT, then measure the EXACTLY-ZERO duty and ask whether
those zeros are FRESH or STALE.

🛑 THE CONFLICT.  `ArcAudit` reports the V89 probe "tests |gp-0x6ae2| >= 64, not literal zero".
   That is **V86's** rung assignment applied to a **V86B-derived** cave.  The kit's own build
   scripts carry the swap explicitly:

       builds/v80_v107/build_v86_tva.py:406   BIT_SIGN, BIT_NONZERO, BIT_MAG, ... = 0x80, 0x40, 0x20, ...
       builds/v80_v107/build_v86b_tva.py:219  BIT_SIGN, BIT_MAG, BIT_NONZERO      = 0x80, 0x40, 0x20
                              # 🛑 b6 = MAG, b5 = NONZERO -- SWAPPED vs V86

   V87, V88 and V89 all import V86B's constants, so **on V89 b6 = MAG (>=64) and b5 = NONZERO**.

   This file does not rest on that.  It settles the question THREE ways:
     M1  the build scripts' own constants and V88's `wire_byte4` mirror swept over values
     M2  the CAVE BYTES read out of the shipped V89 image
     M3  the RAW ALPHABET on routes 75/76 -- parameter-free.  |x| >= 64 IMPLIES x != 0, so the
         magnitude rung must NEST strictly inside the non-zero rung.  Whichever bit is the subset
         is the magnitude rung.  No code, no constants, no assumption.

THEN the number the dose decision needs: what fraction of engaged frames is `gp-0x6ae2` EXACTLY
ZERO, and are those zeros FRESH or a STALE HOLD?
🛑 `gp-0x6ae0`/`gp-0x6ae2` are written on `FUN_0003b8f6`'s SUCCESS PATH ONLY (per `ObserverMatch`);
the gate-fail path leaves them holding their previous value, and V89's cave carries no `gp-0x6c00`
rung, so a `gp-0x6ae2`-only probe cannot see the gate directly.  Four INDIRECT discriminators are
run here, and the file says plainly which of them can and cannot carry the conclusion.
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
FWD = Path(r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
OUTJ = ROOT / "_scratch/cache/r75" / "v89_e7_rung_and_zero.json"

ROUTES = {"73": ("_scratch/cache/r73", "r73", "V88 (cave on gp-0x6b98)"),
          "75": ("_scratch/cache/r75", "r75", "V89 (cave on gp-0x6ae2)"),
          "76": ("_scratch/cache/r76", "r76", "V89 (cave on gp-0x6ae2)")}
BIT = {"b7_sign": 0x80, "b6": 0x40, "b5": 0x20, "b4_gate": 0x10, "b3_fp": 0x08}
CAVE_BASE, CAVE_LEN = 0xC4B34, 62
OUT = {}


def hdr(s):
    print("\n" + "=" * 112 + f"\n{s}\n" + "=" * 112, flush=True)


def sub(s):
    print(f"\n--- {s}", flush=True)


# =================================================================================================
def m1_constants():
    hdr("M1  THE BUILD SCRIPTS' OWN CONSTANTS -- and the exact line where the swap happened")
    for f, pat in (("builds/v80_v107/build_v86_tva.py", "BIT_SIGN, BIT_NONZERO, BIT_MAG"),
                   ("builds/v80_v107/build_v86b_tva.py", "BIT_SIGN, BIT_MAG, BIT_NONZERO")):
        for i, line in enumerate(open(HERE / f, encoding="utf-8"), 1):
            if pat in line and "=" in line and not line.strip().startswith("#"):
                print(f"    {f}:{i}  {line.rstrip()}")
                break
    print("\n    ⇒ V86:  b6 (0x40) = NONZERO,  b5 (0x20) = MAGNITUDE")
    print("    ⇒ V86B: b6 (0x40) = MAGNITUDE, b5 (0x20) = NONZERO   <-- SWAPPED, and V87/V88/V89")
    print("            all import V86B's constants, so this is V89's layout.")
    print("\n    ⊕ The kit already encodes the consequence as a build discriminator:")
    print("      `V86_ONLY = {0x48,0x58,0xC8,0xD8}` -- b6 set with b5 CLEAR.  On V86 that reads")
    print("      'non-zero but under threshold' and is LEGAL.  On V86B/V87/V88/V89 it reads")
    print("      'magnitude >= T but the cell is zero' and is STRUCTURALLY IMPOSSIBLE.")
    OUT["m1"] = {"V86": {"b6": "NONZERO", "b5": "MAG"},
                 "V86B/V87/V88/V89": {"b6": "MAG", "b5": "NONZERO"}}


def m2_bytes():
    hdr("M2  THE CAVE BYTES, READ OUT OF THE SHIPPED V89 IMAGE")
    cand = sorted(FWD.glob("_v89_*_plain_image.bin"))
    if not cand:
        print(f"    🛑 no V89 plain image under {FWD} -- M2 SKIPPED (M1 and M3 stand alone)")
        return
    img = cand[0].read_bytes()
    cave = img[CAVE_BASE:CAVE_BASE + CAVE_LEN]
    print(f"    {cand[0].name}  ({len(img):,} B)")
    print(f"    cave 0x{CAVE_BASE:X}..0x{CAVE_BASE+CAVE_LEN-1:X}:")
    for o in range(0, CAVE_LEN, 16):
        print(f"      +{o:02d}  " + " ".join(f"{b:02x}" for b in cave[o:o + 16]))
    sar = cave[18]
    disp = int.from_bytes(cave[4:6], "little", signed=True)
    print(f"\n    +04..05 = {cave[4]:02x}{cave[5]:02x}  -> ld displacement {disp}  "
          f"= gp{disp:+d} = gp-0x{-disp:X}   {'✅ gp-0x6AE2' if disp == -0x6AE2 else '🛑'}")
    print(f"    +18     = {sar:02x}        -> `sar 0x{sar & 0x1F:x}`  ⇒ magnitude rung trips at "
          f"±{1 << (sar & 0x1F)}   {'✅ 64' if (sar & 0x1F) == 6 else '🛑'}")
    print("    ⊕ `sar 0x6` is the MAGNITUDE rung's shift.  A non-zero test needs no shift at all —")
    print("      it is a `cmp 0` — so the byte that V89 edited is, by construction, the b6 rung.")
    OUT["m2"] = dict(image=cand[0].name, disp=disp, sar_imm=sar & 0x1F,
                     threshold=1 << (sar & 0x1F), cave_hex=cave.hex())


def m3_alphabet():
    hdr("M3  THE RAW ALPHABET -- PARAMETER-FREE.  |x| >= 64 IMPLIES x != 0, so the magnitude rung\n"
        "    must NEST STRICTLY INSIDE the non-zero rung.  Whichever bit is the subset IS the\n"
        "    magnitude rung.  No constants, no code, no assumption.")
    OUT["m3"] = {}
    for r, (cdir, stem, label) in ROUTES.items():
        z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
        b4 = np.asarray(z["raw14_b4"], int) & 0xFF
        vals, cnt = np.unique(b4, return_counts=True)
        print(f"\n    route {r}  [{label}]   {len(b4):,} 0x14A frames")
        print("      " + "  ".join(f"0x{int(v):02X}:{c:,}" for v, c in zip(vals, cnt)))
        b5 = (b4 & BIT["b5"]) != 0
        b6 = (b4 & BIT["b6"]) != 0
        n65 = int(np.sum(b6 & ~b5))     # b6 set, b5 clear
        n56 = int(np.sum(b5 & ~b6))     # b5 set, b6 clear
        print(f"      frames with b6 SET and b5 CLEAR : {n65:,}")
        print(f"      frames with b5 SET and b6 CLEAR : {n56:,}")
        if n65 == 0 and n56 > 0:
            v = "b6 ⊂ b5  ⇒  b5 = (x != 0),  b6 = (|x| >= 64)   [V86B layout]"
        elif n56 == 0 and n65 > 0:
            v = "b5 ⊂ b6  ⇒  b6 = (x != 0),  b5 = (|x| >= 64)   [V86 layout]"
        else:
            v = "🛑 NEITHER nests -- the two bits are not a (nonzero, magnitude) pair"
        print(f"      ⇒ {v}")
        OUT["m3"][r] = dict(alphabet={f"0x{int(v_):02X}": int(c) for v_, c in zip(vals, cnt)},
                            n_b6_without_b5=n65, n_b5_without_b6=n56, verdict=v)


# =================================================================================================
def zero_duty():
    hdr("★ THE NUMBER THE DOSE DECISION NEEDS -- fraction of ENGAGED frames with gp-0x6ae2 EXACTLY 0")
    OUT["zero"] = {}
    for r, (cdir, stem, label) in ROUTES.items():
        z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
        t14 = np.asarray(z["raw14_t"], float)
        b4 = np.asarray(z["raw14_b4"], int) & 0xFF
        rt = np.asarray(z["t"], float)
        lat = np.interp(t14, rt, np.asarray(z["cc_lat"], float)) > 0.5
        nz = (b4 & BIT["b5"]) != 0
        mg = (b4 & BIT["b6"]) != 0
        d = dict(engaged_frames=int(lat.sum()),
                 exactly_zero=float(1 - nz[lat].mean()),
                 nonzero_under_64=float(np.mean(nz[lat] & ~mg[lat])),
                 ge_64=float(mg[lat].mean()))
        OUT["zero"][r] = d
        print(f"    route {r} [{label}]  {d['engaged_frames']:,} engaged frames")
        print(f"      EXACTLY ZERO          {d['exactly_zero']:.4f}")
        print(f"      non-zero but < 64     {d['nonzero_under_64']:.4f}")
        print(f"      |value| >= 64         {d['ge_64']:.4f}")


def freshness():
    hdr("IS THE ZERO FRESH OR A STALE HOLD?  Four indirect discriminators, and what each can carry.")
    OUT["fresh"] = {}
    for r, (cdir, stem, label) in ROUTES.items():
        if r == "73":
            continue
        z = np.load(ROOT / cdir / f"{stem}.npz", allow_pickle=True)
        t14 = np.asarray(z["raw14_t"], float)
        b4 = np.asarray(z["raw14_b4"], int) & 0xFF
        rt = np.asarray(z["t"], float)
        lat = np.interp(t14, rt, np.asarray(z["cc_lat"], float)) > 0.5
        rate = np.abs(np.interp(t14, rt, np.asarray(z["rate_f"], float)))   # 0x18F, 0.1 deg/s LSB
        nz = (b4 & BIT["b5"]) != 0
        row = {}

        sub(f"route {r} -- D1  RUN-LENGTH of the ZERO state (a stale hold FREEZES; a sign relay "
            f"dithers)")
        e = np.where(lat)[0]
        seq = nz[lat]
        chg = np.flatnonzero(np.diff(seq.astype(int)) != 0) + 1
        runs = np.split(seq, chg)
        z_runs = np.array([len(x) for x in runs if len(x) and not x[0]], float)
        n_runs = np.array([len(x) for x in runs if len(x) and x[0]], float)
        for nm, a in (("ZERO runs", z_runs), ("NON-ZERO runs", n_runs)):
            if not len(a):
                continue
            print(f"      {nm:14s} n={len(a):5d}  median {np.median(a)*10:6.0f} ms  "
                  f"p90 {np.percentile(a,90)*10:6.0f} ms  p99 {np.percentile(a,99)*10:7.0f} ms  "
                  f"max {a.max()*10:8.0f} ms   frac of runs >1 s {np.mean(a > 100):.4f}")
            row[nm] = dict(n=len(a), med_ms=float(np.median(a) * 10),
                           p90_ms=float(np.percentile(a, 90) * 10),
                           p99_ms=float(np.percentile(a, 99) * 10), max_ms=float(a.max() * 10),
                           frac_gt_1s=float(np.mean(a > 100)))

        sub(f"route {r} -- D2  is the ZERO state predicted by the WHEEL RATE quantising to zero?\n"
            f"        (a sign(v) relay must; a gate failure has no reason to)")
        edges = [0, 0.05, 0.15, 0.35, 0.75, 1.5, 3.0, 6.0, 12.0, 25.0, 1e9]
        tab = []
        for i in range(len(edges) - 1):
            m = lat & (rate >= edges[i]) & (rate < edges[i + 1])
            if m.sum() < 300:
                continue
            tab.append((edges[i], edges[i + 1], float(1 - nz[m].mean()), int(m.sum())))
            print(f"        |rate| [{edges[i]:5.2f},{edges[i+1]:6.2f}) deg/s   "
                  f"P(exactly zero) {1-nz[m].mean():.4f}   {m.sum()/100:7.1f} s")
        row["D2"] = tab

        sub(f"route {r} -- D3  the STALE-HOLD hypothesis's own prediction, and it is the wrong sign")
        print("        A gate failure holds the LAST SUCCESSFUL value.  Per ObserverMatch the term's")
        print("        typical magnitude is ~41 counts, i.e. NON-ZERO.  So a gate failure predicts a")
        print("        stale NON-ZERO reading, not a zero.  For a stale hold to read zero, the last")
        print("        success must itself have written zero -- which is the FRESH-zero hypothesis")
        print("        one sample earlier.  ⇒ the stale account cannot generate the zero state; it")
        print("        can only PROLONG one.  [logic, not a measurement]")

        sub(f"route {r} -- D4  the zero state's dwell vs the rate zero-crossing period")
        m = lat & (rate < 0.05)
        print(f"        engaged frames with |rate| < 0.05 deg/s : {m.sum()/100:.1f} s, "
              f"P(zero) {1-nz[m].mean():.4f}" if m.sum() else "        none")
        mm = lat & (rate > 6.0)
        print(f"        engaged frames with |rate| > 6 deg/s    : {mm.sum()/100:.1f} s, "
              f"P(zero) {1-nz[mm].mean():.4f}")
        print("        ⇒ if the gate were failing, P(zero) would not be a monotone function of a")
        print("          mechanical variable the gate does not read.")
        OUT["fresh"][r] = row

    hdr("🛑 WHAT THIS CANNOT DO")
    print("    V89's cave has NO `gp-0x6c00` rung, and `gp-0x6ae0`/`gp-0x6ae2` are written on the")
    print("    SUCCESS PATH ONLY.  So NOTHING here observes the gate directly.  D1/D2/D4 are")
    print("    consistency arguments against a stale hold and D3 is a logical one; none of them is")
    print("    a measurement of `gp-0x6c00`.  A DIRECT answer needs one cave bit on")
    print("    `gp-0x6c00 == 0xFFFF` on the next build.")


if __name__ == "__main__":
    m1_constants()
    m2_bytes()
    m3_alphabet()
    zero_duty()
    freshness()
    json.dump(OUT, open(OUTJ, "w"), indent=1, default=float)
    print(f"\n  wrote {OUTJ}")
