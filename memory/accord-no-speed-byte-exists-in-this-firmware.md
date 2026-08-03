---
name: accord-no-speed-byte-exists-in-this-firmware
description: No speed/torque byte exists to repoint a gain gate to; gp-0x671d is a live fault response, not a free slot; and the >50 Hz probe is dead at the proven cave site
metadata:
  type: reference
---

Three evidenced negatives from 2026-08-02, all of which close routes that looked open. Each was
reached with two search methods; the coverage caveats are stated where they exist.

## 🛑 1. There is NO speed- or torque-conditional BYTE to repoint a gain gate to
V67's one-byte win (repointing `0x3AA96` from the dead `gp-0x683c` to `gp-0x6806`) made "find another
byte" look like a general technique. **It is not.** Two independent search passes over the plausible
space rejected every candidate:

| candidate | why it fails |
|---|---|
| `gp-0x679f` (new; sibling of `gp-0x6806` in the same ramp FSM, 8 writers, 0 readers) | `!= 0` is true for **7 of 8** states vs `gp-0x6806`'s 4 of 8 — **strictly broader, the wrong direction** |
| `gp-0x68b3` (standstill) | fires only at voted speed **exactly 0** — 0 for the whole 1–4 m/s creep band |
| `gp-0x67f5` | per-wheel plausibility flags **inside** the speed voter, not a threshold |
| `gp-0x6ba4` | a **halfword**, and it is the shaper's clamp state, not driver torque |
| `gp-0x67fe` | answers the *same* "LKAS applying" question V67 already found insufficient |
| `gp-0x6807`, `gp-0x67fa` | multi-valued enums; `ST == 3` is the *lockout*, i.e. inverted |
| `0xC62EA` | **= 0 on every build since V53** (grep-confirmed V53→V67) — the compare is dead |
| `0xC6316` | gates **inline arithmetic**; no `st.b`/`st.h` persists the boolean anywhere |

★ **The architectural reason, and it is the durable finding:** every `gp-0x6a5e` reader inspected
consumes vehicle speed either as a **continuous LERP evaluation axis** or as an SNA/validity guard —
never as a persisted classification byte. This firmware's idiom for speed is **"always LERP, never
threshold-and-latch."** (Contrast the many discrete flags that *do* exist for LKAS/engage state.)
⚠ Coverage: 3 of ~34 reader functions were inspected in real depth plus lighter passes on others. The
pattern was 100% consistent across two passes with different starting points, but this is *not*
exhaustively closed the way the low-speed search is.

⚠ **Corrected along the way:** cal `0xC62DE` (= 640) is **not** a driver-torque threshold as the record
said — its sole reader `FUN_000428d4` compares it against `gp-0x6a5e`, i.e. **9.99 km/h**. Siblings
`0xC62DC` = 0 (dead: `unsigned < 0`) and `0xC62E0` = 960 → 14.98 km/h. So `gp-0x671a`'s own producer is
already internally speed-gated near 10–15 km/h — baked into the existing arm-3 test, not separately
reachable.

## 🛑 2. Do NOT repoint the mask arm `gp-0x671d` — it is a LIVE fault response
It looked like a second free slot (the ladder's top-priority arm, and it read **0 in all 150,327 frames**
of route 47 and 0/14,980 on route 35). It is not free:
- `FUN_00041d56` makes it a **rising-edge event counter** on a hysteresis-thresholded, filtered
  resolver-rate anomaly, and it **drives DTC `0x5e`**.
- **16 accesses across 8 distinct functions.** Most importantly `FUN_0003d4a2`, the hardware
  phase-disable / motor-off dispatcher, reads it **4 times**, including an edge-detector on the counter
  itself (`gp-0x360f < gp-0x671d`) that forces a retry/reset path.
- Unlike `gp-0x683c` (**zero** writers image-wide, structurally dead), this has 2 live writers.
⇒ Severing r24's de-escalation response to it is a different, untested failure mode, and **0/165k logged
frames is exactly what a rare fault path looks like** — precisely when you don't want the response
quietly removed. **Hard no for a comfort fix.**

## 🛑🛑 3. The >50 Hz probe is DEAD at the proven cave site
The idea: sample inside the 1 kHz task and report a **sticky** HF flag on the 100 Hz CAN channel, to
break the ~50 Hz Nyquist ceiling both instruments share ([[accord-both-instruments-blind-above-50hz]]).
Both halves fail:
1. **The hook is not on the 1 kHz path.** `0x55C0E` sits in `FUN_00055a98`, the CAN-`0x14A` frame
   builder, reached only via handler-table slot 10 (`0xB72D4`, the sole pointer image-wide) ←
   `FUN_00055540` ← **`FUN_00022ca0` = TCB idx-4 = task 5 = 100 Hz**. The suppression counter
   `gp-0x2f68` is a **one-shot** power-on decrement with no reload (2 accesses image-wide).
   ⇒ **the cave physically cannot observe 1 kHz content.** ⚠ This corrects a kit docstring calling this
   a "1 kHz TX path"; the *"CAN-TX base tick is 100 Hz"* memory is the correct one.
2. **A sticky bit could never clear.** `gp-0x1514` has **exactly 8 accesses** and **no stock writer
   touches bits 7:3** — `FUN_0002193e`'s word store is a masked RMW (`andi 0xff0000ff`) writing the byte
   back bit-identical; `FUN_00055a98`'s three stores `andi 0xfb/0xfd/0xfe` touch only bits 2/1/0. The
   register-indirect class was checked too: only two `movea` constructions reach the frame region
   (our hook, passed to the read-only checksum `FUN_00057b24`; and `0x56288`, a different frame), and
   the overlap candidates `gp-0x1515`/`gp-0x1517` have **zero** accesses.
⇒ Breaking the barrier from firmware needs a **new hook on a task-1 site** — a fresh cave, not the
68-byte extent that has flown clean nine times. The cheap alternative is the comma's **microphone**
(`soundPressure`, computed from 16–48 kHz audio), which has no ceiling at all.

## ✅ Two useful positives that fell out
- **`gp-0x683c` IS a free RAM byte on V67 and later.** It is `.data` (boot value `flash[0x86874]` =
  `0x00`, written by two boot loops at `0x146C0`/`0x14766`), and V67 removed its only reader by
  repointing. Audited for pointer literals, `movhi`+consumer, `mov imm32`, LE32 tables, `ep`-relative
  `sld`/`sst` (a real scare, closed: all three `ep` constants in the page use displacement 0), and stack
  reach (7,848 B away). 🛑 **V67-and-later only** — on stock, `0x3AA94` is live and writing this byte
  would flip r24/r26's gain arm.
- **A search heuristic is INVERTED for this binary:** 69% of `gp-0x7000..gp-0x1000` scans as unaccessed,
  so a *long free run* is evidence of a **pointer-accessed array**, not free RAM (the 2nd-longest run's
  initializer is a repeating 16-bit table). Prefer a **short hole in a dense scalar neighbourhood**, and
  use the section (`.data` vs bss) and the initializer value as extra screens — a nonzero initializer on
  a byte with no visible reader is a warning sign.

## ⚠ One open thread worth closing before any future r24 build
**`gp-0x67ac`**: `FUN_0003aa2c`'s *first* instruction reads it, and when it is 1 the branch that adds
r24/r26 into the aggregate **does not run at all** — both lanes drop out silently regardless of which
gain arm was selected. Sourced from `gp-0x3d98`, written once in the mixer `FUN_00026c80` at `0x27314`
from a register whose origin was not traced. Prior record says the selector is unreachable on the A160;
that was via distribute's type array, and the mixer path has not been closed.

Related: [[accord-r24-gain-is-a-speed-rate-surface]], [[accord-v67-flew-both-grinds-fixed]].
