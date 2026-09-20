# -*- coding: utf-8 -*-
"""ARM-KP: rev 6.4 as flown, with SteerKP 1.0 -> 2.0.  One toggle.

THE FINDING (loopshape/, 2026-09-20).  The fork's lateral loop on the torque EPS **never crosses unity**:
|L| < 1 at every frequency 0.08-2.5 Hz in every speed bin, max 0.40-0.65.  V282's crossed at 0.26-0.37 Hz with
~105-110 deg phase margin and cleared |L| = 1 on its PROPORTIONAL term alone (kp/LAF 0.150 x plant 6.84 = 1.03);
rev 6.4 manages 0.0714 x 4.17 = 0.30.  That loop-gain deficit is worth +250 to +430 ms of tracking lag at
0.15-0.30 Hz and is the dominant term in the operator's measured gap.

WHY SteerKP AND NOT SteerLatAccel.  Verified from source: the P contribution is `kp * error_with_lsf` where
`error_with_lsf = error * (1 + low_speed_factor / current_kp)` (latcontrol_torque.py:342), so the effective P gain
is exactly **(kp + lsf)** with `lsf = (interp(v,[0,10,20,30],[12,10.5,8,5]) / max(v,MIN_SPEED))**2` (:339).
lsf DOMINATES at low speed, so raising kp self-tapers out of the regime the operator calls jerky/ratchety:

    v m/s      2      4      6      8     10     15     20     28
    ratio   1.03   1.11   1.23   1.35   1.48   1.72   1.86   1.96

`SteerLatAccel` 14 -> 7 reaches the same kp/LAF but divides BOTH p and i with **no low-speed taper at all** --
exactly x2.00 at every speed, including 4-8 m/s where I is already inflated ~9x by lsf.  Same benefit at speed,
strictly more risk exactly where the operator's rejections live.  Rejected for that reason.

DOSE.  kp/LAF goes 0.0714 -> 0.1429 = 95 % of the 0.150 V282 flew on three routes.  This is an INTERPOLATION
inside the flown envelope (0.050-0.379), not an extrapolation.  Toggle bound is `steerKp * STEER_KP_MAX_MULT`
= 0.6 * 5.0 = **3.00** (latcontrol_torque.py:28, starpilot_variables.py:459/737/811), so 2.0 is in range.

WHAT IT BUYS -- EVIDENCE + ALGEBRA, never a simulation.  Currency: total X->Y error power over 0.15-2.4 Hz over
total demand power, ONE denominator for all bands, >=15 m/s, engaged hands-off runs >=30 s.  Exact identity
X-Y = A + V*D with A (setpoint chain), V (measured wheel->yaw) and D (the loop's own error) all measured, D
scaled by the measured sensitivity ratio:
    as flown 1.350 (3.05x V282's 0.442)  ->  KP 2.0: 1.138 (2.57x)  = 23.4 % of the gap closed
    KP 2.5 -> 32.4 %   KP 3.0 (ceiling) -> 39.9 %   asymptote at infinite gain 109 %
At KP 2.0 all three bands land at or better than V282's own |S|, and the loop finally crosses unity.
Conditional on two stated assumptions: the exogenous drivers of D unchanged, and the car unchanged.  It does NOT
model any nonlinear response to the rougher command (friction, the Honda rate limiter).

🛑 WHAT IT COSTS, AND IT IS NOT FREE.  Two independent estimates of the 1.8-3.5 Hz wheel-shake cost:
  1. exact re-synthesis of the command from logged p/i/f at the new gain, band-filtered: x1.16-1.38 command RMS
     (6c 1.183, 6d 1.155, 6e 1.243, r76 1.376), closed-loop-corrected to ~x1.15-1.24 delivered;
  2. the within-EPS flown ladder (V282 EPS, 6 routes, kp/LAF 0.150->0.379): d log(shake)/d log(kp/LAF) ~ +0.45,
     so x2 => x1.37.
=> **expect +15 % to +40 % more 1.8-3.5 Hz wheel-rate RMS**, on a build already running 3.8-4.6x V282's.
**It gets worse before it gets better, and no dose in this class avoids that.**  Whether that is tolerable is the
OPERATOR'S call, not a measurement -- this file states the number, not a verdict.

SAFETY ENVELOPE, and it is an envelope argument, not a margin.  Shake-band |L| goes 0.08-0.15 -> 0.16-0.33.
Flown anchors: **r71 ran 0.46 and limit-cycled at 2.34 Hz**; r72 ran 0.19 and flew without a shake complaint.
KP 2.0 lands between, nearer r72.  The plant's PHASE at 2-3 Hz is NOT measurable from these logs
(coh(X,u) = 0.14-0.66 there), so this is the whole of the safety argument.  No rail cost: |u| p99 at 4-8 m/s goes
0.488 -> 0.498, 0.00 % saturated.

READOUT, pre-registered before the drive:
  - PRIMARY: total X->Y error power 0.15-2.4 Hz / demand power, >=15 m/s, engaged hands-off runs >=30 s.
    As flown 1.350; this predicts ~1.138.  If it does not fall, the class is wrong and no larger dose is licensed.
  - GATE FIRST: confirm SteerKP = 2.0 in the route's own initData before scoring anything.
  - REVERT SIGNATURE: 1.8-3.5 Hz wheel-rate RMS above ~1.75 deg/s (today 1.03-1.26, V282 0.27), or ANY 2-3 Hz
    limit cycle of the kind r71 showed at shake-band |L| 0.46.  Operator's words to expect on failure: buzzier,
    more shake, nervous at speed.
  - The 1.2-2.4 Hz band of the metric itself rises +7 % at KP 2.0 and +31 % at KP 3.0 (measured waterbed) -- so
    the knee is at x2 and a larger dose should not be taken without reading this one first.

Exactly ONE setting differs from the as-flown config (asserted).  Codec positive control runs first.
"""
import base64, json, os
from pathlib import Path

KIT = Path(__file__).resolve().parents[3]
REF = KIT / "analysis-2020accord" / "reference"
XOR_KEY = "s8#pL3*Xj!aZ@dWq"
FORMAT, VERSION = "starpilot-toggle-backup", 1


def xor(d, k):
    return "".join(chr(ord(c) ^ ord(k[i % len(k)])) for i, c in enumerate(d))


def enc(d):
    return base64.b64encode(xor(json.dumps(d), XOR_KEY).encode()).decode()


def dec(e):
    return json.loads(xor(base64.b64decode(e.encode()).decode(), XOR_KEY))


pairs = 0
for f in sorted(os.listdir(REF)):
    if not f.endswith(".decoded.json"):
        continue
    ep = REF / f.replace(".decoded.json", ".json")
    if not ep.exists():
        continue
    e = json.load(open(ep, encoding="utf-8")); d = json.load(open(REF / f, encoding="utf-8"))
    assert dec(e["data"]) == d, f"decode mismatch {f}"
    assert dec(enc(d)) == d, f"re-encode mismatch {f}"
    pairs += 1
assert pairs > 0, "no reference pair to validate the codec against"
print(f"codec positive control: {pairs} reference pairs round-trip both directions")

flown = json.load(open(REF / "toggle-config_V293_r64_ARM-A_asflown.decoded.json", encoding="utf-8"))
assert flown["AccordDobHz"] == 0.6 and flown["AccordHoldLevel"] is True, "ARM-A is not the rev 6.4 as-flown config"
assert float(flown["SteerKP"]) == 1.0, f"as-flown SteerKP is {flown.get('SteerKP')}, expected 1.0"

KP_CEIL = 0.6 * 5.0      # latcontrol_torque.py:28 KP, starpilot_variables.py:459 STEER_KP_MAX_MULT
arm = dict(flown)
arm["SteerKP"] = 2.0
assert 0.05 <= arm["SteerKP"] <= KP_CEIL, f"outside the toggle's bounds [0.05, {KP_CEIL}]"
diff = {k: (flown.get(k), arm.get(k)) for k in set(flown) | set(arm) if flown.get(k) != arm.get(k)}
assert diff == {"SteerKP": (1.0, 2.0)}, diff

name = "toggle-config_V293_r64_ARM-KP_loopgain"
out = REF / f"{name}.json"
json.dump({"format": FORMAT, "version": VERSION, "settingsCount": len(arm), "data": enc(arm)},
          open(out, "w", encoding="utf-8"), indent=1)
json.dump(arm, open(REF / f"{name}.decoded.json", "w", encoding="utf-8"), indent=1)
assert dec(json.load(open(out, encoding="utf-8"))["data"]) == arm, "written file does not decode to the intended config"
print(f"wrote {out.name}: {len(arm)} settings, one change {diff}, verified by decoding the written file")
print(f"  kp/LAF 0.0714 -> 0.1429 (V282 flew 0.150); toggle ceiling {KP_CEIL}; predicted metric 1.350 -> 1.138")
print("  COST: +15-40 % on 1.8-3.5 Hz wheel shake. Revert signature is in this file's docstring.")
