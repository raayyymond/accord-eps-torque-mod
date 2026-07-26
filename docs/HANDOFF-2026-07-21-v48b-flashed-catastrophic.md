# HANDOFF — 2026-07-21 (latest) — V48B FLASHED → CATASTROPHIC. Root-caused. Two mandatory gates added.

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2. **This supersedes `HANDOFF-2026-07-21-v48b-notch-build.md`**
(which ended "BUILT, safety-signed, UNFLASHED"). It was flashed. It bricked.

## 0. What happened
The operator flashed **V48B** (the 21.4 Hz notch code cave). On car startup — **parked, with NO LKAS
command** — the steering wheel immediately spun fast one direction then the other (full-authority
oscillation). Operator shut the car off within seconds and **recovered by reflashing a known-good image**.
No hardware damage (a few seconds of full-authority motion does not harm the rack/motor). This realized the
"code cave = the kit's only bricked class (V24/V27)" risk the build handoff explicitly flagged. It is now
the kit's **third** code-cave brick.

## 1. Root cause (GhidraMCP-traced on stock code.bin; three questions, decisive answers)

**(1) RAM COLLISION — confirmed; the likely proximate trigger of the violent onset.**
The biquad's `x2` state cell `gp-0x14FA`'s **high byte `0xFEDF6B07` (disp `-0x14F9`) aliases a live
per-monitor/DTC status bitfield** — read as a packed 2-field byte (`bits[5:4]`, `bits[3:0]`) by
`FUN_00051fbc`@`0x52052` and `FUN_00053f32`@`0x53fc8` (both `case 8`). In the DF-I biquad **x2 is multiplied
by `b2 = 3977/4096 ≈ 0.97` (near-unity)**, so an external write to that status byte injects up to ~±16000
into the accumulator → `>>12` → clamps to **±25600 (full-scale) in one sample** → motor slams. Bidirectional:
the cave also stomps that live monitor byte 1000×/s. The **aliasing is confirmed**; the **writer of the
status byte was not positively located** (register-indirect + 6-byte extended-disp are scan blind spots), so
"it writes at key-on" is highly plausible but not proven. Either way the aliasing condemns the build. Other
3 cells (y1 `gp-0x1500`, x1 `gp-0x14FC`, y2 `gp-0x14F8`) are clean by two independent methods. `gp-0x14FA`
sits inside the **sparse-flag poison region `gp-0x1401..gp-0x1502`**; vetted-safe alt = **`gp-0x14E0`**.

**(2) LIGHTLY-DAMPED RESONATOR IN THE ALWAYS-ON BASE-ASSIST LOOP — confirmed placement; never modeled.**
The notch's own poles are r=0.979 → **ζ≈0.157, Q≈3.2 @ 21.4 Hz** (a resonator, not a benign attenuator).
The 7 repointed lanes are the **always-on base power-steering assist loop** into `gp-0x6b94`→`gp-0x6b98`,
gated only on EPS state `gp-0x67fa`∈{4,5,8,10,11}/`gp-0x67fe` — **no LKAS gate, no speed gate** → active
parked, hands-off, no LKAS. The design validated the filter **open-loop** (pole radius <1, DC unity 73/73,
no int32 overflow) and inserted only its **single-frequency magnitude** `|N(21.4)|` into the *LKAS*
loop-gain model (which predicts the notch *helps*). **The closed-loop stability of the base-assist loop the
signal actually lives in was never analyzed.** The notch injects ±25° phase across 18–26 Hz; the design's
phase check looked only at 1–5 Hz (the forward-LKAS crossover). `eps_loop_gain_model.py` Task 4(d)'s
placement rationale ("OFF the safety-critical motor-command path… base assist loses only its 21 Hz response,
which it does not need") is **falsified on-car** and now annotated in the model.

**(3) Clock rate — EXONERATED.** Hook `0x7FEAC` runs from the confirmed ~1 kHz control task `FUN_0002214a`
(→`FUN_0006bb08`→`FUN_0007f3f8`), once per call, no loop, no sub-rate divider. The biquad is correctly
clocked at fs=1000.

## 2. The permanent guardrail (added this session; self-enforcing)
Two new gates now govern any cave/filter/dynamics change, recorded as an auto-loaded feedback memory
[[feedback-cave-two-gates-ram-ownership-and-closed-loop]] and in CLAUDE.md:
- **GATE 1 — RAM ownership:** every byte (full multi-byte footprint) proven free incl. **writers** and
  register-indirect / 6-byte-extended-disp accesses; sparse-flag region `gp-0x1401..gp-0x1502` is poison.
- **GATE 2 — closed-loop stability:** analyze magnitude+phase (Nyquist/margin) of **every loop the signal is
  in** — especially the always-on base-assist loop — with the element inserted; open-loop validation is not
  sufficient.
Byte/CRC/disassembly/open-loop-DSP verification is necessary but does NOT cover these two dimensions — the
exact two that bricked V48B.

## 3. Status of the notch idea
Not necessarily dead, but **on hold**. To revive it: (a) move all four biquad cells to genuinely-free RAM
(`gp-0x14E0` and neighbors, re-verified writer-side); (b) build a real base-assist closed-loop model and
prove the notch keeps positive gain+phase margin there — or move the notch OUT of the base-assist forward
path entirely. Do not re-flash any cave without both gates closed AND explicit operator instruction naming
the file + bus, openpilot killed.

## 4. Files touched this session
- `memory/reference-accord-v48b-flashed-catastrophic-ram-collision.md` (new — the failure record)
- `memory/feedback-cave-two-gates-ram-ownership-and-closed-loop.md` (new — the prevention gates)
- `memory/reference-accord-v48b-notch-cave-build.md` (amended — FLASHED→CATASTROPHIC header)
- `memory/MEMORY.md` (index)
- `CLAUDE.md` (CURRENT STATE)
- `analysis-2020accord/eps_loop_gain_model.py` (Task 4(d) falsification annotation)
