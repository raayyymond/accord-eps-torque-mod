---
name: accord-v88-lever-b-restored
description: "V88 built/unflashed — V87 + Lever B restored + the probe's rectification hole closed; and 0xC6444 is FALSIFIED (it flew as V71c), not untested."
metadata: 
  node_type: memory
  type: project
  originSessionId: 22c24ebf-36e0-4a19-97d3-9b2d73bedafd
  modified: 2026-08-09T17:05:43.204Z
---

**V88 BUILT, VERIFIED, UNFLASHED** (`analysis-2020accord/build_v88_tva.py`), 2026-08-09.
image sha256 `96b1e018d2058984ada1ba4add7ce42516d5ed9cab65c7be7db294c3d0ca47b8`
rwd sha256 `4955d80a763a364b30d82ba315e7f1a97873068399de1842f64864478130a2de` (986,042 B)
`39990-TVA,A160-V88-V87BASE-LEVERB.GATE6806.ARM5244-PROBE.427.6B98-CAVE.6B98.SIGN.MAG256-…rwd`
Base = **flown V87**. **6 runs / 15 bytes, ZERO unattributed; 5 bytes actually change.**

| addr | from | to | what |
|---|---|---|---|
| `0x3AA96` | `c5` | `fb` | **LEVER B gate** → `ld.bu -0x6806[gp],r15` ("LKAS applying") |
| `0xC6446` | 512 | **5244** | **LEVER B arm** — r24 gain flat 5244 while LKAS applies = **2.000×** |
| `0xC4B38` | `9094` | `6894` | cave probe source → **`gp-0x6b98`** ⇒ **b7 = SIGN of the delivered command @100 Hz** |
| `0xC4B46` | `a6` | `a8` | cave `sar 0x6`→`0x8`, magnitude rung 64 → **256 counts** (the engaged median is 208) |

🛑 **No cave is created, moved, grown or shrunk** — both instrument bytes are in-place edits inside the
62-byte payload flown on V86/V86B/V87.
★ **The new load is NOT hand-encoded**: `24376894` is **byte-identical to the 427 packer's own
`ld.h -0x6b98[gp],r6` at `0x55DF0`** on this base — already proven on-car reading that cell.

## ★ The `TVCA4` hazard, checked and CLEARED (it could have voided the dose)
`v66_v67_explained.r24_gain_q10` hard-codes **mode-10** `gain_B`; this car reads **24/26**
([[reference-accord-car-is-tvca4-mode-24-26]], RULE 7), a mismatch that already produced three
byte-stock builds. Re-derived from the image's own pointer arrays (`0xCBF5C`/`0xCC044`/`0xCC12C`/
`0xCC214` at `mode*4`): **mode 24 ≡ mode 26 byte-identical in all four arrays**, mode 10 differs by
**≤2 counts (0.09 %)**, and the LERP at grind #1's operating point (7.2 km/h, 128 °/s) is **2622 in
all three** ⇒ `5244/2622 = 2.0000×` on the car's real records. ⚠ scalar-vs-curve: **1.77×–2.55×**
across the LKAS-on regime.

## 🛑🛑 RECORD CORRECTION — `0xC6444` is FALSIFIED, not untested
[[accord-rate-lane-builds-were-never-single-variable]] calls raising `0xC6444` (Lever B's r26
decoupler) *"UNTESTED: a candidate"*. **It has flown — as V71c**, which is exactly
`V67 + 0xC6444 512→3072 + 0x454FE` and nothing else. `LEDGER-V38-TO-V84.md:236`:
- grind #1 `e_18-22` **223** vs V67/V68's **109** — **excluded HIGHER (P = 0.0215)**;
- **grind #2 came back**: 7 bursts, 44.31 Hz, p99 = **12.2×** any non-bursting build (vs zero);
- **ratchet 8,521 ct p-p = the corpus RECORD.**

⇒ **the 6× r26 cut is LOAD-BEARING in Lever B, not a defect in it.** `0xC6444` stays at Honda's 512
and is **not** a V89 candidate. Caught by a cross-image cell matrix, not by reading prose.

## 🛑 HONEST LABEL — not "V88 fixes the grinding"
Lever B has flown **seven times** (V67, V68, V71c, V84, V85, V86, V86B); the record calls it
*"CONFIRMED-FIX, AT ITS CEILING … tops out at V67's level, which the operator still calls grinding"*.
V88 (1) **restores the best state the kit has measured**, which V87's rebase gave up, and (2) **makes
Lever B's mechanism observable for the first time** — every prior Lever B flight was scored on the
column torque, an OUTPUT; V87's probe exposes the delivered command
([[accord-v87-flew-the-probe-fired-and-6b98-is-broadband]]). **It is NOT a ratcheting lever.**

## ★ PRE-REGISTRATION
- **Identity, parameter-free:** both channels now read the same cell ⇒ `b6 == (MOTOR_TORQUE ≥ 160)`
  per frame. On route `71` that predicate agrees **0.402**. ⇒ **≈1.00 = V88 flew · ≈0.40 = V87 did.**
- **H1 (the one that matters):** V88's engaged 15–22 Hz band rms of `|gp-0x6b98|` must FALL, CI
  excluding 1.00, from V87's **47.6 [40.7, 59.9]** at 2–4 m/s. 🛑 **A null REFUTES the "broadband HF
  in the command drives the mode" reading** — worth more than another attenuation point.
- **H2:** with `b7` giving sign at 100 Hz, rebuild the **signed** command and re-run the fork with
  **no transparency screen**.
- **H3:** the operator scores the symptoms, in his words.
- 🛑 **Exposure — route `71` failed all three:** ≥5 engaged min (had 2.1) · a real manual arm above
  0.5 m/s (59 % of its manual frames were parked) · **highway** (0.0 s engaged ≥50 km/h, 4th route
  running).

GATE 1: nothing new is written (two load displacements, one immediate, one cal halfword).
GATE 2: r24's derivative feedback ×2.000 while LKAS applies = phase LEAD; flown twice at this dose on
this same 4.000× forward LKAS gain; lane ±8192 clamp needs `|dtorque| ≥ 1601` vs V65's measured
123–839 over 120,049 frames.
