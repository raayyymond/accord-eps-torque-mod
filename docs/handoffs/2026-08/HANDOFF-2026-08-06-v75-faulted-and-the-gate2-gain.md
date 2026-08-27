# HANDOFF 2026-08-06 — V75 fixed the grind and hard-faulted the ECU; the cause is a GATE-2 loop-gain overshoot we introduced

**Session shape:** orchestrator + 10 subagents. Two operator goals: (1) root-cause V75's hard fault,
(2) find why LKAS fights excess "friction". Both are answered; the fault's *proximate monitor* is not.

---

## 1. What the operator reported

> "V75 got rid of the audible grind #1 and strongly attenuated the micro-ratcheting… However there was a
> bad issue. After stopping at a stoplight and then continuing like normal, with openpilot engaged, I
> experience a hard fault. The power steering dashboard flashed on, comma reported an LKAS fault, and I
> could feel that I had lost power steering. I had to manually turn the car's wheels after this point."

**Both halves are real and they are the whole trade.** V75 is the best symptom result this kit has ever
produced *and* the first fault in its history to fire **mid-drive**. V24/V27/V48B bricked at flash or on
the first turn; V40 bricked at ignition. ⚠ **n = 1, no rlogs.**

Second report, explicitly not V75-specific: *"excess friction for LKAS in general… openpilot limits the
rate limit of the LKAS command, but I am talking about a friction or rate limit on the steering ANGLE when
openpilot is demanding maximum or strong torque… it only turns the wheel slowly."* **He was right, and the
previous session's "it's an openpilot safety feature" answer was wrong.**

## 2. The delta, from the images (RULE 4)

V74 → V75 is **142 bytes, 35 runs, all attributed**: `FactorC Y[0]` 429→**566** (11 modes), `FactorE X[1]`
400→**200** (13 modes), the probe cave rewritten 45→68 B, 10 CRC words. **Nothing else.** Friction,
`0xC407E`, `sar`, r24/r26, the ceiling table, `0x454FE` and **every mode-24 (manual) record** are
byte-identical to V74.

★ **Anchor: of 17 monitor-related constants byte-read across stock/V74/V75, only TWO were ever moved by any
build** — `0xC63A0` (1024→2048) and `0xC407E` (511→850), both at V72/V73, both identical V74↔V75.
**No build has ever moved a fault threshold** ⇒ the fault is in the **signal**.

## 3. The answer — a GATE-2 loop-gain overshoot, bracketed by our own two flights

The damper's **ramp-regime incremental gain** `k = (C_Y0·Y[1]>>10)/(X[1]−X[0])` is a
**frequency-independent scalar** multiplying the entire damper path ⇒ it scales loop gain equally at every
frequency, and **no plant model is needed to compare builds**.

| build | `C_Y0` | `E_X1` | M | **k** | **vs V74** | on-car |
|---|---|---|---|---|---|---|
| stock | 0 | 400 | 0 | **0.0000** | −∞ dB | damper **identically zero below 35 km/h** |
| **V74** | 429 | 400 | 225 | **0.5799** | **0 dB** | **1,011 s clean** |
| **V75** | 566 | **200** | 297 | **1.5798** | **+8.70 dB** | **faulted** |
| new cut | 566 | 400 | 297 | **0.7655** | **+2.41 dB** | built, unflashed |

⇒ **`k* ∈ (0.580, 1.580]`. V74's gain margin through this path is >0 dB and <8.70 dB.**

Firmware-side phase, all byte-extracted (PID coefficients `KP = 0.250`, `KI = 2.991/s`, `KD = 0.002 s`;
the 16 Hz IIR; the rate EMA; the 100 Hz ZOH): **−20.9° @ 7.79 Hz, −55.4° @ 21 Hz** — well inside 90°.
⇒ **the firmware alone cannot invert the damping; the instability lives in the plant** (measured Q ≈ 13.6).
⚠ **No absolute Nyquist plot or gain margin in dB exists**, because the plant transfer function is not
measured. One was deliberately **not invented**. The relative answer does not need it.

### 3a. The relay — real, ours, and NOT the fault
`FactorE Y[1] := Y[2]` makes the magnitude **constant** across `X[1]→X[2]` while the sign comes from
`gp-0x6abe` ⇒ a **bang-bang relay**. Stock `[0,140,539,927]` has **no flat segment**. Band: **85–531 °/s
(V74) → 42–531 °/s (V75)**. 🛑 **This is exactly V72's error, which `STATE.md` claimed the design avoided**
(*"`Y[0]=0` ⇒ no chatter mechanism"* holds only **below `X[1]`**).
★ It is a **100 Hz sampled-data artifact**, not a table discontinuity — at 21 Hz the zero crossing takes
2.6 ms, a quarter of one sample, so the held output steps ±M in one tick whatever the shape.
🛑 **But it is not the fault**: engaged creep sits above 200 ct only **21.8%** of the time, so ~4/5 of the
faulting regime is in the **ramp**; and a 5,224-point constrained search shows that at matched peak gain a
strictly monotone no-flat surface damps the symptom band the **same** ⇒ **the plateau is not what buys the
damping; the gain is.** *(This retracts a mid-session recommendation to lower `FactorE Y[1]`.)*

### 3b. Eight refuted mechanisms — all on the same constraint, V74 flew clean
| mechanism | why dead |
|---|---|
| surface arithmetic | 0 non-monotone X in 510 records; no `divq`; 2263× s32 headroom |
| `FUN_000347b8` ceiling check | needs `gp-0x6bd0` > 517; FactorE has **no headroom past `X[3]`** ⇒ creep supremum is exactly 512. **215-count margin, 43× tolerance** |
| int/float lockstep (V24–V27 class) | **no float mirror of FactorC/E exists in the ROM** (exhaustive unaligned search, positive control found the ceiling mirror) |
| governor slew-step | `FUN_0004595a` **tolerates output lagging target** |
| `FUN_00045a20` | `gp-0x6bd0` **cancels** — both operands carry the aggregator sum identically |
| duty threshold | **V74 clears the 1/3 break-even 1,411× engaged (2.57/s)** and never faulted |
| dwell | **V74 sits 210 consecutive 1 kHz cycles = 21× the 10-cycle trip requirement, on all 35 entries** |
| per-event / at-rail transitions | **V74 is MORE rail-coincident per transition** (0.800 vs 0.663); V75's volume edge fails its episode sign test (p = 0.289); **in the launch events the direction reverses** |

⇒ **The proximate monitor is NOT identified.** Prime suspect stays **Monitor 2** (`FUN_00043e44`): ±5/1024
on `gp-0x6b98`, charge **+0.001** / leak **−0.0005** ⇒ break-even duty **1/3**, trip at 0.01 ⇒ **10
consecutive 1 kHz cycles = 10 ms → DTC 0x1c/0x1d → `0xF00049`, latched until power cycle**. Sign
alternation **does not cancel**; there is **no minimum-duration gate**. Its corridor compares `gp-0x6b04`
(PRE-clamp) against `gp-0x6b98` (POST) ⇒ **it can only open when a clamp BINDS.**
✅ **And that binding path is now CLOSED as impossible.**

### 3c. The bus → `gp-0x6b98` scale — closed, exactly
**`k = 3564/8192 = 891/2048 = 0.4351`**, exact integer arithmetic, every hop address-cited. The `×−4`
intake and the `arb_setpoint_limit` cancel because this car's record is flat 16384, matching the intake's
own ±0x4000 wall.
⇒ **a rail-pinned openpilot command (4096) delivers just 1782 counts, 37.4% of the 4762 governor ceiling.**
Even the damper's loosest aggregator bound gives `1782 + 2048 = 3830 < 4762`. **And the scale is
byte-identical on V74 and V75, so it could never have discriminated them.**

## 4. Goal 2 — LKAS "friction" is viscous damping, and the honest answer is uncomfortable

🛑 **No live hard rate limiter on the steering angle exists anywhere in this firmware.** The shaper's slew
limiter `0xC61D6` = **0, disabled in stock** (re-enabling already rejected at V16); `0xC6194` is
architecturally dead; a 45-site sweep of `gp-0x6b98` finds only **magnitude** clamps.

🛑 **And no term is indexed by commanded torque** — `FactorB`, the one torque-domain factor, is **flat
unity in modes 24 AND 26**. Opposition is mediated entirely through **motion**, never demand.

🛑 **The friction lane `gp-0x6b26` is a DC-BLOCKED DIFFERENTIATOR** (`gp-0x6c2c`: EMA → first difference →
EMA): gain ≈ **0 at DC**, 3.08× at 7.79 Hz, 7.5× at 20.9 Hz. **For a sustained slow turn — the complaint's
own shape — it contributes nothing.** *(This retracts a mid-session claim that it is the always-there
baseline.)*

Sustained drag at creep, counts of opposing torque at 20 °/s: **stock 0 · V74 47 · V75 129 · new cut 62.**
**All of it is the damper, and stock has none.** ⇒ the *recent* creep heaviness is **ours**, introduced at
V74 — which also first made mode-26 friction ×1.5 live (manual byte-stock), on top of `0xC407E` 511→850
since V73, which is **not** mode-indexed and so raises the drag ceiling **in manual too**.

⚠ **But the part of the complaint that predates all of this is NOT explained by firmware.** Stock's damper
is dead below 35 km/h and, above it, **98.7% of engaged highway frames sit below `FactorE`'s rate
threshold**. So the long-standing sensation is either mechanical (rack/column), or the command rails, or
something not yet found. **Say that rather than offer a lever that will not change what he feels.**

⊕ **A relevant fact fell out of §3c:** LKAS at its own rail uses only **37.4%** of the EPS governor
ceiling, and the binding constraint in that chain is `0xC61B2`/`0xC61B4` = 2048 (already 4× stock's 512).
**There is real unused authority headroom.** That is a separate workstream with its own risk — recorded,
not proposed.

## 5. Built this session

`39990-TVA,A160-V75-V74BASE-ENGCOLS13-levers-**CY0.566**-magprobe-6bd0-thermo-6ac2-0x13000-0x100000.rwd`
rwd `b245e1d17ed1ca4ec51a06a0a17a41afe37ba369b819eb0e2db02d2d49781765` ·
image `9a96b7fe0cb5263f9cbc528cb0a0a67744048f439373f326f5a7c966ff37f3d1`
50/50 CRC PASS · full readback · **mode 24 byte-stock across all six record types, resolved through the
pointer arrays.** 🛑 **Not clearance to fly.**

## 6. Corrections to the record made this session
1. **`BUILD-LINEAGE.md:259`** — "all weights unity and stock ⇒ no hidden loop gain" is **FALSE**;
   `0xC63A0` = **2048 since V72**. RULE 4 class.
2. **RULE 7** files V72's Lever C as "inert by table selection" — it is a bare `tp` scalar, **MODE-PROOF
   and always live**; it was only *functionally* inert because the damper it weights was zero. **V74 armed it.**
3. **RULE 8's "330 °/s"** is a **units error** — route 5d's max is **412 °/s / 1,941 counts**. Added
   **RULE 8b**: an observed-envelope pass must state which regimes the envelope does *not* contain.
   **Route 5d has ZERO engaged stoplight stops** ⇒ every V75 safety check ran on telemetry that
   structurally could not contain the faulting regime.
4. **`tp+0x74a4 = 0xC64A4`, not `0xC74A4`** — the off-by-0x1000 trap, **made twice now**. It briefly
   declared Monitor 2 "permanently gated off"; it is **armed in every build**. The orchestrator propagated
   it by verifying the handed address instead of deriving it. **New rule: recompute `tp + disp` and show
   the addition.**

## 7. Open — in priority order
1. 🛑 **Read the stored DTC.** `flashing-2020accord/eps-read-dtcs.py`, UDS **`19 02 FF`**, **bus 1**,
   `0x18DA30F1`/`0x18DAF130`; proven on this ECU. Fallback `22 48 01`. **Operator confirmation required.**
   It discriminates every remaining hypothesis in one shot.
2. **`g4`** — `FUN_00038148`'s stage 2. Decides whether reverting `0xC63A0` 2048→1024 *increases* net
   damping (PATH 2 **subtracts**, so that cal weights only the cancelling replica). **Do not ship blind.**
3. `FUN_00070a98` (DTC `0x26`) — structural only; **its constants were never checked against `tp`.**
4. Whether the long-standing friction sensation is mechanical. Needs an on-car A/B, not more bytes.

## 8. Artifacts
Scripts: `analysis-2020accord/v75_fault_{lerp_arrays,surface,weight_check,const_anchor}.py`,
`v75_step_{lib,replay,followups,burst,rolling,rolling_null,cooccur,cooccur_close}.py`,
`v77_gate2_*.py`. Memories: `reference-accord-v74-v75-damper-is-a-sampled-relay`,
`reference-accord-v75-fault-refutation-ledger`, `reference-accord-monitor2-corridor-and-the-c64a4-trap`,
`reference-accord-lkas-friction-is-viscous-not-a-rate-limit`.
