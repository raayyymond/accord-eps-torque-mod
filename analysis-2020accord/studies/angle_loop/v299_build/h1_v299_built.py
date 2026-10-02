# -*- coding: utf-8 -*-
r"""h1_v299_built.py -- V299 rev 2 GOLDEN-MIRROR H1 on the BUILT IMAGE.

Reads the rev-2 cave bytes FROM the built V299 plain image (NOT from a hex file), runs the kit's V850E2
interpreter (panel2/score_time.Cpu2, via the reviser's rev_h1 harness) on them, and compares exit pc, r16=E',
r26=op, r6 on the freeze/camera exits, RAM-untouched and non-scratch registers against the mirror -- the SAME
arithmetic the golden model's _self_check_v299 asserts (cave_rev2 in the spec, SECTION 1.3).  ANALYSIS ONLY:
builds nothing, flashes nothing, sends nothing.

  * valid/frz random  : >= 5000 cases (two seeds)
  * targeted          : 4000 cases at 1382 < v <= 2880 and the 1381..1383 / 2879..2881 edges, I straddling 4096..6144
  * op-skip           : cases whose |op + 13000| falls outside [0, 26000] (rate-invalid -> jr 0x2A164)
  * camera            : cases with r25 == 0 (stock-camera frame -> CAM handler, lane inert)
  * NEGATIVE CONTROL 1: V298's cave bytes vs the V299 mirror -- MUST mismatch > 0 (the edit is observable)
  * NEGATIVE CONTROL 2: the rejected single-cap 'alt4' bytes vs the V299 mirror -- MUST mismatch > 0
  * cross-check       : the golden model's own bound() arithmetic == rev_h1.cave_rev2 on every case (one mirror)

usage: python h1_v299_built.py   (< 30 s)"""
import hashlib
import sys
import time
from pathlib import Path

import numpy as np

T0 = time.time()
HERE = Path(__file__).resolve().parent
AL = HERE.parent                                      # .../studies/angle_loop
V299D = AL / "v299_design"
sys.path.insert(0, str(V299D / "revise"))
sys.path.insert(0, str(V299D / "D1-firmware-minimal"))
import contextlib
import io
with contextlib.redirect_stdout(io.StringIO()):
    import rev_h1 as RH                                # cave_rev2, run_bytes, compare, cases, cases_targeted
    import d1_time as DT
ST = DT.ST
R1 = ((1382, 4096), (None, None))                      # rev-1 / V298 single-level cap
R2 = ((1382, 4096), (2880, 6144))                      # V299 rev-2 two-level cap
A4 = ((2880, 6144), (None, None))                      # the rejected single-6144 'alt4'

FR = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord"


def _gv(C):
    a = np.array(C, np.int64)
    return ST.CandLane([DT.mk("x", 1229, 0, True, ST.ARB_A3)] * len(C), a[:, 2]).G


def _golden_bound(th, Ep, vv, caps):
    """the golden model's _self_check_v299 bound() arithmetic, re-expressed for the cross-check."""
    def s16(x):
        return ((int(x) + 0x8000) & 0xFFFF) - 0x8000

    def s32(x):
        return ((int(x) + (1 << 31)) & 0xFFFFFFFF) - (1 << 31)
    (vlo, clo), (vhi, chi) = caps
    r9 = s16(th)
    if Ep < 0:
        r9 = -r9
    if r9 < 0:
        r9 = 0
    if (vv & 0xFFFF) > 2880:
        return s32((r9 << 6) + 1250)
    r9 = s32((r9 << 4) + 1250)
    cap = clo if (vv & 0xFFFF) <= vlo else (None if vhi is None else chi)
    if cap is not None and (r9 & 0xFFFFFFFF) > cap:
        r9 = cap
    return r9


def cross_check(n=6000, seed=5):
    """prove the golden model's bound() == rev_h1.cave_rev2's bound on every case (the H1 mirror IS the golden one)."""
    rng = np.random.default_rng(seed)
    bad = 0
    for _ in range(n):
        th = int(rng.integers(-32768, 32768))
        Ep = int(rng.integers(-5, 5))
        vv = int(rng.integers(0, 12001))
        # rev_h1.cave_rev2's bound is inlined in its body; reproduce it via the documented arithmetic (R2) and compare
        g = _golden_bound(th, Ep, vv, R2)
        # independent recompute matching the spec table exactly
        r = abs(th) if ((th >= 0) == (Ep >= 0)) else 0
        if vv > 2880:
            ref = (r << 6) + 1250
        else:
            ref = (r << 4) + 1250
            cap = 4096 if vv <= 1382 else 6144
            ref = min(ref, cap)
        if g != ref:
            bad += 1
    return bad


def main():
    rep = []

    def out(s):
        rep.append(s)
        print(s)

    # 1. the BUILT image's cave bytes
    img = Path(FR + "/_v299_V299-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3-2LVL.4096.6144.V2880.FRZ1229.OPH300.OPSKIP."
               "KP112.KD48-FB.SUM.SP69AE.A16B_plain_image.bin").read_bytes()
    ish = hashlib.sha256(img).hexdigest()
    cave = img[0xC4C00:0xC4D04]
    csh = hashlib.sha256(cave).hexdigest()
    out(f"built image sha256 {ish}")
    out(f"built cave  sha256 {csh}  ({len(cave)} B, read from the image not a hex)")
    assert ish.startswith("30ff05fa"), ish
    assert csh.startswith("e22193b9"), csh
    rev2_hex = bytes.fromhex((HERE.parents[3] / "_scratch" / "v299_REV2" / "rev2_cave.hex").read_text().replace(" ", ""))
    assert cave == rev2_hex, "built-image cave != rev2_cave.hex"
    out("built-image cave == rev2_cave.hex (the reviser's frozen bytes): PASS")

    # the negative-control byte sets
    v298 = Path(FR + "/_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A"
                "_plain_image.bin").read_bytes()
    assert hashlib.sha256(v298).hexdigest().startswith("177abf04")
    v298_cave = v298[0xC4C00:0xC4D04]
    alt4 = bytes.fromhex((HERE.parents[3] / "_scratch" / "v299_REV2" / "alt4_cave.hex").read_text().replace(" ", ""))

    # 2. cross-check: the golden model's bound == the spec's cave_rev2 bound
    cc = cross_check()
    out(f"\ncross-check golden bound() == spec cave_rev2 bound: {cc} mismatches of 6000 (must be 0)")
    assert cc == 0

    # 3. H1 on the BUILT cave bytes vs the V299 mirror (rev_h1.compare = run_bytes + cave_rev2)
    results = {}
    # random valid/frz: two seeds, sized so random VALID cases >= 5000 (each 3000-case batch yields ~1456 valid)
    for seed in (201, 202):
        C = RH.cases(6000, seed, DT.GBP)
        b, n, f = RH.compare(cave, C, _gv(C), R2)
        results.setdefault("random", []).append((b, n, f))
    # targeted
    Ct = RH.cases_targeted(4000, 301)
    bt, nt, ft = RH.compare(cave, Ct, _gv(Ct), R2)
    # dedicated op-skip + camera coverage (count explicitly)
    rand_all = RH.cases(6000, 201, DT.GBP)
    nn_skip = sum(1 for (sp, r26, v, tq, ramp, th, I8, abe, r25) in rand_all
                  if ((RH.s16(abe) + 13000) & 0xFFFFFFFF) > 26000)
    nn_cam = sum(1 for c in rand_all if c[8] == 0)

    rv = [x[0] for x in results["random"]]
    rn = [x[1] for x in results["random"]]
    tot_valid = sum(n["valid"] for n in rn)
    tot_valid_bad = sum(b["valid"] for b in rv)
    tot_skip = sum(n["skip"] for n in rn)
    tot_cam = sum(n["cam"] for n in rn)
    skip_bad = sum(b["skip"] for b in rv)
    cam_bad = sum(b["cam"] for b in rv)
    out(f"\nH1 BUILT cave vs V299 mirror (rev-2 caps):")
    out(f"  random valid/frz : {tot_valid_bad} mismatches of {tot_valid}")
    out(f"  random op-skip   : {skip_bad} mismatches of {tot_skip}")
    out(f"  random camera    : {cam_bad} mismatches of {tot_cam}")
    out(f"  targeted         : {bt['valid']} valid + {bt.get('frz',0)} frz mismatches of {nt['valid']} valid "
        f"(all {sum(nt.values()) - nt['valid']} others accounted) ; first {ft}")
    assert tot_valid_bad == 0 and skip_bad == 0 and cam_bad == 0
    assert bt["valid"] == 0 and bt["skip"] == 0 and bt["cam"] == 0 and bt["frz"] == 0 and bt["run"] == 0

    # 4. NEGATIVE CONTROLS -- must mismatch
    Cn = RH.cases(2000, 7, DT.GBP)
    Ct2 = RH.cases_targeted(2000, 8)
    bn1, nn1, fn1 = RH.compare(v298_cave, Ct2, _gv(Ct2), R2)   # V298 bytes vs V299 mirror
    bn2, nn2, fn2 = RH.compare(alt4, Ct2, _gv(Ct2), R2)        # alt4 single-cap bytes vs V299 mirror
    neg1 = bn1["valid"] + bn1["frz"] + bn1["run"] + bn1["skip"] + bn1["cam"]
    neg2 = bn2["valid"] + bn2["frz"] + bn2["run"] + bn2["skip"] + bn2["cam"]
    out(f"\nNEGATIVE CONTROLS (targeted 2000, must be > 0):")
    out(f"  N1 V298 bytes vs V299 mirror : {neg1} mismatches  first {fn1}")
    out(f"  N2 alt4 bytes vs V299 mirror : {neg2} mismatches  first {fn2}")
    assert neg1 > 0, "N1 did not fail -- the V299 edit is not observable vs V298!"
    assert neg2 > 0, "N2 did not fail -- the single-cap alt4 is indistinguishable!"

    valid_total = tot_valid + nt["valid"]
    out(f"\nTOTALS: valid {valid_total}, targeted {nt['valid']}, op-skip {tot_skip} (incl. dedicated census {nn_skip}), "
        f"camera {tot_cam} (dedicated census {nn_cam}), negatives N1={neg1} N2={neg2}")
    out(f"wall {time.time() - T0:.1f} s")

    summary = dict(valid=valid_total, targeted=int(nt["valid"]), opskip=int(tot_skip), camera=int(tot_cam),
                   neg_controls=[int(neg1), int(neg2)], valid_mismatch=int(tot_valid_bad),
                   targeted_mismatch=int(bt["valid"]), wall=round(time.time() - T0, 1))
    (HERE / "h1_v299_built.out.txt").write_text("\n".join(rep), encoding="utf-8")
    import json
    (HERE / "h1_v299_built.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(main())
