# -*- coding: utf-8 -*-
"""ARM-KP3: rev 6.4 as flown, SteerKP 1.0 -> 3.0, AccordErrorNotchQ 1.0 -> 0.30, AccordTorqueKi 0.30 -> 0.60.

🛑🛑 THIS REPLACES ARM-KP2, WHICH MUST NOT BE FLOWN.  ARM-KP2 (SteerKP 3.0 + Q 0.60) was built, delivered to
the operator, and is now WITHDRAWN on a safety finding, not a numerical one.

## WHY ARM-KP2 FAILED — its safety argument was aimed at the wrong frequency
ARM-KP2's docstring argued: *"Lower Q is the CONSERVATIVE direction at the 2.34 Hz mode that limit-cycled r71."*
That sentence is TRUE at 2.34 Hz and IRRELEVANT, because on this build the margin does not bind at 2.34 Hz.
It binds at **3.4-4.9 Hz**, where the 2.05 Hz notch has already recovered.  Hand-verified notch magnitudes
(|N| = |1-r^2| / sqrt((1-r^2)^2 + (r/Q)^2), r = f/f0, f0 = 2.05 Hz), and the net loop gain a SteerKP x3 raise
lands at each frequency relative to the flown KP 1.0 / Q 1.0:

      f (Hz)   |N| Q1.0   |N| Q0.60   |N| Q0.30   |N| Q0.20   net at Q0.60   at Q0.30   at Q0.20
       2.34      0.257      0.157       0.079       0.053        1.84x         0.93x      0.62x
       3.40      0.726      0.535       0.302       0.207        2.21x         1.25x      0.85x
       4.22      0.844      0.686       0.427       0.300        **2.44x**     1.52x      1.07x
       4.90      0.892      0.764       0.509       0.367        2.57x         1.71x      1.23x

At 2.34 Hz the notch is deep and Q 0.60 looks protective.  At 4.22 Hz it has recovered to 0.686, so the gain
raise arrives almost undiminished — **2.44x more loop gain exactly where the margin binds**, putting |L| = 1.03
at a -180 deg crossing at 4.22 Hz.

**MEASURED CONSEQUENCE.**  On the vector margin VM = min|1+L| over 2-6 Hz — the only statistic on offer that
correctly ORDERS the flown anchors — ARM-KP2 sits BELOW r71, the only route that has ever limit-cycled, on two
independent plant estimators and in both speed bins:

    V282 0.842/0.882 · r73 0.913/0.828 · r72 (flew clean) -/0.527 · rev 6.4 as flown 0.686/0.505
    **r71 (LIMIT-CYCLED at 2.34 Hz) 0.322/0.079**  ·  **ARM-KP2 AS DELIVERED 0.254/0.049**

ARM-KP2's own reported Ms of 1.09 is computed over 0.10-2.5 Hz; over 0.15-12 Hz it is ~20.  And its readout
gate G6 screened 1.8-3.5 Hz — **blind to its own predicted hazard at 3.4-4.9 Hz.**

⚠ THE SAFETY CURRENCY ALSO CHANGED.  The earlier "shake-band |L|" axis is FALSIFIED: it reads r72 (flew clean)
at 1.8-3.3x r71 (limit-cycled), i.e. it does not order its own anchors.  Logged COMMAND shake does order them
(r72 4.58, rev 6.4 32.40, r71 951.07 in band power; the RMS ratio reproduces the study's r71 anchor to 0.3 %),
and the vector margin does.  Both are used below; |L|shake is retired.

## THIS CONFIG
    SteerKP            1.0  -> 3.00   TOGGLE, at its ceiling (KP 0.6 x STEER_KP_MAX_MULT 5.0)
    AccordErrorNotchQ  1.0  -> 0.30   TOGGLE, bounds [0.0, 4.0], UI step 0.1 so 0.30 is settable
    AccordTorqueKi     0.30 -> 0.60   TOGGLE, bounds [0.05, 1.00]
    everything else UNCHANGED.

    J 1.3512 -> **1.2064**  =  **15.9 % of the gap** (0.442 denominator) / 16.4 % (0.4705)
    command shake **x0.964 — BELOW as flown**   ·   wheel-rate shake x0.97
    crossover 0.208 Hz, PM 129 deg   ·   VM 0.479 (15-22) / 0.377 (22+) — above EVERY flown anchor's
    limit-cycle reading, ~0.75x the flown car's own   ·   full-band Ms 2.6 instead of ARM-KP2's ~20

**It buys a sixth of the gap while making the car QUIETER than it is today.**  That is half of what ARM-KP2
claimed, on a cost axis that works.  Q 0.25 is the more conservative rung (9.7 %, VM 0.553/0.475); Q 0.35 the
more aggressive (20.6 %, VM 0.417/0.285 — but 22+ enters r71's range, so it is NOT recommended).

**AccordTorqueKi 0.30 -> 0.60 is included deliberately.**  `error_with_lsf = error*(1 + lsf/kp)`
(latcontrol_torque.py:342) puts kp in the INTEGRATOR's denominator — it cancels for P (gain = kp + lsf) but not
for I — so SteerKP 1->3 cuts low-speed integral authority to x0.35 at 2 m/s, x0.41 at 4, x0.57 at 8.  Ki x2
restores x0.70 / x0.81 / x1.14.  ⚠ CORRECTION to ARM-KP2's docstring: this is NOT free on the metric, it costs
**-0.9 to -1.6 points of closure** (J 1.0609 -> 1.0693 at the KP3/Q0.6 point).  Worth paying; said plainly.

## THE FORK DIFF THAT WOULD DO BETTER — designed, NOT applied, NOT approved
Two changes, both proposed and neither made (no fork file was edited):
 **A.** `starpilot/common/starpilot_variables.py:459` `STEER_KP_MAX_MULT = 5.0` -> `10.0` (ceiling 3.00 -> 6.00).
     Not so SteerKP alone can go higher — at Q 0.6-1.0 every setting above 2.0 already sits at or below r71's
     margin — but so gain can be raised WITH a wide notch, which is the combination that holds 3.4-4.9 Hz down
     while the low-frequency gain the metric scores goes up.
 **B.** A SPEED-SCHEDULED notch Q (`latcontrol_vehicle_tunes.py` beside `HONDA_ACCORD_KI_SCHEDULE_V_BP`, called
     at `latcontrol_torque.py:347-348`), interpolating [8, 15] m/s from Q 1.0 to the toggle value.  **Zero on the
     metric by construction — every scored window is >= 15.75 m/s — and NOT optional**: it is what makes a wide Q
     survivable below 15 m/s, where the notch centre falls to 0.82-1.28 Hz and Q 0.20 costs |N| 0.426 at -65 deg
     at 0.3 Hz.
At matched vector margin, A+B buys **23.1 %** (SteerKP 5.0 / Q 0.20, VM 0.388, shake x0.973) and **32.9 %**
(SteerKP 6.0 / Q 0.20, VM 0.281, shake x1.004) — i.e. +7 to +17 points over the toggle-only rung, at command
shake AT OR BELOW as flown.
 **REJECTED: a k_d (derivative) term.**  k_d is measurement-rate feedback through a 2 Hz low-pass, so it adds
gain exactly where the margin binds: KP4.0/Q0.30/k_d 0.40 reads VM 0.048, identical to ARM-KP2's.  And the
"51.8 % Tier A cap" (KP3.0/Q0.80/k_d 0.80) has |L| = 3.07 at a -180 deg crossing at 6.05 Hz — **gain margin
0.33, predicted UNSTABLE.  Do not build it.**

## PRE-REGISTERED READOUT — one short symptomatic drive, >=15 m/s, laterally engaged, hands off
 G0 TOGGLE TOOK.  initData must carry SteerKP 3.0, AccordErrorNotchQ 0.3, AccordTorqueKi 0.6.  If the notch key
    reads ABSENT, the device's params .so lacks it: **the drive is VOID, not a null.**
 G1 median(torqueState.p / torqueState.error) = 3.000; median(-(p+i+f)/output) = 14.00.
 G2 NOTCH DEPTH ON THE WIRE.  Re-synthesise error_with_lsf, push through the notch at Q 0.3 and at Q 1.0; RMS
    residual vs logged torqueState.error <= 1e-3 against Q 0.3 and >= 0.05 against Q 1.0.
 G3 THE METRIC.  Predicted J = 1.21.  PASS if J <= 1.27.  FAIL if J >= 1.33 (no movement).
 G4 BAND SIGNATURE.  0.15-0.30 Hz and 0.30-0.60 Hz must both fall, while 0.60-2.40 Hz stays flat within +/-15 %.
    A metric win with the wrong band signature is not this mechanism and must not be credited to it.
 G5 SHAKE.  1.8-3.5 Hz steeringRateDeg RMS vs rev 6.4 on comparable windows.  Predicted **<= x1.00** — this
    config should make the car QUIETER.  Anything above x1.10 falsifies the cost model.
 G6 🛑 **WIDENED TO 1.8-6.0 Hz** — ARM-KP2's 1.8-3.5 Hz window was blind to the hazard frequency.  Add the
    3.5-6.0 Hz steeringRateDeg RMS explicitly.  As-flown reference: T64 carries 0.45/0.57/0.30 % of in-band SR
    power at 4.0/4.3/4.6 Hz.  No sustained (>3 s) narrow line anywhere in 1.8-6.0 Hz.
 G7 Fly it A/B within ONE drive if possible — the unpaired comparison G3 makes is weak at this effect size.

## REVERT = SteerKP 1.0, AccordErrorNotchQ 1.0, AccordTorqueKi 0.30.  Trigger on ANY of:
 R1 Any sustained line in 1.8-6.0 Hz, or 3.5-6.0 Hz RMS above 2x the as-flown reference.
 R2 The operator reports oscillation, buzz, whine or a new hunting feel at speed.
 R3 J >= 1.33 with the params gate passed.  **CLASS-CLOSING at this margin**: if a margin-safe gain raise moves
    nothing, the loop-gain class is done at safe margin and the remaining gap needs the fork diff or firmware.
 R4 A new LOW-SPEED symptom (< 8 m/s).  Q 0.30 costs |N| 0.576 at -55 deg at 0.3 Hz at 2 m/s; that is what
    DIFF B exists to remove.  Step Q to 0.40 rather than abandoning.

## HONEST POSITION
15.9 % is a sixth of the gap.  The structural floor is small (~3 % of the gap is beyond any fork setting), so
nothing structural blocks this class — **3-5 Hz margin does**, and the fork diff A+B is what buys margin-safe
gain.  Whether to spend a drive on 15.9 % at lower shake, or to build A+B first and fly 23-33 %, is the
operator's call.

Exactly THREE settings differ from the as-flown config (asserted).  Codec positive control runs first.
"""
import base64, json, os
from pathlib import Path

KIT = Path(__file__).resolve().parents[3]
REF = KIT / "analysis-2020accord" / "reference"
XOR_KEY = "s8#pL3*Xj!aZ@dWq"
FORMAT, VERSION = "starpilot-toggle-backup", 1
KP_CEIL = 0.6 * 5.0             # latcontrol_torque.py:28 x starpilot_variables.py:459
NOTCH_LO, NOTCH_HI = 0.0, 4.0   # starpilot_variables.py:835
KI_LO, KI_HI = 0.05, 1.0        # starpilot_variables.py:826


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
assert float(flown["AccordTorqueKi"]) == 0.3, f"as-flown AccordTorqueKi is {flown.get('AccordTorqueKi')}"

arm = dict(flown)
arm["SteerKP"] = 3.0
arm["AccordErrorNotchQ"] = 0.3
arm["AccordTorqueKi"] = 0.6
assert 0.05 <= arm["SteerKP"] <= KP_CEIL, f"SteerKP outside [0.05, {KP_CEIL}]"
assert NOTCH_LO < arm["AccordErrorNotchQ"] <= NOTCH_HI, "Q must be > 0 -- Q <= 0 BYPASSES the notch"
assert round(arm["AccordErrorNotchQ"] * 10) == arm["AccordErrorNotchQ"] * 10, "Q must land on the UI step of 0.1"
assert KI_LO <= arm["AccordTorqueKi"] <= KI_HI, f"AccordTorqueKi outside [{KI_LO}, {KI_HI}]"
diff = {k: (flown.get(k), arm.get(k)) for k in set(flown) | set(arm) if flown.get(k) != arm.get(k)}
assert set(diff) == {"SteerKP", "AccordErrorNotchQ", "AccordTorqueKi"}, diff

name = "toggle-config_V293_r64_ARM-KP3_margin-safe"
out = REF / f"{name}.json"
json.dump({"format": FORMAT, "version": VERSION, "settingsCount": len(arm), "data": enc(arm)},
          open(out, "w", encoding="utf-8"), indent=1)
json.dump(arm, open(REF / f"{name}.decoded.json", "w", encoding="utf-8"), indent=1)
assert dec(json.load(open(out, encoding="utf-8"))["data"]) == arm, "written file does not decode to the intended config"
print(f"wrote {out.name}: {len(arm)} settings, changes {diff}, verified by decoding the written file")
print("  J 1.3512 -> 1.2064 = 15.9% of the gap, command shake x0.964 (BELOW as flown), VM 0.479/0.377")
print("  SUPERSEDES ARM-KP2, which sat at VM 0.254/0.049 -- BELOW r71, the only route that limit-cycled.")
