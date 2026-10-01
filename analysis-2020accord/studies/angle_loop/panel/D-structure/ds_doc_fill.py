# -*- coding: utf-8 -*-
"""ds_doc_fill.py -- fills the design page's markers from the result files (the listings from ds_asm_out.txt, the byte
lists from ds_bytes_out.txt, every numeric table from ds_report_out.md / ds_report_summary.md / ds_d3_tune_out.txt), so the
page quotes the scripts' output verbatim.  The prose blocks are this file's; every number in them was read off the same
files.  usage: python ds_doc_fill.py"""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOC = HERE.parents[4] / "docs" / "specs" / "design" / "panel" / "DESIGN-PANEL-D-structure-2026-10-01.md"


def listing(cid):
    out, on = [], False
    for l in (HERE / "ds_asm_out.txt").read_text(encoding="utf-8").splitlines():
        if l.startswith(f"{cid}: cave"):
            on = True
            out.append(l)
            continue
        if on and (l.startswith("=====") or (l and l[0] in "BD" and ": cave" in l)):
            break
        if on and ("('half'" not in l or " TBL " in l):
            out.append(l)
    return "```\n" + "\n".join(out) + "\n```"


def bytelist(cid):
    out, on = [], False
    for l in (HERE / "ds_bytes_out.txt").read_text(encoding="utf-8").splitlines():
        if l.startswith(f"{cid}: "):
            on = True
            continue
        if on and l.startswith("====="):
            break
        if on:
            out.append(l)
    return "```\n" + "\n".join(out) + "\n```"


def block(name):
    return BLOCKS[name]


BLOCKS = {}

BLOCKS["D1A"] = r"""**The loop (integer; every line is Honda's bytes or C1's cave, unchanged):**

```python
r26 = clamp(8*th_h[n] + 8*th_h[n-1], +-65535)              # E1 0x28F4C, E2 0x28FA4, a 0 / b 8192 / C 65535
E   = (sp69ae << 2) - r26 ; E1 = (E * G(v)) >> 8           # C1's cave at 0xC4C00 (displaced pair, the walk, mul ; sar 8)
I   = clamp((I8 >> 3) + ((dz(E1 >> 5) * 56) >> 3), +-(4096 << 7))   # frozen when |tq| > 512 or the ramp is not full
P   = clamp((E1 * 112) >> 8, +-15360)                       # 0x29E34..0x29E5C
r27 = E_prev if -768000 <= E_prev <= 768000 else E1         # 0x29E5E..0x29E7E cmovnc (E_prev = gp-0x6cf8 = last r16)
D   = clamp((256 * (E1 - r27)) >> 3, +-10240)               # 0x29EDE zxh r7 ; 0x29EE0 mov r16,r8 ; sub r27,r8 (STOCK)
```
- **What D is, physically:** per deg/s of wheel rate the average D is `0.02·Kd·G/256` S counts = 5.12·G/256 (26.5 S at G 1326,
  8.0 S at G 399 = 11.75 m/s); it ALSO responds to the setpoint rate with the same gain (D on error), and it arrives as one
  impulse per 0.1° count of θ_h (§2.0).
- **Why Kd 256:** in round 2 (`ds_explore2_out.txt`) Kd 200 collapses the 1–3 m/s envelope (b_hi binds: D too small at low
  G), Kd 320 rule-binds the whole table at 49 T/deg. 256 is the best compromise; the 20 Hz rule then caps G FLAT at 1326
  everywhere except the ms_free dip. **EVIDENCE** (model).
- **Bytes: 185** (17 in-place code — C1's seven without E5 — + 144 cave (C1's 96 code bytes + this table's 48) + 24 cal).
  **No RAM.** Its D costs zero code bytes: that is its only merit.

{BYTES_D1a}

The cave is C1's listing with this candidate's table (assembled and H1-tested in `ds_asm_out.txt`, 0 / 60 000).

- **GATE 2 (brief's set): 0 fails.** Tier A min J_hi 52.3° (1 m/s), ms_free 48.1°; tier B min b_q×J1.0+h10 31.6° (15.5 m/s);
  min exact GM 8.4 dB; **M20 3.12 against V295's 3.38 and L20 0.92× V295's — both rules nearly binding** (they set the table).
- **Re(T/ω):** at age 0 −0.79 at 17–20 Hz (0.96× V295's); at age 10 −1.51 at 10 Hz where V295 is −1.17 (worse), −0.80 at
  20 Hz (0.90×).
- **Goal metric: 0.944 at 11.9 m/s — below 0.95** (the ms_free dip, G 399). All other bands ≥ 0.953.
- **Time domain (§6.4):** the fewest dwell-then-jump events at 3–5 m/s (4 / 4), but **the largest release lurch of any
  candidate (firm 9.6° / 18.6° on bc, light 10.5° / 20.5°)**, the largest step overshoot (21.6 % / 42.1 %), **5–30 Hz
  texture 2.5 counts rms (above the 2.0 line bar)** and **40–200 Hz content 26.8 counts rms (35× B0r)**. The release lurch
  is the DCL clamp: once the wheel moves faster than ~40 deg/s, one frame's θ_h step drives D past 10 240 and the damping
  is clipped exactly when the release needs it. **EVIDENCE** (sim); the mechanism is the arithmetic above.
- **Verdict on its own terms:** the cal-only D answers "can the angle operand's own difference be the D" with **yes in the
  loop, no in the lane**: it fails the texture bar, the goal metric at 11.9 m/s and every release scenario. Not
  recommended by its own numbers; kept as the scored minimum-bytes implementation of D1."""

BLOCKS["D1B"] = r"""**The loop (integer):** C1's angle P + I and G walk unchanged; the D operand is built in the cave and handed to Honda's
multiply in r26:

```python
d   = ld.w gp-0x6cc4                        # the 1 kHz motor-position accumulator (FUN_0003bd7c @0x2224A, before the PID)
op  = (d - d_prev) << 3 ; d_prev = d        # cave RAM gp-0x6c44 (written on every PID tick, not on skips)
D   = clamp((72 * op) >> 3, +-10240)        # 0x29EDE zxh r7 (Kd 72) ; 0x29EE0 mov r26,r8 ; nop  -> D = 72 (d - d_prev)
```
- **Scale (BELIEF on the frame, EVIDENCE on each link):** θ (gp-0x6a00) moves 1.155 counts per lin(d) count near centre
  and 0.962 outward (TRACE angle §2.1), lin(d) = d/32.17 per 0.1°, pol −1 ⇒ Δd = −278.5 counts per degree near centre,
  −334 outward. D = −20.05 S per deg/s near centre, −24.0 outward (the VGR correction lives in gp-0x6a00, not in the
  accumulator). The gate used the near-centre scale; at the outward scale M20 rises ×1.2 to 2.9 (< 3.38).
- **No first-tick guard (8 bytes saved, declared):** after skip ticks `d_prev` is stale; the first PID tick gives ONE tick
  of D, bounded by DCL (10 240 S → ≤ 26 T counts peak through the output lag) and multiplied by the ramp (≈ 0 at an engage).
  A re-reference of gp-0x6cc4 by `FUN_0003bcb2` while engaged does the same (one tick, ≤ DCL).
- **Bytes: 204** (20 in-place: the seven + `0x29EE0` 3 bytes; 160 cave = 112 code + 48 table; 24 cal). **RAM: 1 word,
  gp-0x6c44** (GATE 1 §1.3: 0 accesses of any form in V295).

{BYTES_D1b}

{LIST_D1b}

- **GATE 2: 0 fails.** Tier A min J_hi 46.3° at 1 m/s (thin: 1.3°); tier B min b_lo×J_hi+h10 32.0° (1 m/s), b_q×J1.0+h10
  33.7°; **min exact GM 15.6 dB, the largest of all** (the D does not lag, so it adds no phase at the GM frequency).
- **Re(T/ω), the best of every candidate:** age 0 −0.47 (5 Hz) … −0.17 (20 Hz) = **0.21× V295 at 20 Hz**; age 10 essentially
  neutral at 10–20 Hz (−0.06 … +0.04).
- **Goal metric ≥ 0.962** (17 m/s) — passes, margin 0.012.
- **Time domain:** ≈ B0r (dj 5 / 9 at 3–5 m/s, 3 hold slips at 15–30 m/s under the harness road disturbance, lurch firm 4.2° /
  6.0°, light 6.3° / 6.9°, droop 4.6° / 5.2°), texture 0.64 / 0.78 counts (≈ B0r)."""

BLOCKS["D1C"] = r"""**The loop (integer):** the "10-tick-aware" difference — the held angle's step spread over ~8 ticks:

```python
s_new = ld.w gp-0x3d30                       # the fb state, stored at 0x28FA8 this tick (= 8 th_h[n])
ds    = (2*s_new - r26) << 3                 # s_new - s_old = 8 (th_h[n] - th_h[n-1]) counts, << 3
lp    = lp + ((ds - lp) >> 3)                # 21 Hz pole; cave RAM gp-0x6c44 ; first tick after a skip: lp := 0
D     = clamp((250 * (-lp)) >> 3, +-10240)   # 0x29EE0 mov r26,r8 ; nop ; Kd 250  -> 20 S per deg/s at DC
```
- **Bytes: 232** (20 in-place + 188 cave (140 code + 48) + 24 cal). **RAM: gp-0x6c44.** Hazard: Δs is read from the clamped
  r26 (±65 535 = 409.6°): beyond that angle D is garbage (P is too, as in C1).

{BYTES_D1c}

{LIST_D1c}

- **GATE 2: 0 fails;** min exact GM **7.0 dB** (b_lo×tau6+h10, 8 m/s) — the thinnest GM of the angle kind.
- **Re(T/ω): worse than B0r at 5–13 Hz** (age 0 −1.16 … −1.21 at 5–10 Hz vs −0.84; age 10 −2.00 at 5 Hz) — the 21 Hz pole
  adds lag where the D matters — and better at 17–25 Hz.
- **Time: 5–30 Hz texture 5.4 / 3.9 counts rms in holds — above the 2.0 bar (a FAIL of the line-only gate)**: the low-pass
  turns the 100 Hz impulse train into a 5–30 Hz one. dj 5 events at 8–12.5 m/s on bc.
- **Verdict on its own terms: dominated by D1b** (more bytes, worse 5–13 Hz damping, texture). The answer to "is a
  10-tick-aware difference possible in the cave?" is yes (40 code bytes, one RAM word); it is not worth having, because
  the fresh accumulator (D1b) gives the same D with no hold at all for fewer bytes."""

BLOCKS["D2A"] = r"""**The loop (integer):**

```python
op = ld.h gp-0x6abe                                        # fresh 1 kHz motor-rate EMA, -4.712 counts per deg/s
op = 0 if (op + 13000) > 26000 (unsigned) else op          # Honda's OWN validity form (FUN_0003f776): incl. the 0x7FFF sentinel
D  = clamp((34 * op) >> 3, +-10240)                        # 0x29EE0 mov r26,r8 ; nop ; Kd 34 -> -20.0 S per deg/s
```
- The validity test is the one `FUN_0003f776` applies before it writes `gp-0x6a56`, so the fresh D is zero exactly when
  the held operand would have been zero: no new fault exposure. A pure in-place alternative (`0x29EE0 → ld.h -0x6abe[gp],r8`,
  4 bytes, no cave instructions) was **rejected**: on an invalid motor rate it would multiply 0x7FFF into D and rail DCL
  (10 240 S ≈ 1 650 T counts) for as long as the fault lasts.
- **Bytes: 206** (20 in-place + 162 cave (114 code + 48) + 24 cal). **No RAM.**

{BYTES_D2a}

{LIST_D2a}

- **GATE 2: 0 fails;** tier A min J_hi 46.7°; min exact GM 15.1 dB.
- **Re(T/ω):** age 0 −0.57 … −0.31 (**20 Hz −0.34 = 0.41× V295**); age 10 −0.74 … −0.14 (**20 Hz −0.20 = 0.22× V295**).
- **Goal metric ≥ 0.961.** **Time ≈ B0r** (dj 6 / 7, lurch firm 4.1° / 5.7°, droop 4.7° / 5.2°, texture 0.67 / 0.77).
- **What D2a vs D1b decides:** the same D at DC; D1b has no EMA (2.5 ms less lag: −0.17 vs −0.34 at 20 Hz) and costs a RAM
  word; D2a costs no RAM and inherits Honda's validity test."""

BLOCKS["D2B"] = r"""**The loop (integer):** D2a's D, plus a first-order lead on E′ for P only; Honda's I keeps the unled E′:

```python
E1  = (E * G(v)) >> 8
w   = w + ((E1 - w) >> 4) ; w = E1 on the first tick after a skip   # cave RAM gp-0x6c40 (Honda's sentinel gp-0x6cf8)
e5  = 0 if frozen else E1 >> 5          # Honda's 0x29D7A/7C done in the cave; returns to 0x29D7E: the I integrates E1
r16 = 2*E1 - w                          # = E1 + (E1 - w): P = clamp((r16 * 112) >> 8) sees the lead
# Lf(z) = 1 + (1 - (1/16)/(1 - (15/16) z^-1)): zero 5.22 Hz (cancels the 5.05 Hz output-lag pole 992/1024), pole 10.27 Hz
```
- **Output-lag compensation, in the cave:** for the P path the 5.05 Hz output stage becomes, in effect, a 10.3 Hz one; the
  D (fresh rate) and the I still see the 5.05 Hz lag. **Honda's oscillation detector does not see it:** worst simulated
  `gp-0x6c2c` excursion 0.224 of the threshold (the stiff hand's grab at 3 m/s, the same for every candidate), **zero
  reversals in every run** (§3.0, §6.4). **EVIDENCE** (sim).
- **Bytes: 246** (20 in-place + 202 cave (154 code + 48) + 24 cal). **RAM: gp-0x6c40.**

{BYTES_D2b}

{LIST_D2b}

- **GATE 2: 0 fails;** min exact GM 11.4 dB; T530 −1.4 dB (the closest of the angle kind to the +3 dB bar).
- **Envelope vs B0r: +27 % at 1–5 m/s, +25 % at 8, +16 % at 15, +18–20 % at 17–30**; in the ms_free dip −10 % (10 m/s)
  … +11 % (12.5 m/s).
- **Re(T/ω):** age 0 −0.79 … −0.89 at 5–10 Hz (≈ B0r), **−0.52 at 20 Hz (0.63× V295)**; age 10 −1.31 at 5 Hz, −0.20 at 20 Hz.
- **Goal metric ≥ 0.967 — the best of all candidates.**
- **Time:** dj 4 / 4 at 3–5 m/s (fewest of the angle kind, with D1a/D1c/D2c), **0 hold slips at 15–30 m/s** (B0r 3), **the
  smallest release lurch of the angle kind (firm 3.2° / 4.1°)**, the smallest engage droop (4.1° / 4.4°); costs: texture
  1.0 / 1.8 counts (5–30 / 40–200 Hz, 1.5–2.3× B0r, under the bar), a ×2 P kick on setpoint steps (step peak T at 8 m/s
  1 029 vs B0r 787 counts)."""

BLOCKS["D2C"] = r"""**The loop (integer):** the same filter on the MEASUREMENT, before the error is formed; P and I both see it:

```python
w   = w + ((r26 - w) >> 4) ; w = r26 on the first tick      # cave RAM gp-0x6c40
r26 = 2*r26 - w                                             # the led feedback
E   = (sp69ae << 2) - r26 ; E1 = (E * G(v)) >> 8            # then C1's freeze/I/P and D2a's fresh D, unchanged
```
- **Bytes: 242** (20 in-place + 198 cave (150 code + 48) + 24 cal). **RAM: gp-0x6c40.**

{BYTES_D2c}

{LIST_D2c}

- **GATE 2: 0 fails;** min exact GM 11.9 dB.
- **Envelope vs B0r: +19–20 % at 1–5 m/s, +17 % at 8, 0 … +7 % in the dip, +11–14 % at 15–30.**
- **Re(T/ω):** age 0 −0.80 … −0.87 at 5–10 Hz, −0.50 at 20 Hz; age 10 −1.29 at 5 Hz, −0.20 at 20 Hz.
- **Goal metric ≥ 0.962.** **Time:** the smallest step overshoot of the angle kind (12.1 % / 12.3 %), lurch 3.1° / 3.8°,
  dj 4 / 4, 0 hold slips; texture 1.0 / 1.7 counts."""

BLOCKS["PLACEMENT"] = r"""- **D2b vs D2c are different loops, not the same loop with a different T_ref.** The record's law ("placement decides
  transient authority, not the filter", V289) was for a filter that sees the whole error. Here the forward lead acts on P
  only, the I integrating the unled E′; the feedback lead acts on r26, so the I integrates the led error. On the θ path
  `C_θ(fwd) = −g·(Kp/256·Lf + Ki/32768/(1−z⁻¹))·r26` vs `C_θ(fb) = −g·(Kp/256 + Ki/32768/(1−z⁻¹))·Lf·r26`. The lead
  under the integrator costs phase at the I corner, hence D2b's +4–7 % envelope over D2c. **EVIDENCE** (model).
- **A forward lead on P AND I** (the cave returning E_L through the normal path, 4 bytes fewer than D2b) has exactly
  D2c's θ path and differs only on the setpoint path by Lf: that is the record's case — same margins, a ×2 setpoint kick.
  It is dominated by D2c (same loop, more authority on 0xE4 steps) and was not carried.
- **Transient authority, measured (step scenario, nominal, peak lane T):** 3 m/s D2b 2 171 / D2c 2 134 / B0r 1 978;
  8 m/s D2b 1 029 / D2c 861 / B0r 787; at ≥ 12.5 m/s all within ±7 %. Step overshoot D2b 15.8 % / D2c 12.1 % (max over
  speeds). **EVIDENCE** (sim).
- **The notch (the brief's other option) was not carried.** In an angle loop the crossover is 0.4–1.5 Hz; the 20 Hz
  content is the D term's, and the fresh D already gives 0.2–0.4× V295's 20 Hz anti-damping with L20 ≤ 0.70× V295's. A
  biquad costs two state words and ~40 bytes, and the record's only notch (V289) moved the ring to a pre-existing 16 Hz
  pole. Nothing in the gates asks for it. **BELIEF** (no notch was simulated)."""

BLOCKS["D3INTRO"] = r"""The literal request: "angle P outside, the EXISTING V282-style rate loop inside (rate feedback kept as the inner damping
with its 16.5 Hz lag, angle error forming the rate setpoint)". The x operand stays the RATE (no E1), E2 restores stock's
sum, a/b go back to stock (923/1560: DC 30.89, 16.5 Hz pole), and the cave turns the angle error into the rate setpoint:

```python
x     = gp-0x6a56 (D3a, held) | gp-0x6abe (D3b, E1' at 0x28F4C; the +-12000 bail now gates the 0x7FFF sentinel)
s_new = ((923 * s_old) >> 10) + ((1560 * x) >> 10) ; r26 = clamp(s_old + s_new, +-65535)      # 0x28F86..0x28FBC
th    = ld.h gp-0x6a00 ; e4 = sp69ae - (th << 2)  (0 if |th| > 12000: the -0x8000 baseline wrap)  # the cave
sp_r  = (e4 * G(v)) >> 6 ; E = (sp_r << 2) - r26  (D3a)  |  (sp_r << 2) + r26  (D3b: gp-0x6abe = -x/1.698)
I     = Honda's on E (Ki 12, frozen as C1) ; P = clamp((E * Kp) >> 8) ; D = 0 (Kd 0, DCL 0 as in V295)
```

**Why it is an I-P loop (EVIDENCE, arithmetic on the bytes):** Σₙ r26 = 30.89·Σₙ x = 30.89 × 8 × 1000·Δθ(deg) per degree of
travel, so the inner I state is `(Ki/32768)·Σ(4 sp_r) − 7.54·Ki·(θ − θ_engage)` S counts: a P on the MEASURED angle
(−90 S per degree at Ki 12) that the setpoint does not see, plus the integral of the outer error. At DC the integral wins
(no steady error); at 0.04–0.2 Hz the measurement-P holds the wheel back from the setpoint. That is the tracking cost the
goal metric reads, and the reason the releases are gentle (§6.4: the smallest lurch and step overshoot of all)."""

BLOCKS["D3A"] = r"""- **Bytes: 199** (15 in-place: E2, B2, A2, E4, H, V1 — no E1, no D edit; 166 cave = 118 code + 48 table; 18 cal: a, b, C,
  DB, Ki, ICL, Kp×5). **No RAM.**

{BYTES_D3a}

{LIST_D3a}

- **Inner gain is capped by the held operand:** Kp_in 40–46 FAILS the gates at almost every speed (round 1/2: b_lo+h10,
  J_lo+h10 at low speed); Kp 24 passes. This is V282's lesson, re-measured on the credible set.
- **GATE 2: 0 fails; min exact GM 6.3 dB** (b_lo×tau6+h10, 7.75 m/s) — the thinnest of all; T530 −0.7 dB.
- **Envelope vs B0r: −29 … −38 % at 1–8 m/s**, −6 … −23 % at 10–19 m/s, −9 … −13 % at 22–30 m/s.
- **Re(T/ω): the worst 5–13 Hz anti-damping of all** (age 0 −1.55 … −1.66, age 10 −2.49 at 5 Hz): the 16.5 Hz fb pole and
  the hold sit in the inner loop's own phase.
- **Goal metric 0.913 at 11.9 m/s — FAILS 0.95** (0.914–0.945 at 12.5–19 m/s). `ds_d3_tune.py`: Ki 24 makes it worse (0.837).
- **Time:** the smallest firm-release lurch (2.8° / 1.7°) and step overshoot (8.9 %), the largest dj count at 3–5 m/s
  (8 / 8) and dj 4 at 8–12.5 m/s on bc; tracking fit gain 0.81–0.98 at 0.2 Hz, 0.52–0.91 at 0.5 Hz.
- **Verdict on its own terms:** the existing rate loop inside an angle loop is gentle and slow; it fails the goal's tracking
  criterion and has the thinnest margins. Not recommended by its own numbers."""

BLOCKS["D3B"] = r"""- **Bytes: 200** (16 in-place: E1′ is ONE byte at `0x28F4E` (`aa → 42`), + E2, B2, A2, E4, H, V1; 166 cave; 18 cal). **No RAM.**

{BYTES_D3b}

{LIST_D3b}

- **GATE 2: 0 fails;** min exact GM 8.9 dB; **T530 +0.2 dB (the highest of all, under the +3 dB bar)**.
- **Envelope vs B0r: +11–17 % at ≤ 8 m/s, +52 % at 10, +38 % at 11.75, +32 % at 12.5, +18–21 % at 15–22, +26 % at
  26.9–30 — the highest of all at 10–13 m/s**, where every angle-kind design is pinned by ms_free.
- **Re(T/ω):** age 0 −1.43 … −1.48 at 5–7 Hz, −0.73 at 20 Hz (0.89× V295); age 10 −1.69 at 5 Hz, −0.55 at 20 Hz.
- **Goal metric 0.894–0.949 at 10–19 m/s — FAILS 0.95.** Raising Ki does not rescue it (§4.3).
- **Time:** the smallest step overshoot (1.2 %), lurch 2.5° / 1.5–3.1°; tracking fit gain 0.73–0.90 at 0.2 Hz — the worst.
- **light_b (the prior, report only): PM 1.4° at 26.9 m/s, a 4.4 Hz ring with ζ 0.010** — the cascade is the structure most
  exposed to the prior's light damping (D3a: PM 0.7°). R3 covers the band (§5)."""

BLOCKS["D3C"] = r"""**D3c = the cascade with the angle error entering THROUGH the map path** (a cave at `0x29032`, replacing
`ld.h -0x69ae[gp],r13`, returning a scaled error in r13; LIM, the driver-torque setpoint taper, the 8-bit idx, the map and the
idx-keyed Kp/Kd stay). Evaluated, not carried:
- **Its linear loop is D3a's / D3b's** with ka·G replaced by the map's slope, so its envelope, 20 Hz numbers and the I-P
  tracking failure are theirs (§4.1–4.3). **EVIDENCE** (the chain is a static gain at small signal: tracer `setpoint_chain`).
- **What it adds:** the outer error is quantised to one idx per 64.5 r22 counts (≥ 0.1° per idx only if the cave scales the
  error ×16, which limits the outer range to ±24° before idx saturates at 240 = a constant-rate slew); Kp/Kd become
  keyed on |angle error| (a cal-only nonlinear gain the direct path lacks); **the setpoint taper (`0xCB924`/`0xCB8B4`, flat
  to |tq|>>5 = 80, zero at 112) would fade the OUTER error under the driver's hand — a release by construction**, which
  is the one property worth carrying to C2.
- **Why not carried:** it inherits the cascade's tracking failure, needs a new hook site, and its liveness is not traced.
  From the Ghidra listing of `0x28FC8..0x2906F`, r7, r8, r12 and r14 are written before being read after `0x29032`
  (candidates for the link and scratch) — **BELIEF until a liveness trace on the full function**."""

BLOCKS["CONCERNS"] = r"""1. **Everything above ~8 Hz is model, not measurement** (the r71b ident sees nothing above 8 Hz). The 5–25 Hz rankings rest on
   the hold, the EMA, the output lag and the transport delay, which are bytes; the plant there is BELIEF.
2. **The rate model changes the baseline's numbers.** The bytes say x is the held EMA of the motor rate (§1.2); the C1 pages
   used a 3-tick position difference or the ideal rate. Under the EMA, B0's Re(T/ω) and PM move by 0.1–3° (§1.3). Every
   design number here uses the EMA; the C1 pages' numbers are not directly comparable without re-running them under it.
3. **ms_free at PM ≥ 45° (the brief's single corner) binds every design at 10–12.5 m/s** and costs the C1 lib table
   (B0) 12 sub-bar points. If the judges treat ms_free as report-only (C1r2's choice), every envelope here rises at
   10–12.5 m/s by up to ×1.3 (B0 `env_final_B0.json` per-member results) — and D3b's advantage there shrinks.
4. **The D1b frame scale** (motor counts per degree of gp-0x6a00) varies ×0.83–1.0 with the steering angle (the VGR
   correction); the gate used the low end. Measuring the D gain on the car (instrument §5.3) settles it.
5. **No candidate removes the low-speed friction misses** (dj 4–9 events per scenario set at 3–5 m/s, stick 8–11 % at
   3 m/s, light-hand lurch 5.7–6.9° on the angle kind). Structure does not fix friction; a friction term (C1r2 §6.4's C2)
   would sit in any of these caves.
6. **The light-hand case is the worst release on every angle-kind design** (5.7–6.9° on nominal/bc at a hand below the
   512 freeze threshold): the I winds behind a hand the freeze cannot see. Common to the structure class; declared.
7. **The cave encodings are BELIEF until Ghidra decodes a built image (H5)**, despite 27 form controls, 11 exact-byte
   Ghidra decodes and 0 / 60 000 interpreter mismatches per cave.
8. **GATE 1 for gp-0x6c40 / gp-0x6c44 is static** (0 accesses of every form, controlled); register-indirect access cannot be
   excluded statically. V289's flown cave used these words (record) — on-car precedent, not proof for this image.
9. **The setpoint-hold age** (frame before or after the lane in the arrival tick) is 1 ms of BELIEF; the linear model uses
   1..10, harness_time 0..9.
10. **The C1r2 page and the C1 lib disagree on the table** (the lib's 7-knot table is a later refit; the page's 6-knot table
    fails the factorial b/1.9×J1.0×tau6+h10 at PM 8.7°). I scored the lib (B0) and my own refit (B0r). Reported, not fixed.
11. **The fork interlock byte V1 is counted in every candidate's bytes** (1 byte) for parity with C1r2; it is a fork
    prerequisite, not a loop term."""

BLOCKS["MISSES"] = r"""### 5.1 Pre-declared misses (each with its band and predicted size; every number from §6)

Common to every candidate (the class C1r2 declared, re-measured here on each structure):

| goal criterion | band | B0r | D1b | D2a | D2b | D2c | D3b | basis |
|---|---|---|---|---|---|---|---|---|
| low-speed stick-slip gone; dwell-then-jump ≤ V282 | 3–5 m/s | dj 7 / 7 per scenario set, stick 9.3 % | 5 / 9, 9.0 % | 6 / 7, 9.0 % | 4 / 4, 7.8 % | 4 / 4, 8.2 % | 4 / 6, 9.7 % | sim nominal / bc; V282 not simulable |
| release after a LIGHT hand (below the 512 freeze threshold) | 3–30 m/s | 5.9° / 6.5° | 6.3° / 6.9° | 6.3° / 6.8° | 6.2° / 6.5° | 5.7° / 6.0° | 4.6° / 5.3° | sim, max over speeds |
| engage under a handed-over load | 3–30 m/s | droop 4.7° / 5.2° | 4.6° / 5.2° | 4.7° / 5.2° | 4.1° / 4.4° | 4.2° / 4.6° | 4.2° / 4.7° | sim, max |
| tracking faster than the goal metric (0.2 Hz) | 12.5–19 m/s | 0.90–0.95 harness gain, phase −23…−25° | 0.92–0.95 | 0.92–0.95 | 0.94–0.97 | 0.88–0.94 | **0.68** | sim s02 |
| highway hold slips under road disturbance | 15–30 m/s | 3 | 3 | 3 | 0 | 0 | 0 | sim rh |

Candidate-specific (FAILs of a goal criterion, declared now):
- **D1a:** goal metric 0.944 at 11.9 m/s; texture 2.5 counts (5–30 Hz) and 26.8 counts (40–200 Hz); release lurch up to
  20.5° (bc); step overshoot up to 42 %.
- **D1c:** texture 5.4 counts rms in holds (> 2.0).
- **D3a:** goal metric 0.913–0.945 at 11.9–19 m/s; min exact GM 6.3 dB.
- **D3b:** goal metric 0.894–0.949 at 10–19 m/s.
- **Report members below 30° (not gated, the brief's set excludes them):** the factorial's b/1.9 and b_lo × J_hi2 / J1.0 ×
  tau6 (+h10) cells at 1–2 m/s and b_q×J1.3(+h10) at 15.5–15.75 m/s ring at **0.9–2.1 Hz with ζ ≥ 0.085**; light_b rings
  at **3.7–4.4 Hz** (ζ 0.08 D1b/D2a … 0.005 D3a). No point of any member is unstable.

### 5.2 Revert signatures (written before any build)

C1r2's R1–R9 apply to every candidate unchanged (inverted, rail hands-off, a new 5–30 Hz line, ring presence > 0.5 % or
F7 > 0, |θ−θ_sp| > 10° hands-off, request-drop push, STEER_STATUS ≠ 0, the operator's words), with **R3 widened to every
speed: an oscillation in 0.8–5.5 Hz in 0x14A or the 0x18F rate that grows or shows ≥ 4 visible cycles above twice the
pre-event rms (ζ < 0.10)** — it covers every sub-30° report member above (0.9–2.1 Hz) and light_b (3.7–4.4 Hz). Added per
structure:

| id | added revert signature | why |
|---|---|---|
| D1a | the operator's "buzz/fizz" on a straight; any 0x18F rate content at 40–50 Hz (aliased 100 Hz) | the 100 Hz D impulse train |
| D1b | a single-frame tap spike ≥ 30 counts coincident with a request-bit glitch or a baseline (re-reference) event | the stale `d_prev` one-tick D |
| D2a | none beyond R1–R9 | — |
| D2b | a tap kick ≥ 2× the P step on a fork setpoint step, ringing at 8–12 Hz | the forward lead on 0xE4 steps |
| D2c | none beyond R1–R9 | — |
| D3a, D3b | turn-in lag: |θ_sp − θ| > 3° for > 1 s at > 12.5 m/s in a ≤ 0.2 Hz manoeuvre | the I-P tracking miss, measured |

### 5.3 Hazards

| hazard | B0r | D1a | D1b | D1c | D2a | D2b | D2c | D3a | D3b |
|---|---|---|---|---|---|---|---|---|---|
| 0xE4 fault sentinel 0x7FFF | A2 (sim: 0.00° push every speed) | same | same | same | same | same | same | same | 0.01° on bc |
| invalid motor rate (gp-0x6abe = 0x7FFF) | held x → 0 (FUN_0003f776) | — | — | — | **cave validity → op 0** | same | same | held x → 0 | **±12000 bail → STEER_STATUS 7 latch** (fail-safe, LKAS off) |
| angle baseline wrap (−0x8000) | ±12000 bail on θ | same | same | same | same | same | same | **cave e4 := 0** (x bail tests the rate) | same |
| stale cave RAM after skips | none | none | one tick ≤ DCL × ramp | first tick lp := 0 | none | first tick w := E′ | first tick w := r26 | none | none |
| `gp-0x6cc4` re-reference (`FUN_0003bcb2`) while engaged | — | — | one tick ≤ DCL | — | — | — | — | — | — |
| |θ| > 409.6° (r26 clamp) | P wrong | same | same | P and D wrong | P wrong | same | same | — (rate) | — |
| setpoint-step authority | ×1 | **D kick, DCL-clipped** | ×1 | ×1 | ×1 | **×2 on P, 16 ms** | ×1 | ×1 (I-P) | ×1 (I-P) |
| camera 0xE4 on a relay close, torque fork on the angle image, fork crash 0.51 s hold | C1r2 §2.10 / M12 apply to every candidate unchanged | | | | | | | | |

### 5.4 The instrument that proves each one live in one short drive

Every candidate is observable with signals already on the wire (0xE4 θ_sp, 0x14A θ, 0x18F rate and driver torque, the
427 tap T = gp-0x6b38, the F181 string). The regression is C1r2 §6.1's
`tap = c_P·e + c_I·∫e + c_D·ω + c0` on hands-off windows, extended per structure so that each candidate has a coefficient
no other candidate has (tap units: counts of T/8; e in 0.1° counts; ω in deg/s):

| id | LIVE (in addition to carFw `39990-TVA,A16A`, c_P(v) within ±30 % of `Kp_eff(v)/800`, the dip at 10–12.5 m/s) | NOT LIVE / wrong image | decides |
|---|---|---|---|
| B0r, D2a, D1b | c_D ∈ [0.30, 0.50] tap per deg/s, flat in speed; c on the SETPOINT rate ≈ 0 | c_D ≈ 0 (no D) or c_sp > 0.1 (D on E) | D on a rate operand present |
| D1a | c_D ∝ G(v): 0.53 at ≤ 8 m/s → 0.16 at 11.75 m/s; **c on θ̇_sp equal to c_D** (D on error) | flat c_D | the cal-only D |
| D1b vs D2a vs B0r (fresh vs held operand) | **static, not runtime: the operand address is in the image (H5 decodes `0x29EE0` and the cave's load).** No one-drive wire test separates a 5.5 ms operand lag behind the 5 Hz output lag (BELIEF: ~10° at 5 Hz, below what 15–30 s of road excitation resolves) | — | the image check |
| D2b | a regressor on the error RATE (setpoint and measurement together): c_ė / c_P = 15 ms (the lead time kh(1−β)/β·1 ms) | c_ė ≈ 0 | the forward lead |
| D2c | c on θ̇ (measurement only) = c_P·15 ms + c_D, **c on θ̇_sp ≈ 0** | — | the feedback lead (placement) |
| D3a, D3b | a regressor on the measured angle travel since engage: c_θ = −0.0151·Ki tap per 0.1° = **−0.18 tap per 0.1° at Ki 12** (the I-P term: 7.54·Ki S per degree × 0.160 T per S ÷ 8) | c_θ ≈ 0 | the cascade |

The lead state w (D2b/D2c) and d_prev/lp (D1b/D1c) are runtime states with no tap of their own; each one's effect is the
coefficient in the table, sized against its own operand. **BELIEF** that 15–30 s of hands-off frames in two speed bands
resolve c_ė and c_θ (the C1r2 page's exposure request: one stretch > 22 m/s, one at 12.5–15 m/s, one at 5–10 m/s)."""


def scoreboard():
    import json
    s = {}
    for l in (HERE / "ds_report_summary.md").read_text(encoding="utf-8").splitlines():
        c = [x.strip() for x in l.split("|")]
        if len(c) > 20 and c[1] not in ("id", "") and not c[1].startswith("---"):
            s[c[1]] = c
    by = json.loads((HERE.parents[4] / "_scratch" / "angle_loop" / "D-structure" / "bytes_summary.json").read_text())
    env = {}
    rep = (HERE / "ds_report_out.md").read_text(encoding="utf-8").splitlines()
    on = False
    for l in rep:
        if l.startswith("| id | 1 | 3.1"):
            on = True
            continue
        if on and l.startswith("| ") and not l.startswith("|---"):
            c = [x.strip() for x in l.split("|")]
            if c[1] in ("id (envelope binding member at 3.1 / 11.75 / 17 / 26.9 m/s)",):
                break
            env[c[1]] = c[2:15]
        if on and l.strip() == "":
            if env:
                break
    goal = {}
    cur = None
    for l in (HERE / "final_track.txt").read_text(encoding="utf-8").splitlines():
        if l.startswith("---"):
            cur = l.split(":")[0][4:].strip()
            goal[cur] = []
        m = re.search(r"v\s+([\d.]+) G\s+\d+:.*min ([\d.]+) \|", l)
        if m and cur:
            goal[cur].append((float(m.group(1)), float(m.group(2))))
    retw = json.loads((HERE.parents[4] / "_scratch" / "angle_loop" / "D-structure" / "final_retw.json").read_text())
    rows = ["| id | bytes (in-place + cave + cal) / RAM | GATE 2 fails (brief's set, 4 760 pts) | T per deg at 3.1 / 11.75 / 17 / 26.9 m/s "
            "(B0r = 52 / 24 / 57 / 90) | Re(T/w)20 age 0 / 10 (V295 −0.82 / −0.89) | goal metric worst ≥ 8 m/s (bar 0.95) | "
            "dj 3–5 m/s n / bc | lurch firm / light-400 deg | texture 5–30 / 40–200 Hz | own-terms verdict |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    fails = {"B0": "**13** (ms_free PM45 ×12, ms_free+h10)"}
    verdict = {"B0": "fails the brief's ms_free corner", "B0r": "baseline: passes; misses as C1r2 class",
               "D1a": "**fails** texture, goal 11.9 m/s, releases", "D1b": "passes; best 5–25 Hz damping",
               "D1c": "**fails** texture; dominated by D1b", "D2a": "passes; ½ B0r's 20 Hz anti-damping, no RAM",
               "D2b": "passes; highest stiffness of the angle kind, best tracking and releases",
               "D2c": "passes; as D2b without the setpoint kick, −4–7 % stiffness",
               "D3a": "**fails** goal metric 0.913; thinnest GM", "D3b": "**fails** goal metric 0.894; highest 10–13 m/s stiffness"}
    ram = {"D1b": "gp-0x6c44", "D1c": "gp-0x6c44", "D2b": "gp-0x6c40", "D2c": "gp-0x6c40"}
    for k in ("B0", "B0r", "D1a", "D1b", "D1c", "D2a", "D2b", "D2c", "D3a", "D3b"):
        b = by[k]
        e = env.get(k, ["?"] * 13)
        g = goal.get(k, [])
        gw = min(g, key=lambda t: t[1]) if g else (0, 0)
        r0 = retw[k]["0"]["worst"][6]
        r10 = retw[k]["10"]["worst"][6]
        c = s.get(k)
        rows.append(f"| {k} | {b['in_place_code']} + {b['cave_code']}+{b['cave_table']} + {b['cal']} = **{b['total']}** / "
                    f"{ram.get(k, 'none')} | {fails.get(k, '0')} | {e[1]} / {e[5]} / {e[8]} / {e[11]} | {r0:+.2f} / "
                    f"{r10:+.2f} | {gw[1]:.3f} ({gw[0]:g} m/s) | {c[2] if c else '-'} | "
                    f"{(c[11].split('/')[0].strip() + ' / ' + c[12].split('/')[0].strip()) if c else '-'} | "
                    f"{(c[16].split('/')[0].strip() + ' / ' + c[17].split('/')[0].strip()) if c else '-'} | {verdict[k]} |")
    return "\n".join(rows) + ("\n\nRows: B0 = the C1 lib table scored as published; B0r = the C1r2 structure refitted exactly as every "
                              "candidate. Time-domain columns are nominal unless 'n / bc'. Byte totals are CHANGED bytes "
                              "(in-place code incl. V1, the whole cave incl. its table, cal); CRC trailers excluded.")


def main():
    doc = DOC.read_text(encoding="utf-8")
    fill = dict(BLOCKS)
    for k in fill:
        for cid in ("D1a", "D1b", "D1c", "D2a", "D2b", "D2c", "D3a", "D3b"):
            fill[k] = fill[k].replace("{BYTES_" + cid + "}", bytelist(cid)).replace("{LIST_" + cid + "}", listing(cid))
    for k, v in fill.items():
        doc = doc.replace(f"<!-- {k} -->", v)
    doc = doc.replace("<!-- SCOREBOARD -->", scoreboard())
    doc = doc.replace("<!-- DETMAX -->", "0.226 (the stiff hand's grab, identical for every candidate; zero reversals in every run)")
    tune = (HERE / "ds_d3_tune_out.txt").read_text(encoding="utf-8")
    doc = doc.replace("<!-- D3TUNE -->", "Each (Kp, Ki) at its own gated envelope; the goal metric is the minimum over the "
                      "tracking members at 0.96× that envelope, speeds 8–27 m/s:\n\n```\n" + tune + "\n```\n\n**No point "
                      "reaches 0.95 at 10–11.9 m/s; the best worst-case is 0.916 (fresh, Kp 40 / Ki 20, at the price of "
                      "the envelope).** Raising Ki strengthens the measurement-P (−7.5·Ki S per degree) as fast as the "
                      "error integral, so the I-P lag at 0.04–0.2 Hz does not close. **EVIDENCE** (model): the cascade "
                      "cannot meet the goal's tracking metric on this credible set at any scanned gain.")
    gen = (HERE / "ds_report_summary.md").read_text(encoding="utf-8") + "\n\n" + \
        (HERE / "ds_report_out.md").read_text(encoding="utf-8")
    doc = doc.replace("<!-- GENERATED -->", gen)
    doc = doc.replace("4 930 gated points per candidate", "4 760 gated points per candidate (140 grid speeds)")
    DOC.write_text(doc, encoding="utf-8")
    left = re.findall(r"<!-- [A-Z0-9_]+ -->", doc)
    print(f"wrote {DOC} ({len(doc.encode('utf-8'))} bytes); unfilled markers: {left}")


if __name__ == "__main__":
    main()
