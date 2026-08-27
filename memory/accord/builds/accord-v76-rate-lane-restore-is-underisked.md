# ⚠ V76 IS **UN-DERISKED**, NOT DE-RISKED — built, unflashed, grind-#2 risk NOT ESTABLISHED

**2026-08-06.** 🛑 **Do NOT rename or supersede the artifact.** It is a live candidate whose one open
question is exposure, not bytes. `_v76_gate_fb_arm5244_gateprobe_plain_image.bin`.

## What it is — [EVIDENCE, byte-read]

V75's **sibling**, same V74 base. Restores V67/V68's rate lane: gate `0x3AA96` `0xC5 → 0xFB`,
`0xC6446` = 5244, `0xC6444` = 512 (already equal — asserted, never written), **both `sar` sites stock**.

**V76's ENGAGED rate lane is byte-identical to V67/V68**, so it delivers `(r24, r26)` =
**(3.414, 0.250)** at 0 km/h / rateKey 3000.

- ⚠ **The r24 dose is RATE-DEPENDENT: 1.707× → 3.414×** across the creep rate axis (1.71 / 1.71 / 2.26 /
  2.59 / 3.41 at rateKey 100 / 400 / 1400 / 2000 / 3000). A flat arm replaces a rolling-off LERP.
  **Quoting "≈1.71×" alone understates it by 2×** at the rate index where the bursts live.
- ⊕ V76's **manual** r26 is also cut to 0.167× (V74's ungated `0xC6A68`/`0xC6A7C` = 512), where
  V67/V68's manual is stock. A further cut, in the safe direction.
- ✅ **The masking risk is already closed by existing data**: V67's own probe read `gp-0x671d != 0` in
  **0 of 150,327 frames**, so `0xC6442` = 1024 never outranks the arm. No new drive needed for that.
- ✅ **Mode-proof** — the gated arms are `ld.hu <disp>[tp]` scalars that override the LERP
  unconditionally, so RULE 7 voided V69/V70 but does **not** touch this lever.

## Why it is un-derisked — [EVIDENCE]

V76 sits in the cell whose only occupants are V67/V68:

| cell | V67+V68 exposure | P(0) at V71C's own rate | power | MDE @ 80% |
|---|---|---|---|---|
| non-highway 0.3–14 m/s | 224.0 s | 0.063 | 94% | 0.58× ref |
| creep 0.3–4 m/s | 42.2 s | 0.510 | 49% | 2.39× ref |
| **engaged creep CORNER** | **11.5 s** | **0.607** | **39%** | **3.22× ref** |
| **engaged HIGH-RATE creep** | **0.0 s** | — | **0%** | — |

The powered r26-cut evidence (V72/V73/V74 — 212.5 s of dosed creep-corner, 0 events, P(0) = 0.016) is at
**r24 = 1.000×** and does **not** transfer to a build that raises r24. And per
[[accord-grind1-fix-and-grind2-are-collinear]], **no build has ever moved grind #1 and been well-powered
against grind #2.**

⚠ The single-variable contrast that would settle it exists — **V71C differs from V67/V68 in `0xC6444`
alone (3072 vs 512), and V71C bursts** — but its own power is the same 11.5 s problem.

## The resolution, and it costs no bytes

✅ **~90 s of deliberate ENGAGED hard cornering at creep** — < 4 m/s, |ang| ≥ 100°, sustained driver
torque, openpilot engaged. Takes P(0) from ~0.61 to **< 0.05 on a single drive**, whichever way it falls.
**Fly V76 with that instruction or do not fly it.**

Instruments: `analysis-2020accord/lib/_grind2_delivered_lib.py`, `studies/grind2/grind2_delivered_verdict.py`.
Related: [[accord-two-lane-rule-grind2]], [[feedback-never-log-a-hedge-as-a-null]],
[[feedback-rule7-mode-proof-or-a-bet]], [[accord-gp683c-dead-gate-is-a-free-lkas-arm]].
