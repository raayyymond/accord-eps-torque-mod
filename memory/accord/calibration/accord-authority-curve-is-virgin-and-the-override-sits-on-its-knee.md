---
name: accord-authority-curve-is-virgin-and-the-override-sits-on-its-knee
description: "The LKAS authority collapse curve (0xE547C/0xE5404/0xE52FC/0xE5284, mode 7) takes authority 254 to 0 across raw torque 2240-2560. It is VIRGIN on all 90 images, and the operator's measured median override torque is 2235 = one count below the first knot. 0xC64B8 is dead; the curve is the live mechanism."
metadata:
  type: reference
---

# ★★★★★ THE AUTHORITY COLLAPSE CURVE IS VIRGIN — AND THE OPERATOR DRIVES ON ITS KNEE

Established 2026-08-12 while verifying a different lead, which died. **The dead lead is the more
useful half of this memory, because it is the one that keeps getting re-proposed.**

## ☠ FIRST: `0xC64B8` IS DEAD. STRUCTURALLY TRUE, BEHAVIOURALLY EMPTY. [EVIDENCE]

V37 set `0xC64B8` `0x70` (112) → `0xFF`. The recorded side effect is real: the cal gates a branch that
**hard-kills the LKAS authority weight to 0**, and the comparison is `cal < torque_byte`, so with
`0xFF` and a byte that saturates at 255 the kill path is **unreachable**.

```
0x29a78  ld.bu  0x74b8, tp, r8      8547 b974   ; cal 0xC64B8   (hw2 = disp|1 = 0x74B9)
0x29a7c  ld.bu -0x682f, gp, r1                  ; the torque BYTE
0x29a86  cmp    r8, r1
0x29a88  bnh   0x00029a8e                       ; byte <= cal -> the CURVE path
0x29a8a  jr    0x00029cc4                       ; byte >  cal -> the CUTOFF path: iVar31 = 0
```

⊕ **The compared signal IS a torque, not a counter** — the "fail-counter gate" label describes only
one of three live readers:
`gp-0x682f = min(|gp-0x4f60| >> 5, 254)`, saturating at 255. So the gate fires at byte ≥ 113 ⇒
**|raw| ≥ 3616**.

🛑 **But it does not matter, because at mode 7 BOTH ARMS DELIVER 0 everywhere the branch could fire.**
All four curve records clamp to `Y[last] = 0` above `X[last]`, and `X[last]` is 80 or 112 — below the
gate's 113. **Stock and V37 are bit-identical on this car. V37 removed nothing.**

⇒ **Do not re-propose `0xC64B8` as a lever in the override regime.** It looks compelling — non-stock
for 66 builds, sitting exactly at high driver pushback — and it is empty.

## ★ WHAT IS ACTUALLY LIVE: THE CURVE [EVIDENCE — byte-read, all four records]

Mode index `gp-0x674e` = **7** ⇒ records:

| array | role | record | X | Y |
|---|---|---|---|---|
| `0xCBA74` | primary, sign ≥ 0 | `0xE547C` | 70, 72, 78, **80** | 254, 234, 12, **0** |
| `0xCBA04` | primary, sign < 0 | `0xE5404` | 70, 72, 78, **80** | 254, 234, 12, **0** |
| `0xCB924` | blend, sign ≥ 0 | `0xE52FC` | 32, 42, 80, **112** | 255, 255, 255, **0** |
| `0xCB8B4` | blend, sign < 0 | `0xE5284` | 32, 38, 80, **112** | 255, 255, 255, **0** |

**Authority goes 254 → 0 between raw 2240 and 2560 — a 320-count window. Nearly a step.**

🛑🛑 **ALL FOUR ARE VIRGIN ACROSS ALL 90 `_v*` IMAGES. No build has ever touched them.**

## 🛑 AND THE OPERATOR DRIVES EXACTLY ON THE KNEE

| quantity | raw | torque byte |
|---|---|---|
| curve first knot `X[0]` | 2240 | 70 |
| **measured median override torque** | **2235** | **69** |
| curve fully collapsed `X[3]` | 2560 | 80 |
| `0xC64B8` gate (dead) | 3616 | 113 |

**One count below the first knot** — full authority (254), right at the cliff edge. A few counts either
side is the difference between 254 and 0.
⇒ this is the mechanism behind the measured **~0.5–1 Hz surge**: authority pinned at exactly zero
**17.5–40.5 %** of override time while openpilot winds **UP 6.7–15×**.
⇒ [[accord-override-surge-and-two-dead-mechanisms]]

## 🛑 WHAT THIS IS *NOT*

**It is NOT a 6–9 Hz mechanism, and the curve was already refuted as one, five ways** — crossings
0.47–1.69 Hz, 88–95 % of authority energy in 0.5–3 Hz, correlation inverting against its own control,
and 6–9 Hz energy *falling* after a collapse edge. **Softening the curve targets the SURGE, not the
grinding or the micro-ratchet.** Do not conflate them.

## 🛑 IF ANYONE EVER MOVES IT — the safety direction is not symmetric

Honda collapses authority when the driver pushes hard. **That is a driver-override safety behaviour.**
Widening the window means the car **fights the driver harder and for longer**.
⇒ **The only defensible shape change is MONOTONE-NON-INCREASING: authority never higher than stock at
any torque.** Start the decay *earlier* and make it gradual, reaching 0 at the same place — that
removes the cliff without adding authority anywhere. **Anything that raises `Y` at any `X` is a
different and much more serious proposal.** GATE 2 is entirely untouched; the curve gates the whole
LKAS delivery path (`gp-0x3d3c` → `gp-0x6b30` → 4× gain → `gp-0x6b4c` → aggregator → `gp-0x6b98` →
motor).

## ⚠ THE ONE GAP — and it is one cave rung

`gp-0x674e` = 7 comes from **code + the config table + V73's on-car variant row**, never from a direct
on-car read of the byte. **It matters: modes 28–39 have `Y[last] = 51`, not 0**, and there the
`0xC64B8` branch would NOT be redundant. **V95 carries a rung for it.** It is a static config byte, so
a handful of frames settles it forever.

⊕ **Table-reading trap:** the ASCII key string sits at block `+0x24`, so it renders as the *next*
row's label in a naive dump — row 11's mode bytes are `18 19 1a 1b` (24/25/26/27 ✓ TVCA4) while the
string in the same 36-byte window reads "TVCA6". A naive `+0x12`-based dump is **off by one row**.

## BLAST RADIUS OF `0xC64B8` — 6 readers, 0 writers, two methods, set difference EMPTY
3 live (all in `FUN_00028ea6`: two DTC-0x49 counter arms + the arbitration cutoff), 3 in **dead**
functions (`FUN_0002a30e`, `FUN_0002a93a` — no callers).
🛑 **Parity trap, newly confirmed:** `0x4549E` and `0x4556E` have hw2 = `0x74B9` but opcode field
`0x3D` (disp bit0 = 1) ⇒ they address **`0xC64B9`, the NEIGHBOUR cell**. **A scan keying on hw2 alone
over-reports by two.** ⇒ [[accord-v850-scan-traps-formatv-and-storezero]]

Links: [[accord-override-surge-and-two-dead-mechanisms]] ·
[[reference-accord-steeringpressed-mask-excludes-the-symptom-regime]] ·
[[reference-accord-car-is-tvca4-mode-24-26]] · [[accord-fun38148-weights-have-an-unresolved-sign]] ·
[[accord-4x-lkas-gain-is-the-frozen-variable]] · [[v37-dtc0x49-fix-and-0xc64b8-blast-radius]]
